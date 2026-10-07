# CatCleanse AI — Kenya Re Exposure Standardizer

Local Streamlit workspace for cleansing exposure schedules into an auditable OED property subset and reviewing Nairobi flood scenarios.

## Run locally

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run catcleanse/app.py
```

The dashboard has an admin-style left rail and a compact four-stage work path: exposure intake, hazard review, quality review, and report handoff. The visual palette uses navy `#1B2140`, light `#F7F7FA`, and red `#D62828`.

Load the sample Nairobi cleansing portfolio or upload CSV, XLSX, XLS, or TXT, then run **Run Pipeline**. The result views include the portfolio map, raw-to-OED comparison, field evidence, audit details, and exports. The **Nairobi Flood Scenarios** workspace loads the bundled challenge exposure and hotspot data. In **Hazard & values map**, upload one or more georeferenced GeoTIFFs to inspect their CRS, size, band, NoData, pixel statistics, WGS84 bounds, and map overlay. Raster files are interpreted locally and are not transmitted to a service. The interactive preview supports north-up EPSG:4326 GeoTIFFs up to 100 MB per file; other CRS values are rejected rather than guessed.

The handoff exports include OED CSV and JSON, a multi-sheet Excel workbook, detailed validation JSON, field-level audit CSV/JSON, and a multi-page PDF with portfolio metrics, review statuses, every location, and field-by-field evidence/rationales.

## Extraction and external services

Set `OPENAI_API_KEY` to enable optional OpenAI structured extraction. Without it, deterministic local extraction runs. Set `CATCLEANSE_MODEL` to choose a compatible model. Set `CATCLEANSE_NOMINATIM=1` only to opt in to the external Nominatim geocoder.

## Model limits and assumptions

The bundled challenge exposures are synthetic, not a Kenya Re insured portfolio. Supplied 0–1 pluvial proxy scores are relative susceptibility values, not observed flood depths, rainfall measurements, or event probabilities. Scenario-to-return-period mapping, score-to-depth conversion, damage curves, and nearest-estate aggregation are demonstration assumptions. The starter kit layers produce non-monotonic scenario losses, so the comparison is not a calibrated EP curve or regulatory PML. The model estimates gross building loss only; it excludes policy terms, contents, business interruption, demand surge, uncertainty, and reinsurance. Do not use scenario loss outputs for pricing, capital, or reserving without locally validated hazard, vulnerability, exposure, event frequency, and financial inputs.

The exposure cleanser uses a fixed 130 KES/USD assumption for repeatable demo output; replace it with the approved portfolio FX rate before production. Estate/sub-county centroid coordinates are approximate, not rooftop locations. Flood proximity on cleansed records is a keyword/centroid screen, not a hydraulic model.
