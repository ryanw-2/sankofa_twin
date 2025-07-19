def __init__(self):
    # Dimensions (feet) - Based on architectural scale and proportions
    self.length = 32  # Estimated from drawing proportions
    self.width = 24   # Estimated from drawing proportions  
    self.height = 12  # Peak height including arch structure
    self.sidewall_height = 8  # Height to spring of arch
    self.orientation = 135  # Southeast orientation as shown in drawings
    
    # Construction materials - Based on specified materials in drawings
    # Palram Sunlite 8mm twin-wall polycarbonate specifications
    self.wall_r_value = 1.8  # ft²·°F·hr/BTU (8mm twin-wall polycarbonate)
    self.roof_r_value = 1.8  # Same material for walls and roof
    self.foundation_r_value = 8.0  # Cast-in-place concrete with insulation
    self.glazing_r_value = 1.8  # Twin-wall polycarbonate (better than single, less than double glass)
    
    # Thermal properties of polycarbonate
    self.glazing_u_factor = 0.56  # BTU/hr·ft²·°F (inverse of R-value)
    self.solar_heat_gain_coefficient = 0.65  # For clear polycarbonate
    self.light_transmission = 0.80  # 80% as specified in drawings
    
    # Surface areas (calculated based on arch geometry)
    # Arch increases surface area compared to rectangular structure
    self.arch_factor = 1.15  # 15% increase due to curved arch profile
    self.wall_area = 2 * (self.length + self.width) * self.sidewall_height
    self.roof_area = self.length * self.width * self.arch_factor  # Increased for arch
    self.foundation_area = self.length * self.width
    self.glazing_area = self.wall_area + self.roof_area  # Fully glazed structure
    
    # Thermal mass - Based on concrete footings and bamboo structure
    # Concrete footings: estimated 8 footings, 2'x2'x3' each = 96 ft³
    concrete_volume_ft3 = 96
    concrete_density_lb_ft3 = 150
    concrete_mass_kg = concrete_volume_ft3 * concrete_density_lb_ft3 * 0.453592  # Convert to kg
    
    # Bamboo structure thermal mass (minimal but included)
    bamboo_mass_kg = 200  # Estimated bamboo culm and strut mass
    
    # Soil thermal mass (important for ground-coupled greenhouse)
    soil_volume_ft3 = self.foundation_area * 2  # 2 feet of soil depth influence
    soil_density_lb_ft3 = 100
    soil_mass_kg = soil_volume_ft3 * soil_density_lb_ft3 * 0.453592 * 0.3  # 30% coupling
    
    self.thermal_mass_kg = concrete_mass_kg + bamboo_mass_kg + soil_mass_kg  # ~4200 kg total
    self.specific_heat = 920  # J/kg·K (weighted average of concrete, bamboo, soil)
    
    # Ventilation - Based on natural cross-ventilation design
    # Natural ventilation through roof vents and side openings
    self.air_changes_per_hour = 2.0  # Higher due to natural convection design
    self.natural_ventilation_area = 0.08 * self.glazing_area  # 8% vent area to floor area ratio
    
    # Infiltration (separate from intentional ventilation)
    self.infiltration_ach = 0.3  # Moderate infiltration for polycarbonate panels
    
    # Heating system - Sized for climate zone and structure
    # Heat loss calculation: U × A × ΔT for all surfaces
    design_temp_diff = 70  # °F (20°F outside, 90°F inside for tropical plants)
    
    # Heat loss through envelope
    wall_loss = (1/self.wall_r_value) * self.glazing_area * design_temp_diff
    foundation_loss = (1/self.foundation_r_value) * self.foundation_area * design_temp_diff
    
    # Ventilation heat loss
    cfm_per_ach = (self.length * self.width * self.height) / 60  # ft³/min per ACH
    ventilation_loss = 1.08 * cfm_per_ach * self.air_changes_per_hour * design_temp_diff
    
    total_heat_loss = wall_loss + foundation_loss + ventilation_loss
    safety_factor = 1.3  # 30% safety margin
    
    self.heater_btu_per_hour = int(total_heat_loss * safety_factor)  # ~55,000 BTU/hr
    self.heater_efficiency = 0.90  # High-efficiency unit for greenhouse application
    
    # Solar gain calculations
    self.peak_solar_gain_btu_hr = (
        self.glazing_area * 
        self.solar_heat_gain_coefficient * 
        250  # Peak solar irradiance BTU/hr·ft²
    )
    
    # Structural properties affecting thermal performance
    self.bamboo_thermal_bridging = True  # Bamboo conducts less than steel
    self.foundation_type = "concrete_slab_on_grade"
    self.vapor_barrier = True  # Important for humidity control
    
    # Climate control parameters
    self.target_humidity = 0.65  # 65% RH optimal for most greenhouse crops
    self.co2_enrichment = 1200  # ppm during daylight hours
    self.ventilation_trigger_temp = 78  # °F - when natural vents open
    
    # Crop-specific environmental parameters (from PPFD analysis)
    self.target_ppfd_zones = {
        'high_light': (600, 740),    # μmol/m²/s - center area
        'medium_high': (400, 600),   # μmol/m²/s - mid zones  
        'medium': (300, 400),        # μmol/m²/s - edge zones
        'low': (150, 300)            # μmol/m²/s - propagation areas
    }
    
    # Seasonal adjustments
    self.summer_ventilation_multiplier = 3.0  # Increase ACH in summer
    self.winter_thermal_mass_coupling = 0.8   # Reduced ground coupling in winter
    
    # Energy efficiency features
    self.thermal_curtain_r_value = 4.0  # Optional night curtain system
    self.heat_recovery_efficiency = 0.0  # No HRV in natural ventilation design
    
    # Maintenance and operational parameters
    self.glazing_degradation_factor = 0.02  # 2% light loss per year
    self.insect_screen_reduction = 0.85     # 15% airflow reduction with screens