"""Quarterly transformation pipeline for CTHC model input data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .data_sources import RAW_DATA_DIR, SeriesDefinition, TARGET_SERIES, get_source_registry

PROCESSED_DATA_PATH = Path("data/processed/model_dataset.csv")


def load_raw_series(series_name: str, *, raw_dir: Path = RAW_DATA_DIR) -> pd.Series | None:
    """Load a standardized raw series from ``data/raw``."""
    path = raw_dir / f"{series_name}.csv"
    if not path.exists():
        return None

    frame = pd.read_csv(path)
    if frame.empty:
        return pd.Series(dtype=float, name=series_name)
    if "date" not in frame.columns or "value" not in frame.columns:
        raise ValueError(f"Raw file '{path}' must contain 'date' and 'value' columns.")

    series = pd.Series(
        pd.to_numeric(frame["value"], errors="coerce").to_numpy(),
        index=_parse_period_index(frame["date"].astype(str)),
        name=series_name,
        dtype=float,
    ).sort_index()
    return series[~series.index.duplicated(keep="last")]


def build_model_dataset(
    *,
    raw_dir: Path = RAW_DATA_DIR,
    output_path: Path = PROCESSED_DATA_PATH,
) -> pd.DataFrame:
    """Build the quarterly model-ready dataset from raw input series."""
    registry = get_source_registry()
    transformed: dict[str, pd.Series] = {}

    cpi_raw = load_raw_series("cpi", raw_dir=raw_dir)
    cpi_quarterly = None
    if cpi_raw is not None:
        cpi_quarterly = transform_series_to_quarterly("cpi", cpi_raw, registry["cpi"])

    for series_name in TARGET_SERIES:
        raw_series = load_raw_series(series_name, raw_dir=raw_dir)
        if raw_series is None:
            continue
        quarterly = transform_series_to_quarterly(series_name, raw_series, registry[series_name])
        if series_name != "cpi" and registry[series_name].is_nominal:
            quarterly = deflate_nominal_series(quarterly, cpi_quarterly)
        transformed[series_name] = np.log(quarterly.where(quarterly > 0))

    dataset = align_quarterly_series(transformed)
    dataset = trim_leading_sparse_rows(dataset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output_path, index=True, index_label="date")
    return dataset


def transform_series_to_quarterly(
    series_name: str,
    series: pd.Series,
    spec: SeriesDefinition,
) -> pd.Series:
    """Convert one raw series to quarterly frequency using the configured rule."""
    normalized = series.dropna().sort_index()
    if normalized.empty:
        return pd.Series(dtype=float, name=series_name)

    if spec.cumulative_within_year:
        normalized = cumulative_within_year_to_monthly_flows(normalized)

    frequency = infer_frequency(normalized.index)
    if frequency == "quarterly":
        quarterly = normalized.copy()
        quarterly.index = quarterly.index.asfreq("Q")
        quarterly.name = series_name
        return quarterly

    if frequency != "monthly":
        raise ValueError(f"Unsupported frequency for '{series_name}': {frequency}")

    quarter_index = normalized.index.asfreq("Q")
    if spec.observation_kind == "flow":
        quarterly = normalized.groupby(quarter_index).sum(min_count=1)
    elif spec.observation_kind in {"index", "level"}:
        quarterly = normalized.groupby(quarter_index).mean()
    else:
        raise ValueError(f"Unsupported observation_kind '{spec.observation_kind}' for '{series_name}'.")
    quarterly.name = series_name
    return quarterly.sort_index()


def cumulative_within_year_to_monthly_flows(series: pd.Series) -> pd.Series:
    """Convert within-year cumulative monthly values to monthly flows."""
    if not isinstance(series.index, pd.PeriodIndex) or series.index.freqstr[0] != "M":
        raise ValueError("Cumulative-within-year conversion requires a monthly PeriodIndex.")

    monthly_flows = []
    for _, year_values in series.groupby(series.index.year):
        monthly_flows.append(year_values.diff().where(year_values.index.month != 1, year_values))
    result = pd.concat(monthly_flows).sort_index()
    result.name = series.name
    return result


def deflate_nominal_series(series: pd.Series, cpi_quarterly: pd.Series | None) -> pd.Series:
    """Deflate a nominal quarterly series using quarterly average CPI."""
    if cpi_quarterly is None or cpi_quarterly.empty:
        return series.copy()
    aligned = pd.concat([series, cpi_quarterly.rename("cpi")], axis=1)
    real = aligned.iloc[:, 0] / aligned["cpi"] * 100.0
    real.name = series.name
    return real


def align_quarterly_series(series_map: dict[str, pd.Series]) -> pd.DataFrame:
    """Outer-join all quarterly series on a shared quarterly index."""
    if not series_map:
        return pd.DataFrame(columns=list(TARGET_SERIES))
    dataset = pd.concat(series_map.values(), axis=1, sort=True)
    dataset = dataset.reindex(columns=list(TARGET_SERIES))
    dataset.index = dataset.index.astype(str)
    return dataset


def trim_leading_sparse_rows(dataset: pd.DataFrame) -> pd.DataFrame:
    """Drop leading rows before the dataset starts to carry usable information."""
    if dataset.empty:
        return dataset
    non_empty_mask = dataset.notna().any(axis=1)
    if not non_empty_mask.any():
        return dataset.iloc[0:0].copy()
    first_valid_position = int(np.argmax(non_empty_mask.to_numpy()))
    return dataset.iloc[first_valid_position:].copy()


def summarize_dataset(dataset: pd.DataFrame) -> dict[str, object]:
    """Return a summary of the processed quarterly dataset."""
    if dataset.empty:
        return {
            "sample_start": None,
            "sample_end": None,
            "observations": 0,
            "missing_by_column": {column: 0 for column in dataset.columns},
        }
    return {
        "sample_start": dataset.index[0],
        "sample_end": dataset.index[-1],
        "observations": len(dataset),
        "missing_by_column": dataset.isna().sum().to_dict(),
    }


def infer_frequency(index: pd.PeriodIndex) -> str:
    """Infer whether a PeriodIndex is monthly or quarterly."""
    if index.freqstr[0] == "M":
        return "monthly"
    if index.freqstr[0] == "Q":
        return "quarterly"
    raise ValueError(f"Unsupported PeriodIndex frequency '{index.freqstr}'.")


def _parse_period_index(values: pd.Series) -> pd.PeriodIndex:
    """Parse raw date strings into a monthly or quarterly PeriodIndex."""
    if values.empty:
        return pd.PeriodIndex([], freq="Q")

    sample = values.iloc[0]
    if "Q" in sample:
        return pd.PeriodIndex(values, freq="Q")
    if len(sample) == 7 and sample.count("-") == 1:
        return pd.PeriodIndex(values, freq="M")

    parsed = pd.to_datetime(values, errors="coerce")
    if parsed.isna().any():
        raise ValueError("Could not parse one or more raw date values.")
    inferred = pd.infer_freq(parsed.sort_values())
    if inferred and inferred.startswith("Q"):
        return pd.PeriodIndex(parsed, freq="Q")
    return pd.PeriodIndex(parsed, freq="M")
