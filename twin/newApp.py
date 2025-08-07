import streamlit as st
import pandas as pd
import altair as alt
from GreenhouseEngine import GreenhouseConfig, GreenhouseThermalEngine
from forecast import get_geocode, get_hourly_forecast
from energy import get_rate, estimate_energy

# -----------------------------------------------------------------------------
# Cached simulation helper (returns sim + raw forecast) ------------------------
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def run_sim(city: str, state: str, country: str, hrs: int = 24):
    """Fetch forecast, run engine, return (sim_df, forecast_df)."""
    lat, lon = get_geocode(city, state, country)
    cfg      = GreenhouseConfig(lat, lon)
    engine   = GreenhouseThermalEngine(cfg, air_temp_init_C=20.0)

    forecast_df = get_hourly_forecast(lat, lon, cfg, timezone="UTC").iloc[: hrs + 12]

    sim_df = engine.simulate_step(
        initial_air_temp = 20.0,
        initial_mass_temp = 20.0,
        forecast_df = forecast_df,
        start_i = 0,
        steps = hrs,
        horizon = 12,
    )

    # Merge humidity for later plots
    sim_df = sim_df.join(forecast_df[["humidity"]])
    sim_df = sim_df.reset_index().rename(columns={"index": "datetime"})
    forecast_df = forecast_df.reset_index().rename(columns={"index": "datetime"})
    return sim_df, forecast_df

# -----------------------------------------------------------------------------
# Streamlit UI -----------------------------------------------------------------
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Greenhouse Thermal Twin",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Greenhouse Thermal Twin")

st.sidebar.header("Location & options")
city    = st.sidebar.text_input("City", "Pittsburgh")
state   = st.sidebar.text_input("State / Province", "PA")
country = st.sidebar.text_input("Country code", "US")
hrs     = st.sidebar.slider("Hours to simulate", 6, 48, 24, step=6)

if st.sidebar.button("Run simulation"):
    with st.spinner("Fetching forecast & running engine …"):
        sim_df, fc_df = run_sim(city, state, country, hrs)

    st.success("Simulation complete")

    # ---------------------------------------------------------------------
    # Primary chart – temps + vent rate
    # ---------------------------------------------------------------------
    sim_df = sim_df.merge(
        fc_df[["datetime", "temp"]].rename(columns={"temp": "T_ext"}),
        on="datetime",
        how="left"
    )

    primary = sim_df[["datetime", "T_air", "T_mass", "T_ext"]].copy()
    st.subheader("Exterior vs. Predicted Interior Temperatures (°C)")
    st.line_chart(primary.set_index("datetime"))

    status = sim_df[["datetime", "vent_ach", "heater_on"]].copy()
    status["vent_ach"]   = status["vent_ach"]              # keep true ACH (0–3)
    status["heater_on"]  = status["heater_on"].astype(int) # stays 0 / 1

    status_long = status.melt("datetime", var_name="Metric", value_name="Value")

    st.subheader("Venting (ACH) and Heater Status (0/1)")
    st.line_chart(status_long, x="datetime", y="Value", color="Metric")

    # ---------------------------------------------------------------------
    # Secondary charts – solar gain and outdoor weather
    # ---------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Incoming solar power (W)")
        st.line_chart(sim_df[["datetime", "Q_solar"]].set_index("datetime"))

    with col2:
        st.subheader("Outdoor weather")
        weather_cols = [c for c in fc_df.columns if c in ("temp", "wind_speed", "humidity")]
        st.line_chart(fc_df.set_index("datetime")[weather_cols])

    # ---------------------------------------------------------------------
    # Data table expander
    # ---------------------------------------------------------------------
    with st.expander("Show raw simulation table"):
        st.dataframe(sim_df, use_container_width=True)
else:
    st.info("Enter a location and click **Run simulation** to begin.")
