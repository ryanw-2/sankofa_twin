# ── standard libs ────────────────────────────────────────────────────
from datetime import datetime
import pandas as pd
import streamlit as st
import altair as alt
# ── your project modules ─────────────────────────────────────────────
from GreenhouseEngine import GreenhouseConfig, GreenhouseThermalEngine
from forecast import get_geocode, get_hourly_forecast
from energy import get_rate, estimate_energy

# ─────────────────────────────────────────────────────────────────────
#  Cached simulation helper
# ─────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=True)
def run_sim(city: str, state: str, country: str, hrs: int = 24):
    lat, lon  = get_geocode(city, state, country)
    cfg       = GreenhouseConfig(lat, lon)
    engine    = GreenhouseThermalEngine(cfg, air_temp_init_C=20.0)

    forecast  = get_hourly_forecast(lat, lon, cfg, timezone="UTC").iloc[: hrs + 12]
    sim_df    = engine.simulate_step(
                    initial_air_temp  = 20.0,
                    initial_mass_temp = 20.0,
                    forecast_df       = forecast,
                    start_i           = 0,
                    steps             = hrs,
                    horizon           = 12,
                )

    sim_df = sim_df.join(forecast[["humidity"]])
    sim_df = sim_df.reset_index().rename(columns={"index": "datetime"})
    forecast = forecast.reset_index().rename(columns={"index": "datetime"})
    return sim_df, forecast


# ─────────────────────────────────────────────────────────────────────
#  Streamlit page config
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Greenhouse Thermal Twin",
    layout="wide",
    initial_sidebar_state="expanded",
)
alt.themes.enable("dark")

st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}

[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

</style>
""", unsafe_allow_html=True)
st.title("Greenhouse Thermal Twin")

# ── LEFT COLUMN ──────────────────────────────────────────────────────
with st.sidebar:
    st.title("Location")
    city    = st.text_input("City", "Pittsburgh")
    state   = st.text_input("State / Province", "PA")
    country = st.text_input("Country code", "US")
    hrs     = st.slider   ("Hours to simulate", 6, 24, 24, step=3)

    run_btn = st.button("Run simulation", use_container_width=True)

# When the button is pressed, stash results in session_state so they
# survive Streamlit’s re-runs and the other columns can access them.
if run_btn:
    with st.spinner("Fetching forecast & running engine …"):
        sim_df, fc_df = run_sim(city, state, country, hrs)

        # housekeeping for energy/cost
        sim_df["heating"] = sim_df["heater_on"].astype(int)
        sim_df["venting"] = sim_df["vent_ach"]          # leave ACH as-is
        sim_df, tot_kwh, tot_cost = estimate_energy(sim_df)

        st.session_state["sim_df"]   = sim_df
        st.session_state["fc_df"]    = fc_df
        st.session_state["tot_kwh"]  = tot_kwh
        st.session_state["tot_cost"] = tot_cost

        st.success("Simulation complete")

col_left, col_right = st.columns((1, 3), gap="medium") 
# ── MIDDLE COLUMN – metrics ─────────────────────────────────────────
with col_left:
    if "sim_df" in st.session_state:
        st.markdown("#### Session Cost")
        kwh   = st.session_state["tot_kwh"]
        cost  = st.session_state["tot_cost"]
        st.metric(label="Total energy (kWh)", value=f"{kwh:,.1f}")
        st.metric(label="Estimated cost (USD)", value=f"${cost:,.2f}")
    else:
        st.info("Run a simulation to see cost metrics.")

# ── RIGHT COLUMN – charts & table ───────────────────────────────────
with col_right:
    if "sim_df" in st.session_state:
        st.markdown("#### Simulated Results")
        sim_df = st.session_state["sim_df"]
        fc_df  = st.session_state["fc_df"]

        # Add exterior temp for plotting
        sim_df = sim_df.merge(
            fc_df[["datetime", "temp"]].rename(columns={"temp": "T_ext"}),
            on="datetime", how="left"
        )

        # 1 Temperatures
        st.subheader("Exterior vs. Predicted Interior Temperatures (°C)")
        st.line_chart(
            sim_df[["datetime", "T_air", "T_mass", "T_ext"]]
                 .set_index("datetime")
        )

        # 2 Ventilation / heater
        st.subheader("Ventilation (ACH) and Heater Status (0/1)")
        st.line_chart(
            sim_df[["datetime", "vent_ach", "heater_on"]]
                 .set_index("datetime")
        )

        # 3 Solar gain & weather in two horizontal columns
        st.subheader("Incoming solar power (W)")
        st.line_chart(sim_df[["datetime", "Q_solar"]]
                                .set_index("datetime"))

        fc_df = st.session_state["fc_df"]
        avg_wind  = fc_df["wind_speed"].mean()
        avg_hum   = fc_df["humidity"].mean()
        avg_cloud = fc_df["cloud_cover"].mean()
        t_max     = fc_df["temp"].max()
        t_min     = fc_df["temp"].min()

        st.metric("Avg. wind speed", f"{avg_wind:.1f} m/s")
        st.metric("Avg. humidity", f"{avg_hum:.0f} %")
        st.metric("Avg. cloud cover", f"{avg_cloud:.0f} %")
        st.metric("Temperature max/min", f"{t_max:.1f} ° / {t_min:.1f} °")
        
        # 4 Expandable raw table
        with st.expander("Show raw simulation table"):
            st.dataframe(sim_df, use_container_width=True)
