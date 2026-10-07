"""Evidence-first extraction with deterministic fallback and optional OpenAI JSON."""
import json, os, re
from ..models.schemas import ExtractedField, ParsedExposure

FIELDS = ("loc_name", "address", "latitude", "longitude", "occupancy", "construction", "stories", "year_built", "building_tiv", "contents_tiv")

def _field(value, text, rationale="Deterministically extracted from the supplied record."):
    return ExtractedField(value=value, evidence=text if value is not None else "", rationale=rationale if value is not None else "No explicit supporting value was found; left blank.")

def mock_extract(record: dict) -> ParsedExposure:
    """Extract explicit values using simple deterministic patterns; never infer missing metrics."""
    raw = " | ".join(f"{k}: {v}" for k, v in record.items() if v is not None and str(v).strip())
    lower = raw.lower()
    def find(keys):
        compact=[re.sub(r"[^a-z0-9]","",k.lower()) for k in keys]
        for k in keys:
            for key, val in record.items():
                normalized_key=re.sub(r"[^a-z0-9]","",str(key).lower())
                if re.sub(r"[^a-z0-9]","",k.lower()) in normalized_key and val is not None and str(val).strip(): return val
        return None
    # Prefer human-readable name columns over property reference/identifier columns.
    name = find(["locname", "location name", "property name", "building name", "asset name", "name"])
    if name is None: name = find(["property ref", "property id", "location id", "reference", "ref"])
    address = find(["address", "location", "estate", "area", "subcounty"])
    if len(record)==1 and isinstance(next(iter(record.values())),str):
        name_match=re.search(r"(?im)^\s*(?:RISK NAME|PROPERTY NAME)\s*:\s*(.+?)\s*$",raw)
        if name_match: name=name_match.group(1).strip()
        address_match=re.search(r"(?im)^\s*LOCATION(?:\s*&\s*PARCEL)?\s*:\s*(.+?)\s*$",raw)
        if address_match: address=address_match.group(1).strip()
    if address is None: address = find(["surveyor notes", "raw notes", "description", "site notes", "remarks"])
    lat, lon = find(["latitude", "lat"]), find(["longitude", "lon", "lng"])
    occ = find(["occupancy", "use", "property type", "business"])
    cons = find(["construction", "structure", "material", "building type"])
    stories, year = find(["stories", "storeys", "floors"]), find(["yearbuilt", "year built", "built year"])
    tiv = find(["buildingtiv", "building value", "sum insured", "tiv", "value"])
    contents = find(["contentstiv", "contents value", "contents"])
    if stories is None:
        patterns=(r"\bground\s*(?:plus|\+)\s*(\d{1,2})\s*floors?\b",r"\b(\d{1,2})\s*[- ]?storeys?\b",r"\b(\d{1,2})\s*[- ]?(?:stories|story)\b",r"\b(\d{1,2})\s*[- ]?floors?\b")
        for pattern in patterns:
            m=re.search(pattern,lower)
            if m:
                stories=int(m.group(1)) + (1 if "ground" in m.group(0) else 0); break
        if stories is None and re.search(r"\bdouble[- ]storey\b|\b2[- ]level\b|\b2 level\b",lower): stories=2
        if stories is None and re.search(r"\b(single|one)[- ](?:ground[- ])?(?:storey|story|floor|level)\b|\bsingle ground level\b",lower): stories=1
    if year is None:
        patterns=(r"(?:year of practical completion(?: verified)?|practical completion)\D{0,35}((?:18|19|20)\d{2})",
                  r"(?:built|constructed|commissioned|completed|completion)\D{0,24}((?:18|19|20)\d{2})",
                  r"(?<!pre-)(?<!pre )\b((?:18|19|20)\d{2})\s+(?:build|construction)\b")
        for pattern in patterns:
            m=re.search(pattern,lower)
            if m: year=int(m.group(1)); break
    if (lat is None or lon is None):
        m=re.search(r"(?:coordinates?\s*:?\s*|lat(?:itude)?\s*)([-+]?\d{1,2}\.\d+)\s*[,;/]\s*(?:lon(?:gitude)?\s*)?([-+]?\d{1,3}\.\d+)",raw,re.I)
        if m: lat,lon=float(m.group(1)),float(m.group(2))
    if occ is None:
        occ = next((s for s in ("industrial", "commercial", "apartment", "residential") if s in lower), None)
    if cons is None:
        if re.search(r"reinforced\s+concrete\s+(?:framed|frame|columns?|beams?)",lower): cons="reinforced concrete"
        elif re.search(r"(?:structural\s+)?steel\s+portal\s+frames?|all-steel\s+portal\s+frame",lower): cons="steel frame"
        else: cons = next((s for s in ("reinforced concrete", "concrete", "stone", "masonry", "brick", "timber", "wood", "steel") if s in lower), None)
    if tiv is None:
        money=r"((?:KES|KSH|USD|\$)?\s*\d[\d,]*(?:\.\d+)?\s*(?:billion|million|[bmk](?![A-Za-z]))?\s*(?:KES|KSH|USD)?)"
        patterns=(rf"building\s+reinstatement\s+value\s*:?\s*{money}",rf"building\s+(?:value|tiv)\s*(?:roughly|about|approximately|is|of|:)?\s*{money}",rf"\bstructure\s*:?\s*{money}",rf"\bbuilding\s*:\s*{money}",rf"(?:valuation|insured\s+value)\s*:?\s*{money}\s+(?:for|representing)\s+(?:the\s+)?structure",rf"sum\s+insured\s*:?\s*{money}")
        m=next((hit for pattern in patterns if (hit:=re.search(pattern,raw,re.I))),None)
        tiv = m.group(1).strip() if m else None
    if contents is None:
        money=r"((?:KES|KSH|USD|\$)?\s*\d[\d,]*(?:\.\d+)?\s*(?:billion|million|[bmk](?![A-Za-z]))?\s*(?:KES|KSH|USD)?)"
        patterns=(rf"(?:contents|stock\s*(?:&|and)\s*inventory|fixtures?,?\s*fittings?.*?plant|machinery\s*(?:&|and)\s*contents|household\s+effects)[^.;\n]{{0,120}}?{money}",rf"(?:tenants?\s+)?fixtures?,?\s*fittings?\s*(?:&|and)\s*plant\s*:?\s*{money}")
        m=next((hit for pattern in patterns if (hit:=re.search(pattern,raw,re.I))),None)
        contents = m.group(1).strip() if m else None
    values = dict(loc_name=name, address=address, latitude=lat, longitude=lon, occupancy=occ, construction=cons, stories=stories, year_built=year, building_tiv=tiv, contents_tiv=contents)
    parsed_fields={}
    for key,value in values.items():
        if value is None:
            parsed_fields[key]=_field(None, "")
            continue
        source=next((f"{col}: {cell}" for col,cell in record.items() if cell is not None and str(cell).strip() and str(cell).strip()==str(value).strip()), str(value))
        parsed_fields[key]=_field(value, source)
    return ParsedExposure(**parsed_fields)

def extract(record: dict, use_llm: bool = True) -> ParsedExposure:
    """Use OpenAI structured output when configured; safe deterministic fallback otherwise."""
    if not use_llm or not os.getenv("OPENAI_API_KEY"): return mock_extract(record)
    try:
        from openai import OpenAI
        client = OpenAI()
        instructions = ("Extract only facts explicitly supported by the supplied record. Never infer Year Built or stories. "
          "For every field return value, a verbatim source snippet, and a brief auditable rationale; do not reveal hidden chain-of-thought. "
          "Use null when absent. Output exactly the provided JSON schema.")
        result = client.beta.chat.completions.parse(model=os.getenv("CATCLEANSE_MODEL", "gpt-4o-mini"), temperature=0.0,
            response_format=ParsedExposure, messages=[{"role":"system","content":instructions}, {"role":"user","content":json.dumps(record, ensure_ascii=False)}])
        parsed = result.choices[0].message.parsed
        if parsed is None: return mock_extract(record)
        return parsed
    except Exception:
        return mock_extract(record)
