import pandas as pd
from datetime import datetime, timedelta
import numpy as np
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
        cloud_cover = row["cloud_cover"]

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
                "cloud_cover": cloud_cover,
                "heating": heating,
                "venting": venting,
            }
        )

    return pd.DataFrame(internal_temps)

def simulate_next_conditions(
    internal_temp, external_temp, internal_humidity, external_humidity, heating, venting
):
    temp = internal_temp
    humidity = internal_humidity

    heating_effect = 0.0
    if heating:
        temp += 1.5
        heating_effect = -0.5
    venting_effect = 0.0
    if venting:
        temp += 0.75 * (external_temp - temp)
        venting_effect = 0.3 * (external_humidity - internal_humidity)

    passive_gain = (
        0.05 * (100 - internal_humidity) if not venting and not heating else 0.0
    )

    humidity = internal_humidity + (heating_effect + venting_effect + passive_gain)
    humidity = max(0, min(100, humidity))
    temp += 0.05 * (external_temp - temp)

    return temp, humidity

def forecast_n_hours_ahead(
        n,
        start_internal_temp,
        start_internal_humidity,
        external_temp_forecast,
        external_humidity_forecast,
        clf_heat_model,
        clf_vent_model,
        scaler,
        features
):
    n_steps = n
    if len(external_temp_forecast) != n_steps or len(external_humidity_forecast) != n_steps:
        print("Error: Forecast data not sufficient for accurate modeling")
        return None
    if n_steps > 48:
        print("Caution: Predictions beyond 48 hours may be inaccurate.")
    
    cur_temp = start_internal_temp
    cur_hum = start_internal_humidity

    timestamps = [datetime.now() + timedelta(hours=1) for _ in range(n_steps)]

    predicted_temps = []
    predicted_heating = []
    predicted_venting = []

    for i in range(n_steps):
        ext_temp = external_temp_forecast[i]
        ext_hum = external_humidity_forecast[i]

        feature_row = pd.DataFrame([{
            "internal_temp": cur_temp,
            "external_temp": ext_temp,
            "internal_humidity": cur_hum,
            "external_humidity": ext_hum,
            "heating": 0,
            "venting": 0
        }])[features]

        X_scaled = scaler.transform(feature_row)

        heating = int((clf_heat_model.predict(X_scaled)[0,0]) > 0.5)
        venting = int((clf_vent_model.predict(X_scaled)[0,0]) > 0.5)

        next_temp, next_humidity = simulate_next_conditions(
            cur_temp, ext_temp, cur_hum, ext_hum, heating, venting
        )

        predicted_temps.append(next_temp)
        predicted_heating.append(heating)
        predicted_venting.append(venting)

        cur_temp = next_temp
        cur_hum = next_humidity

    df_forecast = pd.DataFrame({
        "datetime": timestamps,
        "predicted_internal_temp": predicted_temps,
        "predicted_heating": predicted_heating,
        "predicted_venting": predicted_venting
    })

    return df_forecast