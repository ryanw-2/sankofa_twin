import numpy as np
from dataclasses import dataclass

@dataclass
class Predictive:
    C_J_K: float                 # lumped heat capacity  [J K⁻¹]
    U_W_K: float                 # conductance (UA)      [W K⁻¹]
    heater_W: float              # heater capacity       [W]
    vent_max_ach: float          # max vent rate         [h⁻¹]
    dt_hr: float = 1.0           # simulation time-step  [h]
    T_set: float = 18.0          # comfort set-point     [°C]
    deadband: float = 3.0        # ± band around set-point
    safety_margin: float = 0.5   # extra °C buffer

    _heater_state: bool = False  # remembers last heater ON/OFF

    min_on_steps = 3
    min_off_steps = 3
    _on_timer = 0
    _off_timer = 0

    def decide(self, air_temp, forecast_df):
        T_ext = forecast_df["temp"]
        Q_sol = forecast_df["Q_solar"]
        H = len(T_ext)
        dt_s = self.dt_hr * 3600
        alpha  = np.exp(-self.U_W_K * dt_s / self.C_J_K)

        # Simplified thermal physics prediction
        T_pred_off = np.empty(H)
        T_pred_off[0] = air_temp

        for k in range(1, H):
            net_W = (
                Q_sol[k-1] - self.U_W_K * (T_pred_off[k-1] - T_ext[k-1])
            )

            T_pred_off[k] = (
                T_ext[k-1] + 
                (T_pred_off[k-1] - T_ext[k-1]) * alpha +
                net_W * dt_s / self.C_J_K
            )
        
        low_band = self.T_set - self.deadband / 2 - self.safety_margin
        drop_idx = np.argmax(T_pred_off < low_band)
        need_heat: bool = bool(drop_idx != 0)

        # Warm up 
        tau = self.C_J_K / (self.U_W_K + self.heater_W / (self.T_set - T_ext.min() + 1e-6))
        lead_steps = int(np.ceil(tau / self.dt_hr))

        # decision
        heater_on: bool = need_heat and bool(drop_idx <= lead_steps)

        if self._heater_state:   # currently ON
            self._on_timer  += 1
            self._off_timer  = 0
            if self._on_timer < self.min_on_steps:
                heater_on = True
        else:                    # currently OFF
            self._off_timer += 1
            self._on_timer   = 0
            if self._off_timer < self.min_off_steps:
                heater_on = False

        if self._heater_state and air_temp > self.T_set + self.deadband / 2:
            heater_on = False
        
        if not self._heater_state and air_temp < self.T_set - self.deadband / 2:
            heater_on = True
        
        self._heater_state = heater_on
        part_load = 1.0 if heater_on else 0.0

        hi_band = self.T_set + self.deadband / 2 + 5
        above_mask  = T_pred_off > hi_band
        need_vent   = above_mask.any() 
        vent_ach = self.vent_max_ach if need_vent else 0.0

        return heater_on, part_load, vent_ach
