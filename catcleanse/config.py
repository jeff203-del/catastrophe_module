"""Configuration, spatial bounds and the supported OED code subset."""
from typing import Final

KENYA_BOUNDS: Final = {"lat_min": -4.7, "lat_max": 5.0, "lon_min": 33.9, "lon_max": 41.9}
OCCUPANCY_CODES: Final = {"commercial": 1050, "single family residential": 1010, "multi-family residential": 1020, "apartment": 1020, "apartments": 1020, "industrial": 1060}
CONSTRUCTION_CODES: Final = {"reinforced concrete": 5000, "masonry": 5050, "timber": 5100, "wood": 5100, "steel frame": 5200, "unknown": 9999}
CURRENCY_KES_PER_UNIT: Final = {"KES": 1.0, "KSH": 1.0, "USD": 130.0}
