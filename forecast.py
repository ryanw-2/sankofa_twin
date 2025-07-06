import os
import requests
import pandas as pd
from dotenv import load_dotenv

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

def get_current_weather(my_lat:float, my_lon:float):
    if not WEATHER_API_KEY:
        raise ValueError("API key not found. Check .env file")

    params = {
        "lat": my_lat,
        "lon":my_lon,
        "appid":WEATHER_API_KEY,
        "units":"imperial"
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
            "weather": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "rain": rain_val,
        }
    )    

    df = pd.DataFrame(current_weather)
    df["datetime"] = pd.to_datetime(df["datetime"], unit="s")
    df["datetime"] = df["datetime"].dt.tz_localize("UTC")
    df["datetime"] = df["datetime"].dt.tz_convert("US/Pacific")

    return df

def get_hourly_forecast(my_lat:float, my_lon:float, count=24):
    if not WEATHER_API_KEY:
        raise ValueError("API key not found. Check .env file")

    params = {
        "lat":my_lat,
        "lon":my_lon,
        "appid":WEATHER_API_KEY,
        "cnt": count,
        "units": "imperial"
    }

    response = requests.get(FORECAST_BASE_URL, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.json()}")
    
    data = response.json()

    forecast_weather = []   
    for entry in data["list"]:
        rain_val = -1
        if has_value(entry, "rain"):
            rain_val = entry["rain"]["1h"]

        forecast_weather.append({
            "datetime": entry["dt"],
            "temp": entry["main"]["temp"],
            "humidity": entry["main"]["humidity"],
            "wind_speed": entry["wind"]["speed"],
            "weather": entry["weather"][0]["main"],
            "description": entry["weather"][0]["description"],
            "rain": rain_val,           
        })
    
    df = pd.DataFrame(forecast_weather)
    df["datetime"] = pd.to_datetime(df["datetime"], unit="s")
    df["datetime"] = df["datetime"].dt.tz_localize("UTC")
    df["datetime"] = df["datetime"].dt.tz_convert("US/Pacific")

    return df

# latitude, longitude = get_geocode("San Jose", "CA", "US")
# df = get_hourly_forecast(latitude, longitude)
# print(f"entry:{df}")