"""Strict schemas for extracted, normalized and OED exposure records."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class AuditEntry(StrictModel):
    field: str
    raw_value: Any = None
    cleaned_value: Any = None
    standard_name: str | None = None
    transformation_type: str
    evidence: str = ""
    rationale: str = ""

class ExtractedField(StrictModel):
    value: Any = None
    evidence: str = ""
    rationale: str = ""

class ParsedExposure(StrictModel):
    loc_name: ExtractedField
    address: ExtractedField
    latitude: ExtractedField
    longitude: ExtractedField
    occupancy: ExtractedField
    construction: ExtractedField
    stories: ExtractedField
    year_built: ExtractedField
    building_tiv: ExtractedField
    contents_tiv: ExtractedField

class OEDLocation(StrictModel):
    LocNum: int = Field(ge=1)
    LocName: str
    Latitude: float | None = None
    Longitude: float | None = None
    GeocodeQuality: Literal["EXACT", "ESTATE_LEVEL", "SUBCOUNTY_LEVEL", "UNKNOWN"]
    OccupancyCode: int
    ConstructionCode: int
    NumberOfStories: int | None = Field(default=None, ge=1)
    YearBuilt: int | None = Field(default=None, ge=1800, le=2100)
    BuildingTIV: float = Field(ge=0)
    ContentsTIV: float = Field(default=0.0, ge=0)
    ConfidenceScore: float = Field(ge=0.0, le=1.0)
    High_Flood_Proximity_Flag: bool = False
    ReviewStatus: str = "OK"
    DataCleansingAuditLog: list[AuditEntry] = Field(default_factory=list)

    @field_validator("Latitude")
    @classmethod
    def valid_lat(cls, value):
        if value is not None and not -90 <= value <= 90: raise ValueError("Latitude outside WGS84 range")
        return value

    @field_validator("Longitude")
    @classmethod
    def valid_lon(cls, value):
        if value is not None and not -180 <= value <= 180: raise ValueError("Longitude outside WGS84 range")
        return value
