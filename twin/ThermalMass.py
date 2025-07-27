import pandas as pd
from datetime import datetime, timedelta
import numpy as np

"""
The ThermalMass class calculates the changes in internal
temperature based on the heat exchange at the given step intervals.
"""

# Constants
HEAT_EXCHANGE_RATE = 50.0 # Watts/Kelvin

class ThermalMass:
    def __init__(self, mass_kg, specific_heat, initial_temp: float = 20.0):
        assert mass_kg > 0 and specific_heat > 0

        self.mass_kg = mass_kg
        self.specific_heat = specific_heat
    
    # public
    def update_temperature(self, heat_input_watts: float, air_temp: float, prev_temp: float):
        temp_diff = air_temp - prev_temp
        step_seconds = 3600
        heat_exchange_joules = HEAT_EXCHANGE_RATE * temp_diff * step_seconds
        total_heat_input_joules = heat_input_watts * step_seconds + heat_exchange_joules
        temp_change_C = total_heat_input_joules / (self.mass_kg * self.specific_heat)
        return air_temp + temp_change_C
