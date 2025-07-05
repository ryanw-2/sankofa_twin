from dataclasses import dataclass

@dataclass
class CropProfile:
    name: str
    min_temp: float  # °F
    max_temp: float
    min_humidity: float  # %
    max_humidity: float

CROP_PROFILES = {
    "Tomatoes": CropProfile("Tomatoes", min_temp=65, max_temp=85, min_humidity=60, max_humidity=80),
    "Lettuce": CropProfile("Lettuce", min_temp=55, max_temp=70, min_humidity=60, max_humidity=90),
    "Cucumbers": CropProfile("Cucumbers", min_temp=65, max_temp=85, min_humidity=60, max_humidity=90),
    "Peppers": CropProfile("Peppers", min_temp=65, max_temp=80, min_humidity=60, max_humidity=80),
    "Spinach": CropProfile("Spinach", min_temp=50, max_temp=70, min_humidity=60, max_humidity=85),
}

def get_crop_profile(crop_name: str) -> CropProfile:
    return CROP_PROFILES[crop_name]