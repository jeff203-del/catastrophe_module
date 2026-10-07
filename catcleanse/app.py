"""CatCleanse AI Streamlit dashboard and end-to-end exposure pipeline."""
import io, json, re, sys, time
import csv
from pathlib import Path
import pandas as pd
import streamlit as st

PACKAGE_ROOT=Path(__file__).resolve().parent
if str(PACKAGE_ROOT.parent) not in sys.path: sys.path.insert(0,str(PACKAGE_ROOT.parent))
from catcleanse.core.extractor import extract
from catcleanse.core.normalizer import normalize
from catcleanse.core.geocoder import resolve, flood_flag
from catcleanse.core.validator import build_location
from catcleanse.utils.sample_data import sample_portfolio

st.set_page_config(page_title="CatCleanse AI | Kenya Re", page_icon="🌧️", layout="wide")
st.title("CatCleanse AI — Kenya Re Exposure Standardizer")
st.caption("Transforming Unstructured Broker Data into Oasis OED-Ready Cat Modeling Portfolios")
st.markdown("Clean broker schedules into auditable OED property records. Missing facts remain blank; every deterministic change carries evidence.")

def parse_delimited_text(text):
    """Read delimited text and repair surplus empty cells in ragged rows."""
    try:
        dialect=csv.Sniffer().sniff(text[:4096],delimiters=",;\t|\u0001")
        parsed=list(csv.reader(io.StringIO(text),dialect))
        if parsed and len(parsed[0])>1:
            headers=parsed[0]; width=len(headers); repaired=[]
            def row_penalty(candidate):
                penalty=0
                for index,header in enumerate(headers):
                    value=candidate[index].strip() if index<len(candidate) else ""
                    name=header.lower()
                    if any(k in name for k in ("latitude","longitude")) and value:
                        try: float(value)
                        except ValueError: penalty+=4
                    if any(k in name for k in ("sum_insured","tiv","value")) and value and not re.search(r"\d|tbd|none",value,re.I): penalty+=3
                    if any(k in name for k in ("construction","occupancy")) and value and re.fullmatch(r"(?:KES|KSH|USD)?\s*[\d,.]+\s*(?:KES|KSH|USD)?",value,re.I): penalty+=3
                return penalty
            for row in parsed[1:]:
                row=list(row)
                while len(row)>width:
                    blanks=[j for j,value in enumerate(row) if not value.strip()]
                    if not blanks: row=row[:width]; break
                    choices=[]
                    for j in blanks:
                        candidate=row[:j]+row[j+1:]
                        choices.append((row_penalty(candidate),j,candidate))
                    _,_,row=min(choices,key=lambda x:x[0])
                repaired.append((row+[""]*width)[:width])
            table=pd.DataFrame(repaired,columns=headers)
            if len(table)>0: return table
    except Exception: pass
    return None

def parse_upload(upload):
    """Load supported schedules and preserve narrative reports as whole records."""
    name=upload.name.lower()
    if name.endswith((".xlsx", ".xls")): return pd.read_excel(upload)
    text=upload.getvalue().decode("utf-8",errors="replace")
    # Both .csv and .txt schedules use this parser so malformed rows are handled consistently.
    if name.endswith(".csv"):
        table=parse_delimited_text(text)
        return table if table is not None else pd.read_csv(io.StringIO(text))
    # A .txt extension may contain a delimited broker schedule. Try parsing the
    # entire document first; line-by-line parsing destroys CSV quoting and rows.
    table=parse_delimited_text(text)
    if table is not None: return table
    # Narrative valuation memos often contain several survey entries in one file.
    entries=re.split(r"(?=^\s*\[SURVEY\s+ENTRY\s*#?\s*\d+\s*\])",text,flags=re.I|re.M)
    entries=[entry.strip() for entry in entries if re.match(r"^\s*\[SURVEY\s+ENTRY\s*#?\s*\d+\s*\]",entry,re.I)]
    if len(entries)>1:
        return pd.DataFrame([{"Raw Surveyor Notes":entry} for entry in entries])
    return pd.DataFrame([{"Raw Surveyor Notes":text.strip()}] if text.strip() else [])

if "raw_df" not in st.session_state: st.session_state.raw_df=None
with st.sidebar:
    st.header("Exposure input")
    if st.button("Load Sample Nairobi Portfolio", use_container_width=True): st.session_state.raw_df=sample_portfolio()
    uploaded=st.file_uploader("Upload CSV / Excel / surveyor notes", type=["csv","xlsx","xls","txt"])
    if uploaded is not None:
        try: st.session_state.raw_df=parse_upload(uploaded)
        except Exception as exc: st.error(f"Could not read input: {exc}")
    st.caption("LLM extraction is optional. Without OPENAI_API_KEY, deterministic local extraction runs automatically.")
    use_llm=st.checkbox("Use configured OpenAI extraction", value=True)

