# Frontend Data Contract

The frontend reads three JSON files from `web/public/data/`:

## `summary.json`

```json
{
  "last_updated": "2026-04-08",
  "scenario": "baseline",
  "latest_output_gap": -3.0,
  "latest_potential_growth": 4.9,
  "sample_end": "2024-Q4"
}
```

## `series.json`

```json
{
  "last_updated": "2026-04-08",
  "scenario": "baseline",
  "dates": ["2005-Q1", "2005-Q2"],
  "output_gap": [0.1, 0.2],
  "potential_growth": [9.8, 9.7],
  "gdp_observed": [100.0, 101.2],
  "gdp_trend": [99.8, 100.7]
}
```

## `sectors.json`

```json
{
  "last_updated": "2026-04-08",
  "scenario": "baseline",
  "dates": ["2005-Q1", "2005-Q2"],
  "sector_names": ["imports", "electricity"],
  "shares": {
    "imports": [0.4, 0.5],
    "electricity": [0.6, 0.5]
  },
  "theta": {
    "imports": [0.2, 0.3],
    "electricity": [0.1, 0.2]
  }
}
```

## Notes

- `last_updated` and `scenario` are present in all three files.
- `dates` is the canonical time axis for `series.json` and `sectors.json`.
- All arrays should align by position.
- `gdp_observed` may contain `null` for missing observations.
- The frontend expects this canonical schema directly.
- Legacy field names such as `scenario_name`, `periods`, `output_gap_series`, `potential_growth_series`, and `sector_share_series` are no longer part of the frontend contract.
