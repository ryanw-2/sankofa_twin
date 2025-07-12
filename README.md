# 🌿 Greenhouse Resource Planner & Digital Twin Dashboard

![Dashboard Screenshot](dashboard-test.png)  
*A real-time dashboard that simulates greenhouse conditions and recommends energy-efficient actions for farmers.*

---

## 📌 Project Summary

This project builds a simulation-based dashboard to help local greenhouse farmers—especially those connected with the **Sankofa Village Community Farm** in Pittsburgh—optimize energy usage and climate control decisions based on weather forecasts.

By integrating weather data with a lightweight **digital twin model**, the dashboard forecasts internal greenhouse temperature and humidity, estimates energy usage and cost, and provides actionable insights tailored for resource-conscious growers.

---

## 🎯 Objectives

- 🧪 **Simulate greenhouse internal climate** based on real-time weather forecasts
- 💡 **Estimate energy usage and cost** under time-of-use (TOU) electricity rates
- 🛰️ **Provide data-driven recommendations** for when to heat or ventilate
- 🌱 **Support small-scale greenhouse farmers** like those in the Sankofa community
- 📊 **Visualize tradeoffs** between comfort, cost, and control actions

---

## 🧰 Tech Stack

| Layer         | Tool/Library                     |
|---------------|----------------------------------|
| 🌐 Dashboard   | [Streamlit](https://streamlit.io) for rapid web app development |
| 🧠 Simulator   | Python-based digital twin model simulating temperature + humidity |
| 🌦️ Weather API | [OpenWeatherMap](https://openweathermap.org/api) for hourly forecasts |
| ⚡ Energy Calc | Custom estimator using Duquesne Light TOU residential rates |
| 📈 Plotting     | Matplotlib for dual-axis temperature and energy charts |

---

## 🌍 Community Impact

This project is designed with the **Sankofa Village Community Farm** in mind—a local initiative focused on food justice, sustainability, and empowering Black growers in Pittsburgh.

By offering a free, transparent tool to simulate greenhouse operations, this project supports more efficient planning, cost savings, and informed decisions rooted in real data.

---

## 🧪 Features

- ✅ Weather-integrated simulator with real-time forecast
- ✅ Digital twin model for indoor temp + humidity
- ✅ Time-of-use energy pricing from Duquesne Light
- ✅ Custom rule-based heating/venting control
- ✅ Summary metrics + violation alerts
- ✅ Expandable for crop profiles and real-time control

---

## 🚀 Getting Started

```bash
pip install -r requirements.txt
streamlit run app.py
