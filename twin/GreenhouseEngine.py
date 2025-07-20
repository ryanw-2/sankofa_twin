import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from ThermalMass import ThermalMass
import pvlib
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

# ────────────── GREENHOUSE CONFIG ──────────────────────────────────────
class GreenhouseConfig:
    def __init__(self, latitude: float, longitude: float,
                 num_footings: int = 8, design_temp_diff_C: float = 20):
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
        self.glazing_A = self.wall_A + self.roof_A           # fully glazed

        # ── Volume (m³) ────────────────────────────────────────────────
        # Triangular gable + sidewalls
        roof_peak_height = self.height - self.sidewall
        self.volume_m3 = (self.length * self.width *
                          (roof_peak_height / 2 + self.sidewall))

        # ── Fabric performance (m² K W-1) ──────────────────────────────
        self.wall_R   = 1.8 / R_IP_TO_SI     # 0.317  m² K W-1
        self.roof_R   = 1.8 / R_IP_TO_SI
        self.floor_R  = 8.0 / R_IP_TO_SI     # slab to ground
        self.glazing_R = 1 / GLAZING_U_VALUE # 0.312  m² K W-1

        # ── Ventilation ────────────────────────────────────────────────
        self.leak_ach        = 0.30          # h-1, closed house
        self.design_vent_ach = 2.0           # natural vents full-open

        # ── Thermal mass (kg) ──────────────────────────────────────────
        self.mass_kg = self._calc_thermal_mass(num_footings)
        self.mass_c_p = SPECIFIC_HEAT_J_PER_KG

        # ── Heating design load (W) ────────────────────────────────────
        self.design_dT = design_temp_diff_C
        self.heater_W  = self._heater_sizing_W()

    # ---------- helpers -------------------------------------------------
    def _calc_thermal_mass(self, num_footings: int) -> float:
        # 12 ft³ footing → 0.339 m³ each
        concrete_V = num_footings * (12 * 0.0283168)
        concrete_m = concrete_V * CONCRETE_DENSITY_KG_M3
        soil_V     = self.floor_A * 0.61     # 2 ft = 0.61 m depth
        soil_m     = soil_V * SOIL_DENSITY_KG_M3 * SOIL_COUPLING_FACTOR
        return concrete_m + soil_m + BAMBOO_MASS_KG

    def _heater_sizing_W(self) -> int:
        UA_envelope = (
            self.wall_A / self.wall_R +
            self.roof_A / self.roof_R +
            self.floor_A / self.floor_R
        )
        Q_cond = UA_envelope * self.design_dT          # W
        m_dot  = (self.volume_m3 * self.design_vent_ach / 3600) * 1.2  # kg s-1
        Q_vent = m_dot * 1005 * self.design_dT         # W
        safety = 1.30
        return int((Q_cond + Q_vent) * safety)


class GreenhouseThermalEngine:
    def __init__(self, config, T_air_init_C: float):
        self.cfg      = config
        self.air_temp    = T_air_init_C              # °C
        self.mass     = ThermalMass(config.mass_kg, config.mass_c_p)

    def calculate_solar_gain(self, ghi, dni, dhi, solar_zenith, solar_azimuth):
        if ghi <= 0:
            return 0.0

        poa_comp = pvlib.irradiance.get_total_irradiance(
            self.cfg.surface_tilt_deg,
            self.cfg.orientation,
            dni, ghi, dhi,
            solar_zenith, solar_azimuth,
            albedo=ALBEDO
        )
        
        poa = poa_comp['poa_global']
        area_m2 = self.cfg.glazing_A * self.cfg.glazing_tau
        return poa * area_m2

    def calculate_heat_loss(self, ext_temp: float, wind_m_s: float) -> float:
        dT = self.air_temp - ext_temp
        if dT <= 0:
            return 0.0

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


        



        


