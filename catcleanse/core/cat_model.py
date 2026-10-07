"""Transparent deterministic Nairobi flood loss model using challenge data."""
from __future__ import annotations
import math
from pathlib import Path
import pandas as pd
from .geocoder import ESTATES

HAZARD_TIERS = {
    "Common": ("hazard_score_common", 2),
    "Occasional": ("hazard_score_occasional", 5),
    "Moderate": ("hazard_score_moderate", 10),
    "Severe": ("hazard_score_severe", 50),
    "Extreme": ("hazard_score_extreme", 100),
}
DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data" / "team_a_nairobi"


def load_challenge_exposure(path=None):
    """Load validated starter kit synthetic locations and joined hazard proxies."""
    frame = pd.read_csv(path or DEFAULT_DATA / "exposure_nairobi_with_hazard.csv")
    required = {"loc_id", "lat", "lon", "housing_class", "tiv_kes", "synthetic"}
    required.update(column for column, _ in HAZARD_TIERS.values())
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing challenge columns: {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError("Challenge exposure file is empty")
    frame = frame.copy()
    for column in ["lat", "lon", "tiv_kes", *(col for col, _ in HAZARD_TIERS.values())]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["lat", "lon", "tiv_kes"])
    frame = frame[(frame.tiv_kes >= 0) & frame.lat.between(-1.5, -1.0) & frame.lon.between(36.5, 37.2)]
    if frame.empty:
        raise ValueError("No valid Nairobi exposure rows remain")
    for column, _ in HAZARD_TIERS.values():
        frame[column] = frame[column].fillna(0).clip(0, 1)
    frame["synthetic"] = frame["synthetic"].astype(str).str.lower().isin(("true", "1", "yes"))
    return frame.reset_index(drop=True)


def _neighborhood(lat, lon):
    """Return nearest offline estate centroid; this is an approximate label."""
    def distance(point):
        a, b = point
        return 111.0 * math.hypot(lat - a, (lon - b) * math.cos(math.radians(lat)))
    return min(ESTATES, key=lambda name: distance(ESTATES[name])).title()


def _damage_ratio(depth_m, housing_class):
    """Illustrative, uncalibrated piecewise damage curve, capped by class."""
    caps = {"semi_permanent": 0.90, "informal_iron_sheet": 0.95,
            "permanent": 0.80, "masonry": 0.80, "apartment": 0.75}
    cap = next((v for key, v in caps.items() if key in str(housing_class).lower()), 0.80)
    anchors = ((0.0, 0.0), (0.1, 0.03), (0.3, 0.12), (0.6, 0.30),
               (1.0, 0.52), (2.0, 0.72), (4.0, cap))
    for (d0, r0), (d1, r1) in zip(anchors, anchors[1:]):
        if depth_m <= d1:
            return min(cap, r0 + (r1-r0) * (depth_m-d0)/(d1-d0))
    return cap


def calculate_scenario(frame, tier, depth_at_score_1_m=4.0, rainfall_stress=1.0):
    """Calculate location losses and nearest-estate aggregation transparently."""
    if tier not in HAZARD_TIERS:
        raise ValueError(f"Unsupported hazard tier: {tier}")
    if not 0.5 <= depth_at_score_1_m <= 8 or not 0.5 <= rainfall_stress <= 2:
        raise ValueError("Depth or rainfall stress is outside the supported scenario range")
    hazard_col, return_period = HAZARD_TIERS[tier]
    result = frame.copy()
    result["NeighborhoodProxy"] = [_neighborhood(float(a), float(b)) for a,b in zip(result.lat,result.lon)]
    result["HazardScore"] = result[hazard_col].clip(0,1)
    result["ScenarioTier"] = tier
    result["AssumedReturnPeriodYears"] = return_period
    result["DepthAtScore1_AssumptionM"] = depth_at_score_1_m
    result["RainfallStressMultiplier_Assumption"] = rainfall_stress
    result["AssumedDepthM"] = (result.HazardScore*depth_at_score_1_m*rainfall_stress).clip(upper=8)
    result["DamageRatio"] = [_damage_ratio(float(d),str(c)) for d,c in zip(result.AssumedDepthM,result.housing_class)]
    result["ModeledGrossLossKES"] = result.tiv_kes*result.DamageRatio
    grouped = result.groupby("NeighborhoodProxy",as_index=False).agg(
        Locations=("loc_id","count"), BuildingTIV_KES=("tiv_kes","sum"),
        ModeledGrossLossKES=("ModeledGrossLossKES","sum"), MeanHazardScore=("HazardScore","mean"),
        SyntheticRecords=("synthetic","sum"))
    grouped["LossAsPctOfTIV"] = grouped.ModeledGrossLossKES/grouped.BuildingTIV_KES.replace(0,pd.NA)
    tiv=float(result.tiv_kes.sum()); loss=float(result.ModeledGrossLossKES.sum())
    metrics={"locations":len(result),"tiv_kes":tiv,"gross_loss_kes":loss,
        "loss_pct_tiv":loss/tiv if tiv else 0.0,"return_period_years_assumed":return_period,
        "tier":tier,"synthetic_only":bool(result.synthetic.all())}
    return result,grouped.sort_values("ModeledGrossLossKES",ascending=False),metrics


def exceedance_curve(frame, depth_at_score_1_m=4.0, rainfall_stress=1.0):
    """Scenario loss curve; return periods are explicit model assumptions."""
    rows=[]
    for tier,(_,period) in HAZARD_TIERS.items():
        _,_,metric=calculate_scenario(frame,tier,depth_at_score_1_m,rainfall_stress)
        rows.append({"Scenario":tier,"ReturnPeriodYears_Assumed":period,
            "AnnualExceedanceProbability_Assumed":1/period,"ModeledGrossLossKES":metric["gross_loss_kes"]})
    return pd.DataFrame(rows).sort_values("ReturnPeriodYears_Assumed")
