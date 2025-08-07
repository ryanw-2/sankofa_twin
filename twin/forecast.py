import os
import requests
import pandas as pd
from dotenv import load_dotenv
import pvlib
from datetime import datetime, timedelta
from typing import cast
import numpy as np
import math

load_dotenv()
WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

FORECAST_BASE_URL = "https://pro.openweathermap.org/data/2.5/forecast/hourly?"
WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather?"
GEOCODE_BASE_URL = "http://api.openweathermap.org/geo/1.0/direct?"

def has_value(json, key:str):
    """
    Helper to check if a key has a value in the JSON response.
    """
    return json.get(key) is not None

def get_geocode(city:str, state:str, country:str):
    """
    Helper to get the latitude and longitude of the selected city.
    """
    params = {
        "q": (city, state, country),
        "appid": WEATHER_API_KEY,
        "limit":1
    }

    response = requests.get(GEOCODE_BASE_URL, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.json()}")
        
    data = response.json()
    return (data[0]["lat"], data[0]["lon"])

def get_current_weather(my_lat:float, my_lon:float, timezone:str):
    if not WEATHER_API_KEY:
        raise ValueError("API key not found. Check .env file")

    params = {
        "lat": my_lat,
        "lon":my_lon,
        "appid":WEATHER_API_KEY,
        "units":"metric"
    }

    response = requests.get(WEATHER_BASE_URL, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.json()}")
    
    data = response.json()


    current_weather = []
    rain_val = -1
    if has_value(data, "rain"):
        rain_val = data["rain"]["1h"]

    current_weather.append(
        {
            "datetime": data["dt"],
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "cloud_cover": data["clouds"]["all"],
            "weather": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "rain": rain_val,
        }
    )    

    df = pd.DataFrame(current_weather)
    df["datetime"] = pd.to_datetime(df["datetime"], unit="s")
    df["datetime"] = df["datetime"].dt.tz_localize("UTC")
    df["datetime"] = df["datetime"].dt.tz_convert(timezone)

    return df

def get_hourly_solar(my_lat, my_lon, weather_df, cfg, timezone:str, count:int = 24):
    now   = pd.Timestamp.now(timezone) 
    start = (now + pd.Timedelta(hours=1)).floor("h")   
    times_local = pd.date_range(start=start,
                                periods=count,        
                                freq="h",
                                tz=timezone)

    sol = pvlib.solarposition.get_solarposition(times_local.tz_convert("UTC"), my_lat, my_lon)
    sol = cast(pd.DataFrame, sol)
    sol = sol.tz_convert(timezone)

    site = pvlib.location.Location(my_lat, my_lon,
                                   tz=timezone,
                                   altitude=250) ## hardcoded for pittsburgh
    
    clearsky = site.get_clearsky(times_local.tz_convert("UTC"))
    sky_df = cast(pd.DataFrame, clearsky)
    sky_df = sky_df.tz_convert(timezone)
    
    cloud_frac = (
        weather_df.reindex(times_local)["cloud_cover"]
        .to_numpy(dtype=float) / 100.0
    )

    # Simple empirical factor (WMO, Duffie-Beckman): (1-0.75·CF^3)
    trans = 1.0 - 0.75 * cloud_frac**3
    trans = np.clip(trans, 0.0, 1.0)

    ghi_adj = clearsky["ghi"].to_numpy() * trans

    zen = sol["apparent_zenith"].to_numpy()
    ghi_series = pd.Series(ghi_adj, index=times_local)

    erbs = pvlib.irradiance.erbs(ghi_series, zen, times_local)
    dni_adj = erbs["dni"].to_numpy()
    dhi_adj = erbs["dhi"].to_numpy()

    solar_df = pd.DataFrame(
        {
            "apparent_zenith": zen,
            "azimuth": (sol["azimuth"].to_numpy() % 360),
            "ghi": ghi_adj,
            "dni": dni_adj,
            "dhi": dhi_adj,
        },
        index=times_local,
    )

    ALBEDO = 0.20
    poa_comp = pvlib.irradiance.get_total_irradiance(
        surface_tilt   = cfg.surface_tilt_deg,
        surface_azimuth= cfg.orientation,
        dni            = solar_df["dni"],
        ghi            = solar_df["ghi"],
        dhi            = solar_df["dhi"],
        solar_zenith   = solar_df["apparent_zenith"],
        solar_azimuth  = solar_df["azimuth"],
        albedo         = ALBEDO,
    )["poa_global"]

    area_m2 = cfg.glazing_A * cfg.glazing_tau
    solar_df["Q_solar"] = poa_comp * area_m2

    solar_df.index.name = "datetime"
    return solar_df

def get_hourly_weather(my_lat:float, my_lon:float, timezone:str, count=24):
    if not WEATHER_API_KEY:
        raise ValueError("API key not found. Check .env file")

    params = {
        "lat":my_lat,
        "lon":my_lon,
        "appid":WEATHER_API_KEY,
        "cnt": count,
        "units": "metric"
    }

    response = requests.get(FORECAST_BASE_URL, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.json()}")
    
    data = response.json()

    forecast_weather = []   
    for entry in data["list"]:
        rain_val = 0
        if has_value(entry, "rain"):
            rain_val = entry["rain"]["1h"]

        forecast_weather.append({
            "datetime": entry["dt"],
            "temp": entry["main"]["temp"],
            "humidity": entry["main"]["humidity"],
            "wind_speed": entry["wind"]["speed"],
            "cloud_cover": entry["clouds"]["all"],
            "weather": entry["weather"][0]["main"],
            "description": entry["weather"][0]["description"],
            "rain": rain_val,           
        })
    
    df = pd.DataFrame(forecast_weather)
    df["datetime"] = pd.to_datetime(df["datetime"], unit="s")
    df["datetime"] = df["datetime"].dt.tz_localize("UTC")
    df["datetime"] = df["datetime"].dt.tz_convert(timezone)

    return df

def get_hourly_forecast(my_lat, my_lon, cfg, timezone, count=24):
    weather_df = get_hourly_weather(my_lat, my_lon, timezone, count).set_index("datetime")
    solar_df = get_hourly_solar(my_lat, my_lon, weather_df, cfg, timezone, count)
    
    combined_df = weather_df.join(solar_df, how="left")
    return combined_df


latitude, longitude = get_geocode("Pittsburgh", "PA", "US")
test_df = get_hourly_weather(latitude, longitude, "US/Eastern")
print(test_df)