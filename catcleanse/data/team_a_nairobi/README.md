# Team A Nairobi challenge data

This folder bundles the synthetic/open challenge inputs copied from the supplied `Test 14I` starter kit so the demo can run without browsing for files:

- `exposure_nairobi_with_hazard.csv`: 600 synthetic locations with building TIV and five joined 0–1 hazard proxy layers.
- `exposure_nairobi_synthetic.csv`: the same synthetic exposures without joined proxy scores.
- `nairobi_hotspots_geocoded.csv`: supplied named hotspot points.
- `nairobi_pluvial_proxy_*.tif`: five supplied raster proxy layers (retained for reproducibility; the dashboard uses the starter kit's pre-joined CSV scores).

The exposure file explicitly identifies its rows as synthetic. Hazard proxy scores are relative susceptibility scores, not measured flood depths, rainfall observations, or event probabilities. Scenario-to-return-period assignments, proxy-score-to-depth conversion, vulnerability breakpoints, and nearest-estate aggregation in the application are assumptions for demonstration. Do not use the resulting losses for pricing, capital, reinsurance, or regulatory reporting without locally validated hazard, vulnerability, exposure, policy terms, and event frequencies.
