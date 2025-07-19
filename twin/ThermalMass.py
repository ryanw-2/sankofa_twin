import pandas as pd
from datetime import datetime, timedelta
import numpy as np

"""
The ThermalMass class calculates the changes in internal
temperature based on the heat exchange at the given step intervals.
"""

# Constants
HEAT_EXCHANGE_RATE = 50.0

class ThermalMass:
    def __init__(self, mass_kg, specific_heat, initial_temp):
        self.mass = mass_kg
        self.specific_heat = specific_heat
        self.temp_c = initial_temp
    
    def update_temperature(self, heat_input_watts, air_temp, step_hours):
        temp_diff = air_temp - self.temp_c
        heat_exchange_joules = HEAT_EXCHANGE_RATE * temp_diff * step_hours * 3600
        total_heat_input_joules = heat_input_watts * step_hours * 3600 + heat_exchange_joules
        temp_change_c = total_heat_input_joules / (self.mass * self.specific_heat)
        self.temp_c += temp_change_c
        return self.temp_c
