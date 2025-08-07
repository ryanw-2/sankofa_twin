import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import pvlib
from typing import cast
import logging
from Predictive import Predictive
from ThermalMass import ThermalMass

from forecast import get_geocode, get_hourly_forecast, get_hourly_solar, get_hourly_weather
"""
The GreenhouseConfig class sets up the constants 
of the greenhouse based on user defined values.
"""
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    def __init__(self, latitude: float, longitude: float, num_footings: int = 8, design_temp_diff_C: float = 25):
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
        self.wall_R   = 3 / R_IP_TO_SI     
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
        mass_flow  = (self.volume_m3 * self.design_vent_ach / 3600) * AIR_DENSITY
        Q_vent = mass_flow * 1005 * self.design_dT 
        safety = 1.60
        return int((Q_cond + Q_vent) * safety)

    def _build_controller(self) -> Predictive:
        leak_U = AIR_DENSITY * self.volume_m3 * self.leak_ach / 3600 * 1005 
        h_ma = 1500
        
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
    
    def get_summary(self):
        """Return summary of greenhouse configuration."""
        return {
            'location': (self.latitude, self.longitude),
            'dimensions_m': (self.length, self.width, self.height),
            'floor_area_m2': self.floor_A,
            'volume_m3': self.volume_m3,
            'glazing_area_m2': self.glazing_A,
            'thermal_mass_kg': self.mass_kg,
            'ua_envelope_W_K': self.ua_envelope,
            'heater_capacity_W': self.heater_W
        }
    
class GreenhouseThermalEngine:
    def __init__(self, config: GreenhouseConfig, air_temp_init_C: float):
        self.cfg = config
        self.air_temp = air_temp_init_C            
        self.mass = ThermalMass(config.mass_kg, config.mass_c_p)

        logger.info(f"Thermal engine initialized with T_air={air_temp_init_C:.1f}°C")

    def calculate_heat_loss_W(self, air_temp: float, ext_tempemp: float, wind_m_s: float) -> float:
        """
        Calculates the amount of energy lost due to conduction
        and infiltration.
        """
        dT = air_temp - ext_tempemp

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
    
    def calculate_venting_loss_W(self, air_temp: float, ext_tempemp: float, vent_ach:float) -> float:
        """
        Calculates the energy loss due to active ventilation.
        """
        dT = air_temp - ext_tempemp
        if vent_ach == 0 or dT < 0:
            return 0.0
        
        CP_AIR = 1005
        volumetric_flow = self.cfg.volume_m3 * (vent_ach / 3600)
        mass_flow = AIR_DENSITY * volumetric_flow
        Q_vent = mass_flow * CP_AIR * (air_temp - ext_tempemp)

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
        # solar gain + heating gain - (venting loss + heat loss)
        simulated = []
        h_ma = 1500

        air_temp = initial_air_temp
        mass_temp = initial_mass_temp
        mass_fac = 0.8
        for k in range(start_i, start_i + steps):            
            horizon_df = forecast_df.iloc[k : k + horizon]
            horizon_dict = {
                "temp"   : horizon_df["temp"].to_numpy(),
                "Q_solar": horizon_df["Q_solar"].to_numpy(),
            }
            heater_on, part_load, vent_ach = self.cfg.controller.decide(air_temp, horizon_dict)

            row = forecast_df.iloc[k]
            ext_temp = row["temp"]
            wind_speed = row["wind_speed"]
            Q_solar_hr = row.Q_solar
            Q_heat_hr  = self.calculate_heating_gain_W(heater_on, part_load)

            # --- 4 sub‑steps of 15 min each -------------------------------
            Q_solar_sub = Q_solar_hr / 4.0
            Q_heat_sub  = Q_heat_hr  / 4.0
            for _ in range(4):
                # losses at current air temp
                Q_loss = self.calculate_heat_loss_W(air_temp, ext_temp, wind_speed) / 4.0
                Q_vent = self.calculate_venting_loss_W(air_temp, ext_temp, vent_ach) / 4.0

                # split solar, update mass
                q_to_mass = mass_fac * Q_solar_sub
                q_to_air  = (1 - mass_fac) * Q_solar_sub
                mass_temp = self.mass.update_temperature(q_to_mass, air_temp, mass_temp)

                q_exchange = h_ma * (mass_temp - air_temp)
                q_net_air  = q_to_air + Q_heat_sub + q_exchange - Q_loss - Q_vent

                SUB_DT_HR = 0.25               # 15‑minute physics interval
                SUB_DT_S  = SUB_DT_HR * 3600
                air_temp += q_net_air * SUB_DT_S / (self.cfg.rho_cp_V + self.cfg.mass_kg*self.cfg.mass_c_p)



            simulated.append({
                "datetime"  : row.name,
                "T_air"     : air_temp,
                "T_mass"    : mass_temp,
                "heater_on" : heater_on,
                "part_load" : part_load,
                "vent_ach"  : vent_ach,
                "Q_solar"   : Q_solar_hr,
                "Q_heat"    : Q_heat_hr,
                "Q_loss"    : self.calculate_heat_loss_W(air_temp, ext_temp, wind_speed),
                "Q_vent"    : self.calculate_venting_loss_W(air_temp, ext_temp, vent_ach),
                "Q_exchange": h_ma * (mass_temp - air_temp),
            })
            
        simulated_df = pd.DataFrame(simulated).set_index("datetime")
        logger.info(f"Simulation completed: {steps} steps, "
                        f"T_air range: {simulated_df['T_air'].min():.1f}-{simulated_df['T_air'].max():.1f}°C")
        return simulated_df
    
