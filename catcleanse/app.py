"""CatCleanse AI Streamlit dashboard and end-to-end exposure pipeline."""
import io, json, re, sys, time, math, base64
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
from catcleanse.core.cat_model import load_challenge_exposure, calculate_scenario, exceedance_curve, HAZARD_TIERS, DEFAULT_DATA
from catcleanse.core.raster import inspect_geotiff
from catcleanse.core.exporter import build_validation_pdf

st.set_page_config(page_title="CatCleanse AI | Kenya Re", page_icon="🌧️", layout="wide")
st.markdown("""<style>
:root { --ink:#1B2140; --paper:#F7F7FA; --accent:#D62828; --muted:#515873; }
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"] { background-color:#F7F7FA !important; color:#1B2140 !important; }
main, main p, main li, main label, main small, main h1, main h2, main h3, main [data-testid="stMarkdownContainer"], main [data-testid="stMarkdownContainer"] * { color:#1B2140; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color:#515873 !important; }
[data-testid="stSidebar"] { background-color:#1B2140 !important; }
[data-testid="stSidebar"], [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] [data-testid="stMarkdownContainer"], [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * { color:#F7F7FA !important; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea, [data-testid="stSidebar"] [data-baseweb="select"] *, [data-testid="stSidebar"] [data-baseweb="input"] *, [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * { color:#1B2140 !important; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea, [data-testid="stSidebar"] [data-baseweb="select"], [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] { background-color:#FFFFFF !important; }
[data-baseweb="select"] *, [data-baseweb="input"] *, [data-baseweb="textarea"] *, input, textarea, [role="option"] { color:#1B2140 !important; }
[data-baseweb="select"], [data-baseweb="input"], [data-baseweb="textarea"], input, textarea, [role="listbox"], [role="option"] { background-color:#FFFFFF !important; }
[data-baseweb="tab"], [data-baseweb="tab"] p, button[role="tab"] { color:#1B2140 !important; }
[data-baseweb="tab"][aria-selected="true"], button[role="tab"][aria-selected="true"] { color:#D62828 !important; border-bottom-color:#D62828 !important; }
.stButton > button, .stDownloadButton > button { background:#D62828 !important; color:#FFFFFF !important; border:0; border-radius:9px; font-weight:650; }
.stButton > button:hover, .stDownloadButton > button:hover { background:#B51F28 !important; color:#FFFFFF !important; border:0; }
[data-testid="stMetric"] { background:#FFFFFF !important; color:#1B2140 !important; border:1px solid #E0E2EA; border-radius:12px; padding:14px 16px; box-shadow:0 2px 8px rgba(27,33,64,.05); }
[data-testid="stMetric"] label, [data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stMetricDelta"] { color:#1B2140 !important; }
[data-testid="stDataFrame"], [data-testid="stTable"] { background:#FFFFFF !important; color:#1B2140 !important; }
[data-testid="stExpander"] { background:#FFFFFF; border:1px solid #E0E2EA; border-radius:10px; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color:#1B2140 !important; }
a { color:#B51F28 !important; }
[data-baseweb="tab-list"] { gap:8px; }
.cc-hero { background:linear-gradient(110deg,#1B2140 0%,#30395F 72%,#D62828 155%); border-radius:18px; padding:23px 28px; margin:0 0 16px; color:#FFFFFF; }
.cc-eyebrow { color:#F6B9BE; font-size:11px; font-weight:750; letter-spacing:1.4px; }
.cc-title { color:#FFFFFF; font-size:30px; font-weight:750; margin:4px 0 2px; }
.cc-subtitle { color:#F0F1F6; font-size:14px; }
.cc-step { display:inline-block; background:rgba(247,247,250,.11); border:1px solid rgba(247,247,250,.15); color:#FFFFFF; border-radius:20px; padding:6px 10px; margin:10px 6px 0 0; font-size:11px; }
.cc-step-active { background:#D62828; border-color:#D62828; }
main [data-testid="stMarkdownContainer"] .cc-hero .cc-eyebrow { color:#F6B9BE !important; }
main [data-testid="stMarkdownContainer"] .cc-hero .cc-title, main [data-testid="stMarkdownContainer"] .cc-hero .cc-subtitle, main [data-testid="stMarkdownContainer"] .cc-hero .cc-step { color:#FFFFFF !important; }
</style>""",unsafe_allow_html=True)
st.markdown("""<div class="cc-hero"><div class="cc-eyebrow">KENYA RE · NAIROBI FLOOD WORKSPACE</div><div class="cc-title">CatCleanse AI</div><div class="cc-subtitle">Exposure cleansing, hazard review, and explainable cat-model handoff</div><div><span class="cc-step cc-step-active">01 · Exposure</span><span class="cc-step">02 · Hazard</span><span class="cc-step">03 · Review</span><span class="cc-step">04 · Export</span></div></div>""",unsafe_allow_html=True)

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
    st.markdown("<div style='font-size:12px;font-weight:800;letter-spacing:1.5px;padding:5px 0 12px'>CATCLEANSE · ADMIN</div>",unsafe_allow_html=True)
    st.markdown("<div style='font-size:12px;line-height:2.1'>▸ 01 &nbsp; Exposure intake<br>○ 02 &nbsp; Hazard & scenarios<br>○ 03 &nbsp; Quality review<br>○ 04 &nbsp; Reports & handoff</div>",unsafe_allow_html=True)
    st.divider()
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
    st.dataframe(raw_df.head(10).astype("string"),use_container_width=True,hide_index=True)
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
    ribbon_conf=float(clean["ConfidenceScore"].mean()) if len(clean) else 0.0
    ribbon_coords=int(clean["Latitude"].notna().sum())
    ribbon_review=int((clean["ReviewStatus"]=="REQUIRES_HUMAN_REVIEW").sum())
    st.markdown(f"<div style='background:#fff;border:1px solid #e5e6ed;border-left:5px solid #D62828;border-radius:10px;padding:11px 15px;margin:2px 0 14px;color:#1B2140'><b>Portfolio status</b> &nbsp;·&nbsp; Average confidence {ribbon_conf:.0%} &nbsp;·&nbsp; Coordinates {ribbon_coords}/{len(clean)} &nbsp;·&nbsp; Human review {ribbon_review}</div>",unsafe_allow_html=True)
    tabs=st.tabs(["Portfolio Map & Overview","Side-by-Side Data Diff","XAI Inspection","Export & Cat Model Handoff","Nairobi Flood Scenarios"])
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
        with left: st.markdown("**Raw schedule**"); st.dataframe(raw_df.astype("string"),use_container_width=True,hide_index=True)
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
        audit_entries=[]
        for _,record in clean.iterrows():
            entries=record.get("DataCleansingAuditLog") or []
            if isinstance(entries,str):
                try: entries=json.loads(entries)
                except json.JSONDecodeError: entries=[]
            for entry in entries:
                item=dict(entry) if isinstance(entry,dict) else entry.model_dump(mode="json")
                item.update({"LocNum":record.get("LocNum"),"LocName":record.get("LocName")})
                audit_entries.append(item)
        review_rows=clean[clean["ReviewStatus"]=="REQUIRES_HUMAN_REVIEW"]
        geocode_counts={str(k):int(v) for k,v in clean["GeocodeQuality"].value_counts(dropna=False).items()}
        occupancy_counts={str(k):int(v) for k,v in clean["OccupancyCode"].value_counts(dropna=False).items()}
        construction_counts={str(k):int(v) for k,v in clean["ConstructionCode"].value_counts(dropna=False).items()}
        report={"report_title":"CatCleanse AI — Detailed Exposure Validation Report","generated_utc":pd.Timestamp.now(tz="UTC").isoformat(),"portfolio":{"portfolio_locations":len(clean),"building_tiv_kes":tiv,"contents_tiv_kes":float(clean["ContentsTIV"].sum()),"total_insured_value_kes":float(clean["BuildingTIV"].sum()+clean["ContentsTIV"].sum())},"data_quality":{"average_confidence":avg,"confidence_score_scale":"0.0–1.0 deterministic screening score; not a probability","requires_human_review":flagged,"review_records":[{"LocNum":int(r.LocNum),"LocName":str(r.LocName),"ConfidenceScore":float(r.ConfidenceScore),"BuildingTIV_KES":float(r.BuildingTIV),"GeocodeQuality":str(r.GeocodeQuality)} for r in review_rows.itertuples()],"coordinate_coverage_count":int(clean["Latitude"].notna().sum()),"coordinate_coverage_pct":float(clean["Latitude"].notna().mean()),"geocode_quality_counts":geocode_counts,"high_flood_proximity_count":int(clean["High_Flood_Proximity_Flag"].sum())},"portfolio_composition":{"occupancy_code_counts":occupancy_counts,"construction_code_counts":construction_counts},"audit":{"transformation_count":len(audit_entries),"transformation_type_counts":{str(k):int(v) for k,v in pd.Series([e.get("transformation_type") for e in audit_entries]).value_counts().items()},"field_level_log":"See separate downloadable audit CSV/JSON; each event carries raw value, cleaned value, method, source evidence and rationale."},"assumptions_and_limitations":["USD is converted at the configured fixed 130 KES/USD demo rate; confirm the portfolio FX policy before production use.","Estate/sub-county centroid coordinates are approximate, not rooftop coordinates.","Flood proximity is a keyword/centroid screen, not a hydraulic model.","Confidence is deterministic screening and must not be interpreted as a calibrated probability.","Records marked REQUIRES_HUMAN_REVIEW must be reviewed before cat-model handoff."]}
        audit_frame=pd.DataFrame(audit_entries,columns=["LocNum","LocName","field","raw_value","cleaned_value","standard_name","transformation_type","evidence","rationale"])
        audit_csv=audit_frame.to_csv(index=False).encode("utf-8-sig")
        audit_json=json.dumps(audit_entries,indent=2,ensure_ascii=False,default=str).encode("utf-8")
        excel_buffer=io.BytesIO()
        with pd.ExcelWriter(excel_buffer,engine="openpyxl") as writer:
            csv_frame.drop(columns=[],errors="ignore").to_excel(writer,index=False,sheet_name="OED Locations")
            audit_frame.to_excel(writer,index=False,sheet_name="Audit Trail")
            pd.DataFrame([{"section":section,"metric":key,"value":json.dumps(value,ensure_ascii=False,default=str) if isinstance(value,(dict,list)) else value} for section,data in report.items() if isinstance(data,dict) for key,value in data.items()]).to_excel(writer,index=False,sheet_name="Validation Summary")
        st.subheader("Cat model handoff package")
        st.markdown("Export the standardized OED locations together with record-level review decisions and a field-by-field evidence trail. The PDF includes portfolio metrics, every location, and every recorded transformation.")
        downloads=st.columns(3)
        downloads[0].download_button("OED locations · CSV",csv_bytes,"oasis_oed_locations.csv","text/csv",type="primary",use_container_width=True)
        downloads[1].download_button("OED locations · JSON",json_bytes,"oasis_oed_locations.json","application/json",use_container_width=True)
        downloads[2].download_button("OED workbook · Excel",excel_buffer.getvalue(),"catcleanse_oed_handoff.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
        downloads2=st.columns(3)
        downloads2[0].download_button("Detailed validation · JSON",json.dumps(report,indent=2,ensure_ascii=False,default=str).encode("utf-8"),"catcleanse_detailed_validation_report.json","application/json",use_container_width=True)
        downloads2[1].download_button("Field audit trail · CSV",audit_csv,"catcleanse_field_audit_trail.csv","text/csv",use_container_width=True)
        downloads2[2].download_button("Field audit trail · JSON",audit_json,"catcleanse_field_audit_trail.json","application/json",use_container_width=True)
        try:
            pdf_summary={"portfolio_locations":len(clean),"building_tiv_kes":tiv,"contents_tiv_kes":float(clean["ContentsTIV"].sum()),"average_confidence":avg,"requires_human_review":flagged,"coordinate_coverage":int(clean["Latitude"].notna().sum()),"high_flood_proximity":int(clean["High_Flood_Proximity_Flag"].sum()),"audit_entry_count":len(audit_entries)}
            pdf_bytes=build_validation_pdf(clean,pdf_summary,audit_entries)
            st.download_button("Download detailed validation report · PDF",pdf_bytes,"catcleanse_detailed_validation_report.pdf","application/pdf",type="primary",use_container_width=True)
        except ImportError:
            st.warning("PDF export needs the pinned reportlab dependency. Install the updated requirements.txt, then rerun the app.")
        with st.expander("Preview validation report",expanded=True): st.json(report)
    with tabs[4]:
        st.subheader("Nairobi urban flood stress model")
        st.caption("Challenge starter-kit proxy scores × assumed depth-damage curves × synthetic building TIV. This is an illustrative screening model, not a calibrated catastrophe model.")
        try:
            cat_frame=load_challenge_exposure()
            hotspots_path=DEFAULT_DATA / "nairobi_hotspots_geocoded.csv"
            hotspots=pd.read_csv(hotspots_path) if hotspots_path.exists() else pd.DataFrame(columns=["name","lat","lon"])
            controls=st.columns(3)
            tier=controls[0].selectbox("Hazard scenario",list(HAZARD_TIERS),index=4,key="cat_tier")
            depth=controls[1].slider("Assumed depth when proxy score = 1.0 (m)",0.5,8.0,4.0,0.5,key="cat_depth")
            stress=controls[2].slider("Rainfall stress multiplier (assumption)",0.5,2.0,1.0,0.1,key="cat_rainfall")
            stressed,neighborhood,cat_metrics=calculate_scenario(cat_frame,tier,depth,stress)
            curve=exceedance_curve(cat_frame,depth,stress)
            st.info("The supplied 0–1 raster/CSV values represent relative pluvial susceptibility, not measured flood depth. Return periods (2, 5, 10, 50, 100 years by tier) and the depth conversion are explicit scenario assumptions; rainfall is not an observed gauge input. All supplied exposure records are synthetic.")
            k1,k2,k3,k4=st.columns(4)
            k1.metric("Synthetic locations",f"{cat_metrics['locations']:,}")
            k2.metric("Building TIV",f"KES {cat_metrics['tiv_kes']:,.0f}")
            k3.metric(f"Modeled gross loss · {tier}",f"KES {cat_metrics['gross_loss_kes']:,.0f}")
            k4.metric("Loss / TIV",f"{cat_metrics['loss_pct_tiv']:.1%}")
            st.markdown(f"**Scenario assumption:** {tier} tier · nominal 1-in-{cat_metrics['return_period_years_assumed']}-year return period · max proxy-derived depth {depth*stress:.1f} m. Return period is not empirically estimated.")
            sub=st.tabs(["Hazard & values map","Neighborhood aggregation","Loss exceedance & assumptions"])
            with sub[0]:
                raster_uploads=st.file_uploader("Upload GeoTIFF hazard layers",type=["tif","tiff"],accept_multiple_files=True,help="Reads local georeferencing, CRS, raster statistics, and overlays the selected pixels on the map. GeoTIFF files up to 100 MB each are supported.",key="hazard_geotiff_upload")
                raster_layers=[]
                if raster_uploads:
                    for raster_file in raster_uploads:
                        try:
                            raster_info=inspect_geotiff(raster_file)
                            summary_columns=st.columns(4)
                            summary_columns[0].metric(raster_info["filename"],f"{raster_info['width']:,} × {raster_info['height']:,}")
                            summary_columns[1].metric("Valid pixel range",f"{raster_info['min']:.3g} – {raster_info['max']:.3g}")
                            summary_columns[2].metric("Mean raster value",f"{raster_info['mean']:.3g}")
                            summary_columns[3].metric("CRS / band",f"{raster_info['crs']} · {raster_info['data_type']}")
                            st.caption(f"Bands: {raster_info['bands']} · NoData: {raster_info['nodata']} · valid pixels: {raster_info['valid_pixel_count']:,} · WGS84 extent: {raster_info['bounds_wgs84']}")
                            if raster_info["overlaps_kenya"]: raster_layers.append(raster_info)
                            else: st.warning(f"{raster_info['filename']} does not overlap the configured Kenya map bounds and will not be overlaid.")
                        except ImportError:
                            st.error("GeoTIFF support requires rasterio. Install the updated pinned dependencies in requirements.txt.")
                            break
                        except Exception as exc:
                            st.error(f"Could not interpret {raster_file.name}: {exc}")
                try:
                    import folium
                    from streamlit_folium import st_folium
                    fmap=folium.Map(location=[-1.286,36.817],zoom_start=11,tiles="OpenStreetMap")
                    for raster_info in raster_layers:
                        west,south,east,north=raster_info["bounds_wgs84"]
                        image_uri="data:image/png;base64,"+base64.b64encode(raster_info["png"]).decode("ascii")
                        folium.raster_layers.ImageOverlay(image=image_uri,bounds=[[south,west],[north,east]],opacity=.72,name=raster_info["filename"],interactive=True,cross_origin=False,zindex=2,origin="upper").add_to(fmap)
                    for _,r in stressed.iterrows():
                        score=float(r.HazardScore); color="#b91c1c" if score>=.6 else "#f59e0b" if score>=.25 else "#15803d"
                        radius=max(3,min(12,3+math.log10(max(float(r.tiv_kes),1))*0.6))
                        folium.CircleMarker([r.lat,r.lon],radius=radius,color=color,fill=True,fill_opacity=.65,
                            popup=f"{r.loc_id} · {r.NeighborhoodProxy}<br>TIV KES {r.tiv_kes:,.0f}<br>Proxy {score:.2f}<br>Assumed depth {r.AssumedDepthM:.2f} m<br>Modeled loss KES {r.ModeledGrossLossKES:,.0f}",tooltip=str(r.loc_id)).add_to(fmap)
                    for _,h in hotspots.iterrows():
                        folium.Marker([h.lat,h.lon],icon=folium.Icon(color="blue",icon="tint",prefix="fa"),tooltip=f"Named hotspot: {h['name']}").add_to(fmap)
                    if raster_layers: folium.LayerControl(collapsed=False).add_to(fmap)
                    st_folium(fmap,use_container_width=True,height=500,key="cat_hazard_map")
                    st.caption("Circle color shows the selected relative hazard proxy tier (green low, amber medium, red high); circle size scales with building value. Blue pins are the supplied named hotspots, not modeled flood observations.")
                except ImportError:
                    st.warning("Map dependencies are unavailable; the scenario tables and charts remain usable.")
                    st.map(stressed.rename(columns={"lat":"latitude","lon":"longitude"})[["latitude","longitude"]])
            with sub[1]:
                st.markdown("Nearest-estate aggregation uses the app's offline neighborhood centroids; labels are approximate and not administrative boundaries.")
                st.dataframe(neighborhood,use_container_width=True,hide_index=True)
                st.bar_chart(neighborhood.set_index("NeighborhoodProxy")[["BuildingTIV_KES","ModeledGrossLossKES"]])
            with sub[2]:
                st.markdown("Scenario loss comparison using provisional tier-to-return-period assumptions. These points are not a fitted or calibrated EP curve.")
                if not curve["ModeledGrossLossKES"].is_monotonic_decreasing:
                    st.warning("The supplied proxy score layers do not produce monotonic losses across the assumed return periods. The chart is a scenario comparison only; it must not be interpreted as an EP curve or regulatory PML.")
                st.bar_chart(curve.set_index("Scenario")[["ModeledGrossLossKES"]])
                st.dataframe(curve,use_container_width=True,hide_index=True)
                with st.expander("Model inputs, logic and limitations",expanded=True):
                    st.write("**Hazard:** provided synthetic 0–1 susceptibility scores for five named scenarios. They are not flood depths or rainfall measurements.")
                    st.write("**Exposure:** the supplied 600-location challenge dataset marks records synthetic; building values are not an insured Kenya Re portfolio.")
                    st.write("**Depth conversion:** assumed depth = hazard score × selected depth-at-score-1 × rainfall stress multiplier, capped at 8 m.")
                    st.write("**Vulnerability:** transparent piecewise depth-damage anchors and class caps are illustrative assumptions, not Kenya-calibrated curves.")
                    st.write("**Loss:** gross building loss = building TIV × damage ratio; no policy terms, contents, BI, demand surge, uncertainty, or reinsurance are modeled.")
                    st.write("**AI/explainability:** the exposure parser and its evidence log document extraction; catastrophe calculations are deterministic and auditable, not LLM-generated.")
                st.download_button("Download scenario location losses CSV",stressed.to_csv(index=False).encode("utf-8-sig"),"nairobi_scenario_location_losses.csv","text/csv")
                st.download_button("Download scenario summary CSV",neighborhood.to_csv(index=False).encode("utf-8-sig"),"nairobi_scenario_neighborhood_summary.csv","text/csv")
        except Exception as exc:
            st.error(f"Could not run the Nairobi scenario model: {exc}")
else:
    st.info("Load the sample portfolio or upload an exposure file to begin.")
