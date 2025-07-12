import pandas as pd

WINTER_ENERGY_HOURLY_RATE = 0.040306
SUMMER_ENERGY_HOURLY_RATE = 0.0017562


def simulate_next_humidity(
    internal_hum: float,
    external_hum: float,
    internal_temp: float,
    is_heating: bool,
    is_venting: bool,
):
    heating_effect = 0.0
    if is_heating:
        heating_effect = -0.5

    venting_effect = 0.0
    if is_venting:
        venting_effect = 0.3 * (external_hum - internal_hum)

    passive_gain = (
        0.05 * (100 - internal_hum) if not is_venting and not is_heating else 0.0
    )

    delta = heating_effect + venting_effect + passive_gain
    humidity = internal_hum + delta

    return max(0, min(100, humidity))


def simulate_internal_temp(
    forecast_df: pd.DataFrame,
    initial_temp: float,
    internal_humidity: float,
    heating_fn,
    venting_fn,
):
    internal_temps = []
    current_temp = initial_temp

    for i, row in forecast_df.iterrows():
        ext_temp = row["temp"]
        ext_humidity = row["humidity"]

        heating = heating_fn(row["datetime"])
        venting = venting_fn(row["datetime"])

        heat_loss = 0.1 * (ext_temp - current_temp)
        heat_input = 2.5 if heating else 0.0

        venting_cooling = 0.3 * (ext_temp - current_temp) if venting else 0.0

        delta = heat_loss + heat_input + venting_cooling
        current_temp += delta

        current_humidity = simulate_next_humidity(
            internal_humidity, ext_humidity, current_temp, heating, venting
        )

        internal_temps.append(
            {
                "datetime": row["datetime"],
                "external_temp": ext_temp,
                "internal_temp": current_temp,
                "external_humidity": ext_humidity,
                "internal_humidity": current_humidity,
                "heating": heating,
                "venting": venting,
            }
        )

    return pd.DataFrame(internal_temps)

