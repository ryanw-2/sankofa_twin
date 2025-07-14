import streamlit as st
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
import matplotlib.pyplot as plt
from forecast import get_hourly_forecast, get_geocode
from twin import simulate_internal_temp, forecast_n_hours_ahead
from advice import always_heat_at_night, vent_if_hot
from energy import estimate_energy
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
import joblib

reg_model = tf.keras.models.load_model("./notebooks/models/regression_model.keras")
clf_heat_model = tf.keras.models.load_model("./notebooks/models/classifier_heat_model.keras")
clf_vent_model = tf.keras.models.load_model("./notebooks/models/classifier_vent_model.keras")
scaler = joblib.load("./notebooks/models/scaler.pkl")
features = ["external_temp", "external_humidity", "internal_temp", "internal_humidity", "heating", "venting"]
st.set_page_config(page_title="Greenhouse Twin Dashboard", layout="wide")
st.title("Greenhouse Resource Planner")
st.subheader("Simulated Greenhouse Temperature using Digital Twin")

# --- User Input ---
city = st.text_input("Enter city", "Pittsburgh")
state = st.text_input("Enter state (2-letter code)", "PA")
country = st.text_input("Enter country (2-letter code)", "US")

# --- Get forecast and simulate ---
if st.button("Simulate Greenhouse"):
    try:
        # Generate synthetic data

        # Get coordinates
        latitude, longitude = get_geocode(city, state, country)
        st.success(f"Location: {city}, Lat: {latitude:.2f}, Lon: {longitude:.2f}")

        # Get forecast
        count = 24
        forecast_df = get_hourly_forecast(latitude, longitude, count)

        external_temp_forecast = forecast_df["temp"].values[:count]
        external_humidity_forecast = forecast_df["humidity"].values[:count]

        predicted_forecast_df = forecast_n_hours_ahead(
            count,
            start_internal_temp=68,
            start_internal_humidity=70,
            external_temp_forecast=external_temp_forecast,
            external_humidity_forecast=external_humidity_forecast,
            clf_heat_model=clf_heat_model,
            clf_vent_model=clf_vent_model,
            scaler=scaler,
            features=features
        )

        # Run Regression and Classifier simulation
        fig, ax = plt.subplots(figsize=(8,4))
        ax.plot(forecast_df["datetime"], forecast_df["predicted_internal_temp"], label="Predicted Internal Temp")
        ax.set_title("Forecast: Internal Temp Next 12 Hours")
        ax.set_xlabel("Time")
        ax.set_ylabel("Temperature (°F)")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig)

        st.subheader("Predicted Heating & Venting Actions")
        st.dataframe(forecast_df[["datetime", "predicted_heating", "predicted_venting"]])


        # Run digital twin simulation
        sim_df = simulate_internal_temp(
            forecast_df,
            initial_temp=68.0,
            internal_humidity=70.0,
            heating_fn=always_heat_at_night,
            venting_fn=vent_if_hot
        )

        sim_df, energy_cost = estimate_energy(sim_df)
        total_kwh = sim_df["energy_kwh"].sum()
        total_cost = energy_cost

        most_expensive_row = sim_df.loc[sim_df["energy_cost"].idxmax()]
        most_expensive_time = most_expensive_row["datetime"].strftime("%A, %I:%M %p")
        most_expensive_cost = most_expensive_row["energy_cost"]

        st.metric("🔌 Total Energy Used (kWh)", f"{total_kwh:.2f}")
        st.metric("💰 Total Energy Cost", f"${total_cost:.2f}")

        # --- Plotting ---
        st.subheader("🌡️ Temperature Forecast and Simulation")

        fig, ax1 = plt.subplots(figsize=(10, 5))

        # Primary y-axis: Temperature
        ax1.plot(sim_df["datetime"], sim_df["external_temp"], label="External Temp", color="skyblue")
        ax1.plot(sim_df["datetime"], sim_df["internal_temp"], label="Internal Temp (Simulated)", color="orange")
        ax1.set_ylabel("Temperature (°F)", color="black")
        ax1.tick_params(axis="y", labelcolor="black")

        # Create secondary y-axis
        ax2 = ax1.twinx()
        ax2.bar(sim_df["datetime"], sim_df["energy_kwh"], width=0.03, label="Energy Usage (kWh)", color="lightgreen", alpha=0.3)
        ax2.set_ylabel("Energy Usage (kWh/hour)", color="green")
        ax2.tick_params(axis="y", labelcolor="green")

        # Title and layout
        fig.suptitle("Greenhouse Simulation: Temperature and Energy Usage", fontsize=14)
        ax1.set_xlabel("Time")
        fig.autofmt_xdate()

        # Combine legends from both axes
        lines_1, labels_1 = ax1.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper left")
        st.pyplot(fig)

        """
        ---
        """

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(sim_df["datetime"], sim_df["external_humidity"], label="External Humidity", color="green")
        ax.plot(sim_df["datetime"], sim_df["internal_humidity"], label="Internal Humidity (Simulated)", color="yellow")
        ax.set_title("Greenhouse Humidity Simulation")
        ax.set_xlabel("Time")
        ax.set_ylabel("Humidity (%)")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig)


        st.markdown(f"""
        **💡 Usage Summary:**
        - The highest-cost hour was **{most_expensive_time}**, costing **${most_expensive_cost:.2f}**.
        - Total estimated cost for the period is **${total_cost:.2f}** across **{len(sim_df)} hours**.
        """)

        with st.expander("View simulation data"):
            st.dataframe(sim_df)

    except Exception as e:
        st.error(f"Something went wrong: {e}")