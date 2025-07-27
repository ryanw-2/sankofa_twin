import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import pvlib
from typing import cast

from Predictive import Predictive
from ThermalMass import ThermalMass
"""
The GreenhouseConfig class sets up the constants 
of the greenhouse based on user defined values.
"""

# ────────────── CONSTANTS (SI) ──────────────────────────────────────────
CONCRETE_DENSITY_KG_M3 = 2400            # kg m-3
SOIL_DENSITY_KG_M3     = 1600            # kg m-3
SOIL_COUPLING_FACTOR   = 0.30            # fraction of soil mass thermally linked
BAMBOO_MASS_KG         = 200             # plant + bench mass
SPECIFIC_HEAT_J_PER_KG = 920             # concrete / soil
ARCH_FACTOR            = 1.15            # curved roof extra area
GLAZING_U_VALUE        = 3.2             # W m-2 K-1  (≈ 0.56 BTU ft-2 h-1 °F-1)
SOLAR_HEAT_GAIN_COEFF  = 0.65            # SHGC of glazing
LIGHT_TRANSMISSION     = 0.80
ALBEDO                 = 0.20
R_IP_TO_SI             = 5.678263        # divide IP R by this to get m² K W-1
AIR_DENSITY            = 1.225

# ────────────── GREENHOUSE CONFIG ──────────────────────────────────────
class GreenhouseConfig:
    def __init__(self, latitude: float, longitude: float, num_footings: int = 8, design_temp_diff_C: float = 20):
        # ── Geometry (m) ────────────────────────────────────────────────
        self.latitude  = latitude
        self.longitude = longitude

        self.length   = 37.6666 * 0.3048   # 11.48 m
        self.width    = 18.95   * 0.3048   #  5.78 m
        self.height   = 12      * 0.3048   #  3.66 m
        self.sidewall = 8       * 0.3048   #  2.44 m
        self.orientation      = 135        # wall azimuth °
        self.surface_tilt_deg = 90.0       # vertical walls
        self.glazing_tau      = 0.78

        # ── Areas (m²) ─────────────────────────────────────────────────
        self.wall_A = 2 * (self.length + self.width) * self.sidewall
        self.roof_A = self.length * self.width * ARCH_FACTOR
        self.floor_A = self.length * self.width
        self.glazing_A = self.wall_A + self.roof_A           

        # ── Volume (m³) ────────────────────────────────────────────────
        # Triangular gable + sidewalls
        _roof_peak_height = self.height - self.sidewall
        self.volume_m3 = (self.length * self.width *
                          (_roof_peak_height / 2 + self.sidewall))
        self.rho_cp_V = AIR_DENSITY * self.volume_m3 * 1005

        # ── Fabric performance (m² K W-1) ──────────────────────────────
        self.wall_R   = 1.8 / R_IP_TO_SI     # 0.317  m² K W-1
        self.roof_R   = 1.8 / R_IP_TO_SI
        self.floor_R  = 8.0 / R_IP_TO_SI     # slab to ground
        self.glazing_R = 1 / GLAZING_U_VALUE # 0.312  m² K W-1

        # ── Ventilation ────────────────────────────────────────────────
        self.leak_ach        = 0.30          # h-1, closed house
        self.design_vent_ach = 2.0           # natural vents full-open

        # ── Thermal mass (kg) ──────────────────────────────────────────
        self.mass_kg = self._build_thermal_mass_KG(num_footings)
        self.mass_c_p = SPECIFIC_HEAT_J_PER_KG
        self.ua_envelope = (
            self.wall_A / self.wall_R +
            self.roof_A / self.roof_R +
            self.floor_A / self.floor_R
        )
        # ── Heating design load (W) ────────────────────────────────────
        self.design_dT = design_temp_diff_C
        self.heater_W  = self._build_heater_sizing_W()

        # Controller
        self.controller = self._build_controller()

    def _build_thermal_mass_KG(self, num_footings: int) -> float:
        # 12 ft³ footing → 0.339 m³ each
        concrete_V = num_footings * (12 * 0.0283168)
        concrete_m = concrete_V * CONCRETE_DENSITY_KG_M3
        soil_V     = self.floor_A * 0.61     # 2 ft = 0.61 m depth
        soil_m     = soil_V * SOIL_DENSITY_KG_M3 * SOIL_COUPLING_FACTOR
        return concrete_m + soil_m + BAMBOO_MASS_KG

    def _build_heater_sizing_W(self) -> int:
        Q_cond = self.ua_envelope * self.design_dT  
        mass_flow  = (self.volume_m3 * self.design_vent_ach / 3600) * 1.2
        Q_vent = mass_flow * 1005 * self.design_dT 
        safety = 1.30
        return int((Q_cond + Q_vent) * safety)

    def _build_controller(self) -> Predictive:
        leak_U = AIR_DENSITY * self.volume_m3 * self.leak_ach / 3600 * 1005 
        h_ma = 230
        
        sim_C_J_K = self.mass_kg * self.mass_c_p + AIR_DENSITY * self.volume_m3 * 1005
        sim_U_W_K = self.ua_envelope + leak_U + h_ma

        controller = Predictive(
            C_J_K=sim_C_J_K,
            U_W_K=sim_U_W_K,
            heater_W=self.heater_W,
            vent_max_ach=self.design_vent_ach,
            dt_hr=1.0
        )

        return controller

