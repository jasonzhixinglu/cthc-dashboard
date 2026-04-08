# Data Sources

This pipeline targets the following model input variables:

- `gdp`
- `imports`
- `electricity`
- `industrial_va`
- `retail_sales`
- `fixed_asset_investment`
- `cpi`

The implementation uses a practical source priority:

1. OECD public SDMX/API download when a stable official series is available
2. IMF API fallback when OECD is unavailable or unsuitable
3. Official NBS source for fixed asset investment, with a clean manual CSV fallback when automated retrieval is difficult

Raw standardized files are stored in `data/raw/<series>.csv` with:

```csv
date,value,source,units,fetched_at
```

Manual fallback files use:

```csv
date,value
```

## Variable Notes

### `gdp`

- Chosen source: OECD
- Fallback: IMF, then manual CSV
- Proxy: quarterly GDP level from the OECD Quarterly National Accounts developer feed
- Raw frequency: quarterly
- Quarterly transform: none
- Nominal or real: nominal by default in this pipeline
- CPI deflation: yes
- Live retrieval: yes, via OECD
- Notes: the live OECD filter uses the QNA developer API and selects the China quarterly GDP level slice in national currency and current prices

### `imports`

- Chosen source: OECD
- Fallback: IMF, then manual CSV
- Proxy: monthly imports from OECD International Merchandise Trade Statistics, world counterpart
- Raw frequency: monthly
- Quarterly transform: quarterly sum
- Nominal or real: nominal by default
- CPI deflation: yes
- Live retrieval: yes, via OECD
- Notes: IMF fallback support remains in the fetch helper, but the current primary path uses the official OECD IMTS feed

### `electricity`

- Chosen source: manual official CSV fallback
- Fallback: none
- Proxy: monthly official electricity production drop-in CSV
- Raw frequency: monthly
- Quarterly transform: quarterly average
- Nominal or real: real/index-like
- CPI deflation: no
- Live retrieval: no, not by default
- Notes: no clean OECD live series is wired in the current source design, so `data/raw/electricity_manual.csv` remains the preferred path

### `industrial_va`

- Chosen source: OECD
- Fallback: IMF, then manual CSV
- Proxy: OECD Key Economic Indicators manufacturing production index
- Raw frequency: monthly
- Quarterly transform: quarterly average
- Nominal or real: real/index-like
- CPI deflation: no
- Live retrieval: yes, via OECD
- Notes: this is a practical industrial activity proxy rather than the exact paper measure

### `retail_sales`

- Chosen source: OECD
- Fallback: IMF, then manual CSV
- Proxy: OECD Key Economic Indicators retail sales index
- Raw frequency: monthly
- Quarterly transform: quarterly average
- Nominal or real: treated as real/index-like in the current registry
- CPI deflation: no
- Live retrieval: yes, via OECD
- Notes: if a nominal retail series is substituted later, update the registry so CPI deflation is applied

### `fixed_asset_investment`

- Chosen source: NBS
- Fallback: manual CSV
- Proxy: official fixed asset investment excluding rural households
- Raw frequency: monthly
- Quarterly transform: cumulative-within-year monthly values are first converted to monthly flows, then summed to quarter
- Nominal or real: nominal
- CPI deflation: yes
- Live retrieval: manual/NBS fallback only
- Notes: this remains the main special-case series. Manual official CSV input is preferred over fragile scraping. Place the official cumulative series in `data/raw/fixed_asset_investment_manual.csv`

### `cpi`

- Chosen source: OECD
- Fallback: IMF, then manual CSV
- Proxy: OECD all-items CPI index for China from the official CPI exchange feed
- Raw frequency: monthly
- Quarterly transform: quarterly average
- Nominal or real: index
- CPI deflation: not applicable
- Live retrieval: yes, via OECD
- Notes: the OECD COICOP 1999 CPI exchange flow currently returns China observations cleanly; IMF remains the configured fallback

## Ragged Edge Handling

- The quarterly dataset is aligned on the union of available quarterly dates
- Trailing missing values are preserved for real-time updates
- The Kalman filter later handles these missing observations directly

## Configuration Notes

The fetcher supports environment variable URL overrides for official API downloads:

- `CTHC_GDP_OECD_URL`
- `CTHC_IMPORTS_OECD_URL`
- `CTHC_ELECTRICITY_OECD_URL`
- `CTHC_INDUSTRIAL_VA_OECD_URL`
- `CTHC_RETAIL_SALES_OECD_URL`
- `CTHC_FIXED_ASSET_INVESTMENT_NBS_URL`
- `CTHC_CPI_OECD_URL`

This keeps the source registry explicit while still allowing the project to point at alternate official URLs if the OECD or IMF APIs change.

## Current Live Coverage

- Live via OECD now:
  - `gdp`
  - `imports`
  - `industrial_va`
  - `retail_sales`
  - `cpi`
- IMF fallback helper implemented:
  - `gdp`
  - `imports`
  - `industrial_va`
  - `retail_sales`
  - `cpi`
- Manual official fallback remains primary:
  - `fixed_asset_investment`
  - `electricity`
