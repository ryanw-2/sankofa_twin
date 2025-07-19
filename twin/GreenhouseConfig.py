import pandas as pd
from datetime import datetime, timedelta
import numpy as np

"""
The GreenhouseConfig class sets up the constants 
of the greenhouse based on user defined values.
"""

# Constants
CONCRETE_DENSITY_LB_FT3 = 150
SOIL_DENSITY_LB_FT3 = 100
SOIL_COUPLING_FACTOR = 0.3
BAMBOO_MASS_KG = 200
FT3_TO_KG = 0.453592
SPECIFIC_HEAT_J_PER_KG_K = 920
ARCH_FACTOR = 1.15
GLAZING_U_FACTOR = 0.56
SOLAR_HEAT_GAIN_COEFF = 0.65
LIGHT_TRANSMISSION = 0.80

class GreenhouseConfig:
    def __init__(self, num_footings=8, design_temp_diff=70):
        """Values derived from architectural drawings of the greenhouse"""
        self.length = 37.6666
        self.width = 18.95
        self.height = 12
        self.sidewall_height = 8
        self.orientation = 135
        
        # Material properties
        self.wall_r_value = 1.8
        self.roof_r_value = 1.8
        self.foundation_r_value = 8.0
        self.glazing_r_value = 1.8
        self.glazing_u_factor = GLAZING_U_FACTOR
        self.solar_heat_gain_coefficient = SOLAR_HEAT_GAIN_COEFF
        self.light_transmission = LIGHT_TRANSMISSION
        
        # Areas
        self.arch_factor = ARCH_FACTOR
        self.wall_area = 2 * (self.length + self.width) * self.sidewall_height
        self.roof_area = self.length * self.width * self.arch_factor
        self.foundation_area = self.length * self.width
        self.glazing_area = self.wall_area + self.roof_area  # Fully glazed
        self.greenhouse_volume_ft3 = self.length * self.width * self.height
        
        # Thermal properties
        self.thermal_mass = self._calculate_thermal_mass(num_footings)
        self.specific_heat_j_per_kg_k = SPECIFIC_HEAT_J_PER_KG_K
        
        # Ventilation
        self.air_changes_per_hour = 2.0
        self.natural_ventilation_area = 0.08 * self.glazing_area
        self.infiltration_ach = 0.3
        
        # Heating
        self.design_temp_diff = design_temp_diff
        self.heater_btu_hour = self._calculate_heater_sizing()
        
    def _calculate_thermal_mass(self, num_footings):
        concrete_volume = num_footings * 12
        concrete_mass = concrete_volume * CONCRETE_DENSITY_LB_FT3 * FT3_TO_KG
        soil_volume = self.foundation_area * 2
        soil_mass = soil_volume * SOIL_DENSITY_LB_FT3 * FT3_TO_KG * SOIL_COUPLING_FACTOR
        return concrete_mass + BAMBOO_MASS_KG + soil_mass
    
    def _calculate_heater_sizing(self):
        wall_loss = (1/self.wall_r_value) * self.glazing_area * self.design_temp_diff
        foundation_loss = (1/self.foundation_r_value) * self.foundation_area * self.design_temp_diff
        cfm = self.greenhouse_volume_ft3 / 60
        ventilation_loss = 1.08 * cfm * self.air_changes_per_hour * self.design_temp_diff
        safety_factor = 1.3
        return int((wall_loss + foundation_loss + ventilation_loss) * safety_factor)



