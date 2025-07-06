def always_heat_at_night(dt):
    return dt.hour < 7 or dt.hour > 20

def vent_if_hot(dt):
    return 12 <= dt.hour <= 16  # midday hours