# load_dotenv()
# WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

# FORECAST_BASE_URL = "https://pro.openweathermap.org/data/2.5/forecast/hourly?"
# WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather?"
# GEOCODE_BASE_URL = "http://api.openweathermap.org/geo/1.0/direct?"

# latitude, longitude = get_geocode("Pittsburgh", "PA", "US")

# config = GreenhouseConfig(latitude, longitude)
# combined_df = get_hourly_forecast(latitude, longitude, config, "US/Pacific")
# print(combined_df)
# GCFG = GreenhouseConfig(latitude, longitude)
# GEngine = GreenhouseThermalEngine(GCFG, 20.0)
def create_example_config(city: str = "Pittsburgh", state: str = "PA", country: str = "US") -> GreenhouseConfig:
    """
    Create example greenhouse configuration for a given location.
    
    Args:
        city: City name
        state: State/province code  
        country: Country code
        
    Returns:
        Configured GreenhouseConfig object
    """
    try:
        # This would require the forecast module to be available
        # latitude, longitude = get_geocode(city, state, country)
        
        # For demo purposes, use Pittsburgh coordinates
        latitude, longitude = 40.4406, -79.9959
        
        config = GreenhouseConfig(
            latitude=latitude,
            longitude=longitude,
            num_footings=8,
            design_temp_diff_C=20
        )
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to create config for {city}, {state}: {e}")
        raise


if __name__ == "__main__":
    # ------------------------------------------------------------------
    # 0 · Dummy 5-hour forecast  ---------------------------------------
    # ------------------------------------------------------------------
    times = pd.date_range("2025-08-06 06:00", periods=5, freq="h", tz="UTC")
    dummy = pd.DataFrame(
        {
            # outside air °C
            "temp":       [18, 18, 19, 20, 22],
            # constant light breeze m s-1
            "wind_speed": [2.0]*5,
            # fake clear-sky solar gain W entering GH
            "Q_solar":    [0, 5_000, 10_000, 8_000, 2_000],
        },
        index=times,
    )
    times = pd.date_range("2025-08-06 06:00", periods=6, freq="h", tz="UTC")
    winter_forecast = pd.DataFrame(
        {
            # outdoor dry-bulb temperature (°C)
            "temp": [-5, -5, -4, -3, -2,  0],
            # wind speed at 2 m (m s⁻¹)
            "wind_speed": [3, 4, 4, 5, 4, 3],
            # net solar power entering GH glazing (W)
            # — night is 0, clear winter sun peaks ~6 kW at local noon
            "Q_solar": [0, 0, 1500, 3000, 4500, 6000],
        },
        index=times,
    )
    print("\nDummy forecast\n--------------")
    print(winter_forecast)

    # ------------------------------------------------------------------
    # 1 · Build config & engine  ---------------------------------------
    # ------------------------------------------------------------------
    cfg = create_example_config()          # Pittsburgh hard-coded
    engine = GreenhouseThermalEngine(cfg, air_temp_init_C=20.0)
    mylat, mylon = get_geocode("San Jose", "CA", "US")
    forecast_df = get_hourly_forecast(mylat, mylon, cfg, "US/Eastern")

    # ------------------------------------------------------------------
    # 2 · One simulate_step call (5 h window) --------------------------
    # ------------------------------------------------------------------
    sim_df = engine.simulate_step(
        initial_air_temp = 20.0,
        initial_mass_temp = 20.0,
        forecast_df = forecast_df,
        start_i = 0,
        steps = 24,
        horizon = 12,        # look ahead all remaining rows
    )

    print("\nSimulation results\n------------------")
    print(sim_df.round(2))
