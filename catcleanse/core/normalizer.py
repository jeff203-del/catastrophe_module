"""Deterministic field normalization and auditable OED mapping."""
import re
from ..config import CURRENCY_KES_PER_UNIT, OCCUPANCY_CODES, CONSTRUCTION_CODES
from ..models.schemas import AuditEntry

def money_kes(value):
    """Convert numeric and abbreviated values to KES; USD assumes documented default FX 130."""
    if value is None or str(value).strip() == "": return None
    s = str(value).replace(",", "").strip().upper()
    currency = "USD" if "USD" in s or "$" in s else "KES"
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m: return None
    amount = float(m.group())
    if re.search(r"\d\s*B\b", s) or "BILLION" in s: amount *= 1_000_000_000
    elif re.search(r"\d\s*M\b", s) or "MILLION" in s: amount *= 1_000_000
    elif re.search(r"\d\s*K\b", s) or "THOUSAND" in s: amount *= 1_000
    return amount * CURRENCY_KES_PER_UNIT[currency]

def normalize(parsed):
    """Return normalized values and entries describing every nontrivial mapping."""
    values, audit = {}, []
    for name, item in parsed:
        values[name] = item.value
    for key, table, default, standard in (("occupancy", OCCUPANCY_CODES, 1050, "OED occupancy"), ("construction", CONSTRUCTION_CODES, 9999, "OED construction")):
        raw = values.get(key); val = str(raw or "").lower()
        if key == "occupancy" and "residential" in val and not any(x in val for x in ("multi", "apartment")): val = "single family residential"
        if key == "construction" and "steel" in val and ("frame" in val or "portal" in val): val = "steel frame"
        elif key == "construction" and "concrete" in val: val = "reinforced concrete"
        if key == "construction" and any(x in val for x in ("stone", "brick", "block")): val = "masonry"
        if key == "construction" and "steel" in val: val = "steel frame"
        code = 9999 if key == "occupancy" and (not val or val == "unknown") else next((c for token,c in table.items() if token in val), default)
        values[key + "_code"] = code
        if raw is not None:
            audit.append(AuditEntry(field=key.title()+"Code", raw_value=raw, cleaned_value=code, standard_name=standard, transformation_type="DETERMINISTIC_CODE_MAP", evidence=next((item.evidence for k,item in parsed if k==key), ""), rationale=f"Mapped description to supported code {code}."))
    for key in ("building_tiv", "contents_tiv"):
        raw=values.get(key); amount=money_kes(raw)
        values[key+"_kes"] = amount
        if raw is not None:
            values.setdefault("audit", []).append(AuditEntry(field="BuildingTIV" if key.startswith("building") else "ContentsTIV", raw_value=raw, cleaned_value=amount, standard_name="KES", transformation_type="CURRENCY_NORMALIZATION", evidence=next((item.evidence for k,item in parsed if k==key), ""), rationale="Parsed amount and applied deterministic KES conversion (USD at configured 130 KES/USD)."))
    audit.extend(values.pop("audit", []))
    for key in ("stories", "year_built"):
        v=values.get(key)
        try:
            match=re.search(r"\d+",str(v)) if v is not None else None
            values[key]=int(match.group()) if match else None
        except (TypeError,ValueError): values[key]=None
    return values, audit
