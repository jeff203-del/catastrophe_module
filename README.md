# CatCleanse AI — Kenya Re Exposure Standardizer

Local Streamlit application that converts broker schedules and survey notes to an auditable core subset of Oasis OED property fields.

## Run locally

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run catcleanse/app.py
```

Set `OPENAI_API_KEY` to enable optional OpenAI structured extraction. When it is absent, the deterministic parser is used. Set `CATCLEANSE_MODEL` to select a compatible model. Set `CATCLEANSE_NOMINATIM=1` only if network geocoding is desired.

## Operational notes

The bundled currency conversion uses a fixed 130 KES/USD assumption for repeatable demo output; set the policy-approved rate before production use. Place centroids represent neighborhood-level locations, not surveyed building coordinates. Flood proximity is a conservative address keyword flag, not a hydraulic model. Validate supported code mappings and CSV columns with the receiving OED ingestion configuration before catastrophe model handoff.
