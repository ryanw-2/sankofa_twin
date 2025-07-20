# tests/test_greenhouse.py
import math
import pytest

from GreenhouseEngine import GreenhouseConfig, GreenhouseThermalEngine  # adapt import paths
from ThermalMass import ThermalMass                              # same here


# ------------------------------------------------------------------
# 1 · ThermalMass ---------------------------------------------------
# ------------------------------------------------------------------
def test_thermal_mass_heating_only():
    """
    100 kg mass, cp = 1000 J/kg-K.
    Inject 1 kW for one hour with zero air-mass temperature difference.
    Expected ΔT ≈ 3 600 000 J / (100 000 J/K) = 36 K.
    """
    m = ThermalMass(mass_kg=100, specific_heat=1000, initial_temp=20)
    new_T = m.update_temperature(heat_input_watts=1_000,
                                 air_temp=20, step_hours=1)
    assert math.isclose(new_T, 56, rel_tol=1e-2)


def test_thermal_mass_cools_toward_air():
    """
    No heat input; mass warmer than air → should cool.
    """
    m = ThermalMass(50, 1000, initial_temp=40)
    new_T = m.update_temperature(0, air_temp=20, step_hours=1)
    assert new_T < 40


# ------------------------------------------------------------------
# 2 · Heat-loss -----------------------------------------------------
# ------------------------------------------------------------------
class DummyCfg:
    """Minimal stub so we don't need full GreenhouseConfig."""
    wall_A = roof_A = floor_A = glazing_A = 1.0    
    wall_R = roof_R = floor_R = glazing_R = 1.0       
    volume_m3 = 1.0
    leak_ach  = 1.0

def make_engine(T_in=20):
    eng = GreenhouseThermalEngine.__new__(GreenhouseThermalEngine)
    eng.cfg = DummyCfg()        # use the 1 m² / 1 K W-1 stub
    eng.air_temp = T_in
    return eng


def test_heat_loss_zero_when_colder_outside_equal():
    eng = make_engine(T_in=20)
    assert eng.calculate_heat_loss(20, wind_m_s=0) == 0

def test_heat_loss_expected_value():
    """
    With areas/R = 1, ΔT = 10 K:
      conduction = 4 x 1 x 10 = 40 W
      infiltration: ṁ = V·ACH/3600·p = 1/3600·1.2 = 0.000333 kg/s
                    Q  = ṁ cp ΔT ≈ 0.000333 x 1005 x 10 ≈ 3.35 W
      total ≈ 43.35 W (no wind factor)
    """
    eng = make_engine(T_in=30)        
    q = eng.calculate_heat_loss(20, wind_m_s=0)
    assert math.isclose(q, 43.35, rel_tol=1e-2)


# ------------------------------------------------------------------
# 3 · Solar gain (monkey-patched pvlib) -----------------------------
# ------------------------------------------------------------------
@pytest.fixture
def monkeypatched_engine(monkeypatch):
    cfg = GreenhouseConfig(latitude=40, longitude=-80)
    eng = GreenhouseThermalEngine(cfg, T_air_init_C=20)

    # ➜ patch pvlib so POA is fixed at 500 W m-2
    monkeypatch.setattr(
        'pvlib.irradiance.get_total_irradiance',
        lambda *a, **kw: {'poa_global': 500}
    )
    return eng

def test_solar_gain_simple(monkeypatched_engine):
    eng = monkeypatched_engine
    gain = eng.calculate_solar_gain(
        ghi=800, dni=600, dhi=200, solar_zenith=45, solar_azimuth=180
    )
    expected = 500 * eng.cfg.glazing_A * eng.cfg.glazing_tau
    assert math.isclose(gain, expected, rel_tol=1e-6)