class GreenhouseThermalEngine:
    def __init__(self, config: GreenhouseConfig, air_temp_init_C: float):
        self.cfg = config
        self.air_temp = air_temp_init_C            
        self.mass = ThermalMass(config.mass_kg, config.mass_c_p)

    def calculate_solar_gain_W(self, ghi:float, dni:float, dhi:float, solar_zenith:float, solar_azimuth:float):
        """
        Calculates the amount of energy entering the building
        at a given solar position.
        """
        if ghi <= 0:
            return 0.0

        poa_comp = pvlib.irradiance.get_total_irradiance(
            self.cfg.surface_tilt_deg,
            self.cfg.orientation,
            dni, ghi, dhi,
            solar_zenith, solar_azimuth,
            albedo=ALBEDO
        )

        poa = poa_comp["poa_global"].iloc[0]
        area_m2 = self.cfg.glazing_A * self.cfg.glazing_tau
        return float(poa) * area_m2

    def calculate_heat_loss_W(self, air_temp: float, ext_temp: float, wind_m_s: float) -> float:
        """
        Calculates the amount of energy lost due to conduction
        and infiltration.
        """
        dT = air_temp - ext_temp

        # 1. Conduction (W)
        Q_cond = (
            self.cfg.wall_A   / self.cfg.wall_R   +
            self.cfg.roof_A   / self.cfg.roof_R   +
            self.cfg.floor_A  / self.cfg.floor_R  +
            self.cfg.glazing_A / self.cfg.glazing_R
        ) * dT

        # 2. Infiltration (W) 
        m_dot = self.cfg.volume_m3 * self.cfg.leak_ach / 3600 * 1.2
        Q_inf = m_dot * 1005 * dT

        # 3. Wind multiplier
        WIND_COEFF = 0.05      
        Q_total = (Q_cond + Q_inf) * (1 + WIND_COEFF * wind_m_s)

        return Q_total
    
    def calculate_venting_loss_W(self, air_temp: float, ext_temp: float, vent_ach:float) -> float:
        """
        Calculates the energy loss due to active ventilation.
        """
        dT = air_temp - ext_temp
        if vent_ach == 0 or dT < 0:
            return 0.0
        
        CP_AIR = 1005
        volumetric_flow = self.cfg.volume_m3 * (vent_ach / 3600)
        mass_flow = AIR_DENSITY * volumetric_flow
        Q_vent = mass_flow * CP_AIR * (air_temp - ext_temp)

        return Q_vent

    def calculate_heating_gain_W(self, heater_on: bool, partial: float = 1.0) -> float:
        """
        Calculates the energy gained due to active heating.
        """
        if not heater_on:
            return 0.0

        EFFICIENCY =  0.90
        partial = max(0.0, min(1.0, partial))
        Q_heat = partial * self.cfg.heater_W * EFFICIENCY
        return Q_heat

    def simulate_step(self, initial_air_temp, initial_mass_temp, forecast_df, start_i:int=0, steps:int=12, horizon:int=12):
        assert len(forecast_df) >= start_i + steps + horizon
        # solar gain + heating gain - (venting loss + heat loss)
        simulated = []
        
        air_temp = initial_air_temp
        mass_temp = initial_mass_temp
        for k in range(start_i, start_i + steps):            
            horizon_df = forecast_df[k:k+horizon] # needs extra 12 hours of data
            pred_forecast_df = {
                "temp" : horizon_df["temp"],
                "Q_solar" : horizon_df["Q_solar"],
            }

            heater_on, part_load, vent_ach = self.cfg.controller.decide(air_temp, horizon_df)

            forecast_row = forecast_df.iloc[k]
            ext_temp = forecast_row["temp"]
            wind_speed = forecast_row["wind_speed"]
            q_sol_gain = forecast_row["Q_solar"]
            q_heat_loss = self.calculate_heat_loss_W(air_temp, ext_temp, wind_speed)
            q_vent_loss = self.calculate_venting_loss_W(air_temp, ext_temp, vent_ach)
            q_heat_gain = self.calculate_heating_gain_W(heater_on, part_load)

            mass_factor = 0.3
            q_to_mass = mass_factor * q_sol_gain
            q_to_air = (1 - mass_factor) * q_sol_gain
            mass_temp = self.mass.update_temperature(q_to_mass, air_temp, mass_temp)

            h_ma = 230
            q_exchange = h_ma * (mass_temp - air_temp)

            q_net = q_to_air + q_heat_gain + q_exchange - q_heat_loss - q_vent_loss
            air_temp += (q_net) * 3600 / self.cfg.rho_cp_V


            simulated.append({
                "datetime":   forecast_row.name,
                "T_air":      air_temp,
                "T_mass":     mass_temp,
                "heater_on":  heater_on,
                "part_load":  part_load,
                "vent_ach":   vent_ach,
                "Q_solar":    q_sol_gain,
                "Q_heat":     q_heat_gain,
                "Q_loss":     q_heat_loss,
                "Q_vent":     q_vent_loss,
                "Q_exchange": q_exchange,
                "Q_net_air":  q_net,
            })
        
        simulated_df = pd.DataFrame(simulated).set_index("datetime")
        return simulated_df