raw_df=st.session_state.raw_df
if raw_df is not None:
    st.subheader("Input preview")
    st.dataframe(raw_df.head(10),use_container_width=True,hide_index=True)
    if st.button("Run Pipeline", type="primary", use_container_width=True):
        bar=st.progress(0,text="Ingestion")
        statuses=["Ingestion","LLM Extraction / deterministic fallback","Geo-Validation","Confidence Scoring","OED Export"]
        output=[]
        try:
            for i,(_,row) in enumerate(raw_df.iterrows(),1):
                record=row.where(pd.notna(row),None).to_dict()
                parsed=extract(record,use_llm=use_llm)
                vals,audits=normalize(parsed)
                lat,lon,quality=resolve(vals.get("address"),vals.get("latitude"),vals.get("longitude"))
                loc=build_location(i,parsed,vals,audits,lat,lon,quality,flood_flag(vals.get("address"),lat,lon))
                output.append(loc)
                pct=int(i/len(raw_df)*80)
                bar.progress(pct,text=f"{statuses[1]} • {i}/{len(raw_df)}")
            bar.progress(90,text=statuses[3]); time.sleep(.1)
            clean=pd.DataFrame([loc.model_dump(mode="json") for loc in output])
            bar.progress(100,text=statuses[4]); st.session_state.clean_df=clean; st.session_state.locations=output
        except Exception as exc:
            bar.empty(); st.error(f"Pipeline stopped safely: {exc}")

if st.session_state.get("clean_df") is not None:
    clean=st.session_state.clean_df
    locations=st.session_state.locations
    tabs=st.tabs(["Portfolio Map & Overview","Side-by-Side Data Diff","XAI Inspection","Export & Cat Model Handoff"])
    with tabs[0]:
        tiv=float(clean["BuildingTIV"].sum()); avg=float(clean["ConfidenceScore"].mean()); flagged=int((clean["ReviewStatus"]=="REQUIRES_HUMAN_REVIEW").sum())
        c1,c2,c3,c4=st.columns(4); c1.metric("Portfolio Building TIV",f"KES {tiv:,.0f}"); c2.metric("Avg Confidence",f"{avg:.0%}"); c3.metric("Human Review",flagged); c4.metric("Locations",len(clean))
        st.dataframe(clean[["LocNum","LocName","BuildingTIV","ContentsTIV","ConfidenceScore","ReviewStatus","High_Flood_Proximity_Flag"]],use_container_width=True,hide_index=True)
        points=clean.dropna(subset=["Latitude","Longitude"])
        if not points.empty:
            try:
                import folium
                from streamlit_folium import st_folium
                # CARTO's anonymous tile endpoint now returns an API-key watermark.
                # OpenStreetMap is used here so the demo basemap renders without a key.
                fmap=folium.Map(location=[-1.286,36.817],zoom_start=11,tiles="OpenStreetMap")
                for _,r in points.iterrows():
                    color="green" if r.ConfidenceScore>=.8 else "orange" if r.ConfidenceScore>=.6 else "red"
                    folium.CircleMarker([r.Latitude,r.Longitude],radius=8,color=color,fill=True,popup=f"{r.LocName}: {r.ConfidenceScore:.0%}").add_to(fmap)
                st_folium(fmap,use_container_width=True,height=450)
            except ImportError: st.map(points.rename(columns={"Latitude":"lat","Longitude":"lon"})[["lat","lon"]])
        else: st.info("No valid Kenya coordinates resolved for mapping.")
    with tabs[1]:
        left,right=st.columns(2)
        with left: st.markdown("**Raw schedule**"); st.dataframe(raw_df,use_container_width=True,hide_index=True)
        with right: st.markdown("**OED-ready output**"); st.dataframe(clean.drop(columns=["DataCleansingAuditLog"]),use_container_width=True,hide_index=True)
    with tabs[2]:
        names=[f"{x.LocNum}: {x.LocName}" for x in locations]
        selection=st.selectbox("Select a location to inspect its evidence",range(len(names)),format_func=lambda x:names[x])
        loc=locations[selection]
        st.write(f"**Confidence:** {loc.ConfidenceScore:.0%} · **Status:** {loc.ReviewStatus}")
        if loc.DataCleansingAuditLog:
            for e in loc.DataCleansingAuditLog:
                with st.expander(f"{e.field}: {e.cleaned_value}",expanded=True):
                    st.write("**Source evidence**", e.evidence or "No explicit source snippet")
                    st.write("**Rationale**",e.rationale or "No transformation rationale")
                    st.caption(f"Raw: {e.raw_value} · Method: {e.transformation_type}")
        else: st.info("No transformations were required or source snippets were not available.")
    with tabs[3]:
        csv_frame=clean.copy()
        csv_frame["DataCleansingAuditLog"]=csv_frame["DataCleansingAuditLog"].apply(lambda entries: json.dumps(entries,ensure_ascii=False))
        csv_bytes=csv_frame.to_csv(index=False).encode("utf-8-sig")
        json_bytes=clean.to_json(orient="records",indent=2,force_ascii=False).encode("utf-8")
        report={"portfolio_locations":len(clean),"building_tiv_kes":tiv,"average_confidence":avg,"requires_human_review":flagged,"high_flood_proximity":int(clean["High_Flood_Proximity_Flag"].sum()),"coordinate_coverage":int(clean["Latitude"].notna().sum()),"notes":"USD values converted at configured 130 KES/USD assumption. Confirm portfolio-specific FX policy before production use."}
        st.download_button("Download oasis_oed_locations.csv",csv_bytes,"oasis_oed_locations.csv","text/csv",type="primary")
        st.download_button("Download OED JSON",json_bytes,"oasis_oed_locations.json","application/json")
        st.download_button("Download executive validation report",json.dumps(report,indent=2).encode(),"catcleanse_validation_report.json","application/json")
        st.json(report)
else:
    st.info("Load the sample portfolio or upload an exposure file to begin.")
