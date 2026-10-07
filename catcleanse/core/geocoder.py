"""Offline Kenya resolver, bounds checks, and conservative flood-proximity flags."""
import re
from ..config import KENYA_BOUNDS

ESTATES = {
 "westlands": (-1.267,36.811), "kilimani": (-1.292,36.787), "upper hill": (-1.300,36.815),
 "cbd": (-1.286,36.817), "central business district": (-1.286,36.817), "south c": (-1.321,36.829),
 "south b": (-1.316,36.833), "eastleigh": (-1.279,36.847), "karen": (-1.319,36.707),
 "runda": (-1.205,36.805), "industrial area": (-1.315,36.850), "thika road": (-1.230,36.875),
}
SUBCOUNTIES = {"dagoretti":(-1.300,36.750), "langata":(-1.350,36.750), "embakasi":(-1.300,36.900), "kasarani":(-1.220,36.900), "mathare":(-1.250,36.850), "starehe":(-1.275,36.825), "westlands":(-1.250,36.800)}
FLOOD_KEYWORDS = ("nairobi river", "ngong river", "south c flood", "flood basin")

def in_kenya(lat, lon):
    try: return lat is not None and lon is not None and KENYA_BOUNDS["lat_min"] <= float(lat) <= KENYA_BOUNDS["lat_max"] and KENYA_BOUNDS["lon_min"] <= float(lon) <= KENYA_BOUNDS["lon_max"]
    except (TypeError,ValueError): return False

def resolve(address, lat=None, lon=None):
    """Prefer valid supplied coordinates, otherwise resolve Nairobi names offline."""
    if in_kenya(lat,lon): return float(lat),float(lon),"EXACT"
    text=str(address or "").lower()
    for name,(a,b) in ESTATES.items():
        if name in text: return a,b,"ESTATE_LEVEL"
    for name,(a,b) in SUBCOUNTIES.items():
        if name in text: return a,b,"SUBCOUNTY_LEVEL"
    # Optional online fallback is explicitly opt-in to keep default processing deterministic/offline.
    if text and __import__("os").getenv("CATCLEANSE_NOMINATIM") == "1":
        try:
            from geopy.geocoders import Nominatim
            loc=Nominatim(user_agent="catcleanse-kenya-exposure", timeout=5).geocode(text + ", Kenya")
            if loc and in_kenya(loc.latitude,loc.longitude): return float(loc.latitude),float(loc.longitude),"ESTATE_LEVEL"
        except Exception: pass
    return None,None,"UNKNOWN"

def flood_flag(address, lat=None, lon=None):
    """Flag explicit basin/river evidence, plus the South C neighborhood centroid."""
    text=str(address or "").lower()
    return any(k in text for k in FLOOD_KEYWORDS) or "south c" in text
