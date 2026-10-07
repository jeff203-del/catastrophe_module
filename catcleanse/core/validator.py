"""Deterministic data quality checks and confidence scoring."""
from ..models.schemas import OEDLocation, AuditEntry
from .geocoder import in_kenya

def score_record(values, geocode_quality):
    """Apply specified deductions with floor at zero and return score plus review status."""
    score=1.0
    if geocode_quality == "UNKNOWN" or not in_kenya(values.get("latitude"),values.get("longitude")): score -= .30
    tiv=values.get("building_tiv_kes")
    if tiv is None or tiv <= 0: score -= .40
    if values.get("construction_code",9999)==9999: score -= .15
    if values.get("year_built") is None and values.get("stories") is None: score -= .15
    score=max(0.0,min(1.0,score))
    return round(score,3), ("REQUIRES_HUMAN_REVIEW" if score < .60 else "OK")

def build_location(locnum, parsed, values, audits, lat, lon, quality, flood):
    """Apply scoring and strict OED model validation; malformed values fail safely."""
    score,status=score_record({**values,"latitude":lat,"longitude":lon},quality)
    raw_name=values.get("loc_name") or values.get("address") or f"Location {locnum}"
    log=list(audits)
    for key,label in (("stories","NumberOfStories"),("year_built","YearBuilt")):
        item=getattr(parsed,key)
        if item.value is not None:
            log.append(AuditEntry(field=label,raw_value=item.value,cleaned_value=values.get(key),transformation_type="EXPLICIT_EXTRACTION",evidence=item.evidence,rationale=item.rationale))
    if quality != "UNKNOWN": log.append(AuditEntry(field="Geocode",raw_value=values.get("address"),cleaned_value=quality,transformation_type="OFFLINE_GEOCODE",evidence=values.get("address") or "",rationale="Resolved using Kenya-specific deterministic place dictionary."))
    return OEDLocation(LocNum=locnum, LocName=str(raw_name), Latitude=lat, Longitude=lon, GeocodeQuality=quality,
        OccupancyCode=values["occupancy_code"], ConstructionCode=values["construction_code"], NumberOfStories=values.get("stories"), YearBuilt=values.get("year_built"),
        BuildingTIV=values.get("building_tiv_kes") or 0.0, ContentsTIV=values.get("contents_tiv_kes") or 0.0, ConfidenceScore=score,
        High_Flood_Proximity_Flag=flood, ReviewStatus=status, DataCleansingAuditLog=log)
