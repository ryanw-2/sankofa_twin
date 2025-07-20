# Greenhouse Thermal Model

**Constant & Configuration Reference (SI Units)**

---

## 1 · Global Constants

| Name / Symbol                  | Default   | Meaning                                                 | Unit           |
| ------------------------------ | --------- | ------------------------------------------------------- | -------------- |
| **CONCRETE\_DENSITY\_KG\_M3**  | 2 400     | Density of cast concrete                                | kg · m⁻³       |
| **SOIL\_DENSITY\_KG\_M3**      | 1 600     | Typical mineral soil density                            | kg · m⁻³       |
| **SOIL\_COUPLING\_FACTOR**     | 0.30      | Fraction of sub-soil mass coupled to air each hour      | —              |
| **BAMBOO\_MASS\_KG**           | 200       | Extra sensible storage (benches, plants, barrels, etc.) | kg             |
| **SPECIFIC\_HEAT\_J\_PER\_KG** | 920       | Mean $c_p$ of concrete / soil                           | J · kg⁻¹ · K⁻¹ |
| **ARCH\_FACTOR**               | 1.15      | Curved-roof area ÷ plan-roof area                       | —              |
| **GLAZING\_U\_VALUE**          | 3.2       | Overall $U$ of single glazing incl. films               | W · m⁻² · K⁻¹  |
| **SOLAR\_HEAT\_GAIN\_COEFF**   | 0.65      | SHGC of glazing                                         | —              |
| **LIGHT\_TRANSMISSION**        | 0.80      | Visible & total solar transmittance                     | —              |
| **ALBEDO**                     | 0.20      | Ground reflectance (short-wave)                         | —              |
| **R\_IP\_TO\_SI**              | 5.678 263 | Convert ft² · h · °F · BTU⁻¹ → m² · K · W⁻¹             | —              |

---

## 2 · `GreenhouseConfig` Attributes

| Attribute              | Derived from / Comment            | Typical (default geometry) | Role                                | Unit                |
| ---------------------- | --------------------------------- | -------------------------- | ----------------------------------- | ------------------- |
| **latitude**           | user input                        | e.g. 40.4                  | Solar-position calc                 | ° N                 |
| **longitude**          | user input                        | –80.0                      | Solar-position calc                 | ° E (positive east) |
| **length**             | 37.67 ft × 0.3048                 | **11.48**                  | Internal length                     | m                   |
| **width**              | 18.95 ft × 0.3048                 | **5.78**                   | Internal width                      | m                   |
| **height (ridge)**     | 12 ft →                           | **3.66**                   | Peak height                         | m                   |
| **sidewall**           | 8 ft →                            | **2.44**                   | Straight-wall height                | m                   |
| **orientation**        | drawing                           | **135**                    | Azimuth of long-wall normal (0 = N) | °                   |
| **surface\_tilt\_deg** | fixed                             | **90**                     | Tilt of vertical glazing            | °                   |
| **glazing\_tau**       | constant                          | **0.78**                   | Short-wave transmittance            | —                   |
| **wall\_A**            | geom.                             | **≈ 158**                  | Area of 4 walls                     | m²                  |
| **roof\_A**            | plan × ARCH\_FACTOR               | **≈ 76**                   | Curved roof area                    | m²                  |
| **floor\_A**           | L × W                             | **≈ 66**                   | Soil contact area                   | m²                  |
| **glazing\_A**         | wall + roof                       | **≈ 234**                  | Total transparent area              | m²                  |
| **volume\_m3**         | prism + gable                     | **≈ 217**                  | Air volume                          | m³                  |
| **wall\_R**            | 1.8 IP / R\_IP\_TO\_SI            | **0.317**                  | Wall resistance                     | m² · K · W⁻¹        |
| **roof\_R**            | ”                                 | **0.317**                  | Roof resistance                     | m² · K · W⁻¹        |
| **floor\_R**           | 8.0 IP / R\_IP\_TO\_SI            | **1.41**                   | Slab-to-ground R                    | m² · K · W⁻¹        |
| **glazing\_R**         | 1 / GLAZING\_U                    | **0.312**                  | Glazing R                           | m² · K · W⁻¹        |
| **leak\_ach**          | rule of thumb                     | **0.30**                   | Natural infiltration (closed)       | h⁻¹                 |
| **design\_vent\_ach**  | design                            | **2.0**                    | Vent ACH (full open)                | h⁻¹                 |
| **mass\_kg**           | concrete + soil × factor + bamboo | **≈ 7 000**                | Lumped thermal mass                 | kg                  |
| **mass\_c\_p**         | constant                          | **920**                    | Specific heat of mass               | J · kg⁻¹ · K⁻¹      |
| **design\_dT**         | user                              | **20**                     | ΔT for heater sizing                | K                   |
| **heater\_W**          | calc with safety 1.3              | **≈ 22 000**               | Nominal heater capacity             | W                   |

---

### 3 · How These Values Enter the Physics

* **Solar gain**   $Q_{\text{solar}} = \text{POA} × \text{glazing\_A} × \text{glazing\_tau}$
* **Conduction loss**   $Q_{\text{cond}} = \sum \dfrac{A_i}{R_i} ΔT$
* **Infiltration loss**   $Q_{\text{inf}} = \left(\dfrac{\text{volume\_m³} × \text{ACH}}{3600}\right)ρ_{air}c_p ΔT$
* **Heating input**   $Q_{\text{heat}} = \text{heater\_on} × \text{heater\_W}$
* **Thermal-mass ΔT**   $ΔT_{mass} = \dfrac{E}{\text{mass\_kg} × \text{mass\_c\_p}}$

