import pandas as pd
from datetime import datetime

TOU_RATES = {
    "peak": 0.3065,
    "off_peak": 0.1243,
    "super_off_peak": 0.0787
}

def get_rate(dt: datetime) -> tuple[str, float]:
    weekday = dt.weekday() < 5
    hour    = dt.hour
    if weekday and 15 <= hour <= 21:
        return ("peak", TOU_RATES["peak"])
    elif hour >= 23 or hour <= 6:
        return ("super off peak", TOU_RATES["super_off_peak"])
    else:
        return ("off_peak", TOU_RATES["off_peak"])

def estimate_energy(sim_df: pd.DataFrame,
                    heat_kwh_hourly: float = 2.0,
                    vent_kwh_hourly:  float = 0.5):
    """Add kWh & cost columns and return totals."""
    energy     = []
    total_cost = 0.0
    total_kwh  = 0.0
    for _, row in sim_df.iterrows():
        _, rate = get_rate(row["datetime"])
        kwh  = row["heating"] * heat_kwh_hourly + row["venting"] * vent_kwh_hourly
        cost = kwh * rate
        total_cost += cost
        total_kwh  += kwh
        energy.append({"energy_kwh": kwh, "energy_cost": cost})
    joined = pd.concat([sim_df.reset_index(drop=True),
                        pd.DataFrame(energy)], axis=1)
    return joined, total_kwh, total_cost