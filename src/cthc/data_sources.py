"""Source registry and raw data fetch helpers for the CTHC China dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests

RAW_DATA_DIR = Path("data/raw")
OECD_API_BASE = "https://sdmx.oecd.org/public/rest/data"
IMF_API_BASE = "https://api.imf.org/external/sdmx/2.1/data"

TARGET_SERIES = (
    "gdp",
    "imports",
    "electricity",
    "industrial_va",
    "retail_sales",
    "fixed_asset_investment",
    "cpi",
)


@dataclass(frozen=True)
class SeriesDefinition:
    """Metadata describing one raw source and quarterly transformation path."""

    variable_name: str
    preferred_source: str
    fallback_sources: tuple[str, ...]
    source_type: str
    endpoint: str | None
    expected_frequency: str
    units_description: str
    is_nominal: bool
    observation_kind: str
    cumulative_within_year: bool
    proxy_definition: str
    download_url_env: str | None = None
    download_url: str | None = None
    dataset_code: str | None = None
    resource_id: str | None = None
    resource_version: str | None = None
    dimension_order: tuple[str, ...] = ()
    key_overrides: dict[str, str] | None = None
    source_filters: dict[str, str] | None = None
    manual_csv: str | None = None
    imf_resource_id: str | None = None
    imf_resource_version: str | None = None
    imf_dimension_order: tuple[str, ...] = ()
    imf_key_overrides: dict[str, str] | None = None
    imf_filters: dict[str, str] | None = None


@dataclass(frozen=True)
class FetchResult:
    """Outcome of fetching a single series."""

    series_name: str
    success: bool
    source_used: str
    output_path: Path | None
    message: str


def get_source_registry() -> dict[str, SeriesDefinition]:
    """Return source metadata for all model input series."""
    return {
        "gdp": SeriesDefinition(
            variable_name="gdp",
            preferred_source="oecd",
            fallback_sources=("imf", "manual_csv"),
            source_type="api",
            endpoint="OECD QNA Developer API, China quarterly GDP level",
            expected_frequency="quarterly",
            units_description="Quarterly GDP level, current prices, national currency",
            is_nominal=True,
            observation_kind="flow",
            cumulative_within_year=False,
            proxy_definition="Quarterly GDP level from OECD QNA developer feed.",
            download_url_env="CTHC_GDP_OECD_URL",
            dataset_code="OECD.SDD.NAD:DSD_NAMAIN1@DF_QNA",
            resource_id="OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA",
            resource_version="1.1",
            dimension_order=(
                "FREQ",
                "ADJUSTMENT",
                "REF_AREA",
                "SECTOR",
                "COUNTERPART_SECTOR",
                "TRANSACTION",
                "INSTR_ASSET",
                "ACTIVITY",
                "EXPENDITURE",
                "UNIT_MEASURE",
                "PRICE_BASE",
                "TRANSFORMATION",
                "TABLE_IDENTIFIER",
            ),
            key_overrides={"FREQ": "Q", "REF_AREA": "CHN"},
            source_filters={
                "ADJUSTMENT": "N",
                "SECTOR": "S1",
                "COUNTERPART_SECTOR": "S1",
                "TRANSACTION": "B1GQ",
                "UNIT_MEASURE": "XDC",
                "PRICE_BASE": "Q",
                "TRANSFORMATION": "N",
                "TABLE_IDENTIFIER": "T0102",
            },
            manual_csv="gdp_manual.csv",
            imf_resource_id="NEA_Q",
            imf_dimension_order=("REF_AREA", "INDICATOR", "FREQ"),
        ),
        "imports": SeriesDefinition(
            variable_name="imports",
            preferred_source="oecd",
            fallback_sources=("imf", "manual_csv"),
            source_type="api",
            endpoint="OECD IMTS monthly imports, world counterpart, merchandise value",
            expected_frequency="monthly",
            units_description="Monthly imports, USD current prices",
            is_nominal=True,
            observation_kind="flow",
            cumulative_within_year=False,
            proxy_definition="OECD international merchandise trade statistics, imports from world.",
            download_url_env="CTHC_IMPORTS_OECD_URL",
            dataset_code="OECD.SDD.TPS:DSD_IMTS@DF_IMTS",
            resource_id="OECD.SDD.TPS,DSD_IMTS@DF_IMTS",
            resource_version="1.0",
            dimension_order=(
                "REF_AREA",
                "COUNTERPART_AREA",
                "TRADE_FLOW",
                "PRODUCT_TYPE",
                "FREQ",
                "UNIT_MEASURE",
                "ADJUSTMENT",
                "TRANSFORMATION",
            ),
            key_overrides={"REF_AREA": "CHN", "FREQ": "M"},
            source_filters={
                "COUNTERPART_AREA": "W",
                "TRADE_FLOW": "M",
                "PRODUCT_TYPE": "C",
                "UNIT_MEASURE": "USD_EXC",
                "ADJUSTMENT": "N",
                "TRANSFORMATION": "N",
                "PRICES": "V",
            },
            manual_csv="imports_manual.csv",
            imf_resource_id="ITG",
            imf_dimension_order=("REF_AREA", "INDICATOR", "FREQ"),
        ),
        "electricity": SeriesDefinition(
            variable_name="electricity",
            preferred_source="manual_csv",
            fallback_sources=(),
            source_type="manual_csv",
            endpoint="Manual fallback only unless a stable official machine-readable source is configured later",
            expected_frequency="monthly",
            units_description="Monthly electricity production proxy, index or level",
            is_nominal=False,
            observation_kind="index",
            cumulative_within_year=False,
            proxy_definition="Manual official electricity production drop-in CSV.",
            download_url_env="CTHC_ELECTRICITY_OECD_URL",
            dataset_code="Manual fallback",
            manual_csv="electricity_manual.csv",
        ),
        "industrial_va": SeriesDefinition(
            variable_name="industrial_va",
            preferred_source="oecd",
            fallback_sources=("imf", "manual_csv"),
            source_type="api",
            endpoint="OECD KEI manufacturing production index as industrial activity proxy",
            expected_frequency="monthly",
            units_description="Monthly manufacturing production index",
            is_nominal=False,
            observation_kind="index",
            cumulative_within_year=False,
            proxy_definition="OECD Key Economic Indicators manufacturing production index as industrial value-added proxy.",
            download_url_env="CTHC_INDUSTRIAL_VA_OECD_URL",
            dataset_code="OECD.SDD.STES:DSD_KEI@DF_KEI",
            resource_id="OECD.SDD.STES,DSD_KEI@DF_KEI",
            resource_version="4.0",
            dimension_order=(
                "REF_AREA",
                "FREQ",
                "MEASURE",
                "UNIT_MEASURE",
                "ACTIVITY",
                "ADJUSTMENT",
                "TRANSFORMATION",
            ),
            key_overrides={"REF_AREA": "CHN", "FREQ": "M"},
            source_filters={
                "MEASURE": "MANM",
                "UNIT_MEASURE": "IX",
                "ACTIVITY": "_Z",
                "ADJUSTMENT": "Y",
                "TRANSFORMATION": "_Z",
            },
            manual_csv="industrial_va_manual.csv",
            imf_resource_id="IPI",
            imf_dimension_order=("REF_AREA", "INDICATOR", "FREQ"),
        ),
        "retail_sales": SeriesDefinition(
            variable_name="retail_sales",
            preferred_source="oecd",
            fallback_sources=("imf", "manual_csv"),
            source_type="api",
            endpoint="OECD KEI retail sales index",
            expected_frequency="monthly",
            units_description="Monthly retail sales index",
            is_nominal=False,
            observation_kind="index",
            cumulative_within_year=False,
            proxy_definition="OECD Key Economic Indicators retail sales index.",
            download_url_env="CTHC_RETAIL_SALES_OECD_URL",
            dataset_code="OECD.SDD.STES:DSD_KEI@DF_KEI",
            resource_id="OECD.SDD.STES,DSD_KEI@DF_KEI",
            resource_version="4.0",
            dimension_order=(
                "REF_AREA",
                "FREQ",
                "MEASURE",
                "UNIT_MEASURE",
                "ACTIVITY",
                "ADJUSTMENT",
                "TRANSFORMATION",
            ),
            key_overrides={"REF_AREA": "CHN", "FREQ": "M"},
            source_filters={
                "MEASURE": "RS",
                "UNIT_MEASURE": "IX",
                "ACTIVITY": "_T",
                "ADJUSTMENT": "RT",
                "TRANSFORMATION": "_Z",
            },
            manual_csv="retail_sales_manual.csv",
            imf_resource_id="RTV",
            imf_dimension_order=("REF_AREA", "INDICATOR", "FREQ"),
        ),
        "fixed_asset_investment": SeriesDefinition(
            variable_name="fixed_asset_investment",
            preferred_source="nbs",
            fallback_sources=("manual_csv",),
            source_type="manual_csv",
            endpoint="Official NBS fixed asset investment release, with manual CSV fallback",
            expected_frequency="monthly",
            units_description="Monthly cumulative fixed asset investment excluding rural households, current-price level",
            is_nominal=True,
            observation_kind="flow",
            cumulative_within_year=True,
            proxy_definition="Official NBS fixed asset investment (excluding rural households), usually cumulative within year.",
            download_url_env="CTHC_FIXED_ASSET_INVESTMENT_NBS_URL",
            dataset_code="NBS FAI release",
            manual_csv="fixed_asset_investment_manual.csv",
        ),
        "cpi": SeriesDefinition(
            variable_name="cpi",
            preferred_source="oecd",
            fallback_sources=("imf", "manual_csv"),
            source_type="api",
            endpoint="OECD CPI exchange API, China all-items CPI index",
            expected_frequency="monthly",
            units_description="Monthly CPI index, all items",
            is_nominal=False,
            observation_kind="index",
            cumulative_within_year=False,
            proxy_definition="OECD CPI exchange feed, all-items CPI index for China.",
            download_url_env="CTHC_CPI_OECD_URL",
            dataset_code="OECD.SDD.TPS:DSD_PRICES_EXC@DF_PRICES_EXCHANGE",
            resource_id="OECD.SDD.TPS,DSD_PRICES_EXC@DF_PRICES_EXCHANGE",
            resource_version="1.0",
            dimension_order=(
                "REF_AREA",
                "FREQ",
                "METHODOLOGY",
                "MEASURE",
                "UNIT_MEASURE",
                "EXPENDITURE",
                "ADJUSTMENT",
                "TRANSFORMATION",
            ),
            key_overrides={"REF_AREA": "CHN", "FREQ": "M"},
            source_filters={
                "METHODOLOGY": "N",
                "MEASURE": "CPI",
                "UNIT_MEASURE": "IX",
                "EXPENDITURE": "_T",
                "ADJUSTMENT": "N",
                "TRANSFORMATION": "_Z",
                "BASE_PER": "2020Y",
            },
            manual_csv="cpi_manual.csv",
            imf_resource_id="CPI",
            imf_dimension_order=("REF_AREA", "INDICATOR", "FREQ"),
        ),
    }


def fetch_all_series(
    series_names: list[str] | None = None,
    *,
    raw_dir: Path = RAW_DATA_DIR,
    timeout_seconds: int = 30,
) -> list[FetchResult]:
    """Fetch a set of target series and save standardized raw CSV files."""
    registry = get_source_registry()
    selected = series_names or list(TARGET_SERIES)
    results: list[FetchResult] = []
    raw_dir.mkdir(parents=True, exist_ok=True)

    for series_name in selected:
        if series_name not in registry:
            results.append(
                FetchResult(
                    series_name=series_name,
                    success=False,
                    source_used="registry",
                    output_path=None,
                    message="Unknown series name.",
                )
            )
            continue
        results.append(fetch_series(registry[series_name], raw_dir=raw_dir, timeout_seconds=timeout_seconds))
    return results


def fetch_series(
    spec: SeriesDefinition,
    *,
    raw_dir: Path = RAW_DATA_DIR,
    timeout_seconds: int = 30,
) -> FetchResult:
    """Fetch one series using the preferred source and configured fallbacks."""
    raw_dir.mkdir(parents=True, exist_ok=True)

    fetch_attempts = (spec.preferred_source,) + spec.fallback_sources
    last_error = "No source attempt was made."

    for source_name in fetch_attempts:
        try:
            frame = _fetch_from_source(
                spec,
                source_name=source_name,
                raw_dir=raw_dir,
                timeout_seconds=timeout_seconds,
            )
            output_path = save_standardized_raw_csv(spec.variable_name, frame, raw_dir=raw_dir)
            return FetchResult(
                series_name=spec.variable_name,
                success=True,
                source_used=source_name,
                output_path=output_path,
                message=f"Fetched {len(frame)} observations.",
            )
        except Exception as error:  # noqa: BLE001
            last_error = str(error)

    placeholder_path = ensure_empty_raw_csv(spec.variable_name, raw_dir=raw_dir)
    manual_path = ensure_manual_csv_template(spec, raw_dir=raw_dir)
    message = last_error
    if placeholder_path is not None:
        message = f"{message} Placeholder raw CSV created at {placeholder_path}."
    if manual_path is not None:
        message = f"{message} Manual fallback template available at {manual_path}."
    return FetchResult(
        series_name=spec.variable_name,
        success=False,
        source_used=fetch_attempts[-1],
        output_path=placeholder_path,
        message=message,
    )


def fetch_oecd_series(
    spec: SeriesDefinition,
    *,
    timeout_seconds: int = 30,
) -> pd.DataFrame:
    """Fetch an OECD SDMX CSV series and normalize it to ``date,value`` columns."""
    url = _resolve_download_url(spec, default_base=OECD_API_BASE, source_name="oecd")
    if not url:
        if not spec.resource_id or not spec.resource_version or not spec.dimension_order:
            raise ValueError(
                f"No OECD API configuration is available for '{spec.variable_name}'."
            )
        key = build_sdmx_key(spec.dimension_order, spec.key_overrides or {})
        url = f"{OECD_API_BASE}/{spec.resource_id},{spec.resource_version}/{key}?format=csvfile"
    frame = _read_csv_url(url, timeout_seconds=timeout_seconds)
    return _standardize_observation_frame(frame, spec, source_label="oecd")


def fetch_imf_series(
    spec: SeriesDefinition,
    *,
    timeout_seconds: int = 30,
) -> pd.DataFrame:
    """Fetch an IMF series from a configured JSON or CSV endpoint."""
    url = _resolve_download_url(spec, default_base=IMF_API_BASE, source_name="imf")
    if not url:
        if not spec.imf_resource_id or not spec.imf_dimension_order:
            raise ValueError(
                f"No IMF API configuration is available for '{spec.variable_name}'."
            )
        key = build_sdmx_key(spec.imf_dimension_order, spec.imf_key_overrides or {})
        version_part = f",{spec.imf_resource_version}" if spec.imf_resource_version else ""
        url = f"{IMF_API_BASE}/{spec.imf_resource_id}{version_part}/{key}"

    response = requests.get(
        url,
        timeout=timeout_seconds,
        headers={"Accept": "application/vnd.sdmx.data+json;version=1.0.0-wd"},
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "csv" in content_type:
        frame = pd.read_csv(StringIO(response.text))
    else:
        frame = _frame_from_imf_json(response.json())
    return _standardize_observation_frame(frame, spec, source_label="imf")


def fetch_nbs_series(
    spec: SeriesDefinition,
    *,
    raw_dir: Path = RAW_DATA_DIR,
    timeout_seconds: int = 30,
) -> pd.DataFrame:
    """Fetch an NBS series, preferring a clean manual CSV when present."""
    manual_path = _manual_csv_path(spec, raw_dir=raw_dir)
    if manual_path and manual_path.exists():
        frame = read_standardized_raw_csv(manual_path)
        if frame.empty:
            raise ValueError(f"Manual CSV fallback '{manual_path}' is empty.")
        return frame

    url = _resolve_download_url(spec, default_base=None, source_name="nbs")
    if not url:
        raise ValueError(
            f"No automated NBS URL is configured for '{spec.variable_name}', and "
            f"manual fallback '{manual_path}' is not present."
        )
    frame = _read_csv_url(url, timeout_seconds=timeout_seconds)
    return _standardize_observation_frame(frame, spec, source_label="nbs")


def read_standardized_raw_csv(path: Path) -> pd.DataFrame:
    """Read a standardized raw CSV and return ``date,value`` plus metadata columns."""
    frame = pd.read_csv(path)
    if "date" not in frame.columns or "value" not in frame.columns:
        raise ValueError(f"Raw CSV '{path}' must contain 'date' and 'value' columns.")
    return frame


def save_standardized_raw_csv(
    series_name: str,
    frame: pd.DataFrame,
    *,
    raw_dir: Path = RAW_DATA_DIR,
) -> Path:
    """Save a standardized raw series CSV under ``data/raw/<series>.csv``."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / f"{series_name}.csv"
    ordered = frame.copy()
    ordered["date"] = ordered["date"].astype(str)
    ordered = ordered.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    ordered.to_csv(output_path, index=False)
    return output_path


def ensure_manual_csv_template(spec: SeriesDefinition, *, raw_dir: Path = RAW_DATA_DIR) -> Path | None:
    """Create an empty manual CSV template when a series supports manual fallback."""
    manual_path = _manual_csv_path(spec, raw_dir=raw_dir)
    if manual_path is None or manual_path.exists():
        return manual_path
    pd.DataFrame(columns=["date", "value"]).to_csv(manual_path, index=False)
    return manual_path


def ensure_empty_raw_csv(series_name: str, *, raw_dir: Path = RAW_DATA_DIR) -> Path:
    """Ensure a standardized placeholder raw CSV exists for a series."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / f"{series_name}.csv"
    if not output_path.exists():
        pd.DataFrame(columns=["date", "value", "source", "units", "fetched_at"]).to_csv(
            output_path,
            index=False,
        )
    return output_path


def build_sdmx_key(
    dimension_order: tuple[str, ...],
    key_overrides: dict[str, str],
) -> str:
    """Build an SDMX key path from a dimension order and selected constraints."""
    return ".".join(key_overrides.get(dimension, "") for dimension in dimension_order)


def _fetch_from_source(
    spec: SeriesDefinition,
    *,
    source_name: str,
    raw_dir: Path,
    timeout_seconds: int,
) -> pd.DataFrame:
    """Dispatch fetching by source name."""
    if source_name == "oecd":
        return fetch_oecd_series(spec, timeout_seconds=timeout_seconds)
    if source_name == "imf":
        return fetch_imf_series(spec, timeout_seconds=timeout_seconds)
    if source_name == "nbs":
        return fetch_nbs_series(spec, raw_dir=raw_dir, timeout_seconds=timeout_seconds)
    if source_name == "manual_csv":
        manual_path = _manual_csv_path(spec, raw_dir=raw_dir)
        if manual_path is None or not manual_path.exists():
            raise ValueError(f"Manual CSV fallback '{manual_path}' is not available.")
        frame = read_standardized_raw_csv(manual_path)
        if frame.empty:
            raise ValueError(f"Manual CSV fallback '{manual_path}' is empty.")
        return frame
    raise ValueError(f"Unsupported source '{source_name}'.")


def _resolve_download_url(
    spec: SeriesDefinition,
    *,
    default_base: str | None,
    source_name: str,
) -> str | None:
    """Resolve the most specific configured endpoint URL for a series."""
    if spec.download_url_env:
        env_value = os.getenv(spec.download_url_env)
        if env_value:
            return env_value
    if spec.download_url:
        return spec.download_url
    if source_name == "oecd" and default_base and spec.resource_id and spec.resource_version and spec.dimension_order:
        key = build_sdmx_key(spec.dimension_order, spec.key_overrides or {})
        return f"{default_base}/{spec.resource_id},{spec.resource_version}/{key}?format=csvfile"
    if source_name == "imf" and default_base and spec.imf_resource_id and spec.imf_dimension_order:
        key = build_sdmx_key(spec.imf_dimension_order, spec.imf_key_overrides or {})
        version_part = f",{spec.imf_resource_version}" if spec.imf_resource_version else ""
        return f"{default_base}/{spec.imf_resource_id}{version_part}/{key}"
    return None


def _read_csv_url(url: str, *, timeout_seconds: int) -> pd.DataFrame:
    """Download a CSV endpoint into a DataFrame."""
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


def _standardize_observation_frame(
    frame: pd.DataFrame,
    spec: SeriesDefinition,
    *,
    source_label: str,
) -> pd.DataFrame:
    """Normalize a source-specific frame into the standard raw schema."""
    if "NoRecordsFound" in frame.columns:
        raise ValueError(f"No records found for '{spec.variable_name}' from {source_label}.")

    filtered = frame.copy()
    filters = (spec.imf_filters if source_label == "imf" else spec.source_filters) or {}
    for key, expected in filters.items():
        if key in filtered.columns:
            filtered = filtered.loc[filtered[key].astype(str) == expected]

    date_column = _find_first_column(
        filtered.columns,
        ("date", "DATE", "TIME_PERIOD", "TIME", "time_period", "REF_DATE"),
    )
    value_column = _find_first_column(
        filtered.columns,
        ("value", "VALUE", "Value", "OBS_VALUE", "obs_value"),
    )
    if date_column is None or value_column is None:
        raise ValueError(
            f"Could not identify date/value columns for '{spec.variable_name}' from {source_label}."
        )

    standardized = pd.DataFrame(
        {
            "date": filtered[date_column].astype(str),
            "value": pd.to_numeric(filtered[value_column], errors="coerce"),
            "source": source_label,
            "units": spec.units_description,
            "fetched_at": current_timestamp(),
        }
    ).dropna(subset=["date", "value"])

    if standardized.empty:
        raise ValueError(f"No observations remained after standardizing '{spec.variable_name}'.")
    return standardized


def _frame_from_imf_json(payload: Any) -> pd.DataFrame:
    """Build a DataFrame from a simple IMF JSON series payload."""
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], list):
        return pd.DataFrame(payload["data"])
    if isinstance(payload, dict) and "observations" in payload and isinstance(payload["observations"], list):
        return pd.DataFrame(payload["observations"])
    raise ValueError("Unsupported IMF JSON payload structure.")


def _find_first_column(columns: Any, candidates: tuple[str, ...]) -> str | None:
    """Return the first candidate column present in a DataFrame."""
    available = {str(column): str(column) for column in columns}
    for candidate in candidates:
        if candidate in available:
            return available[candidate]
    return None


def _manual_csv_path(spec: SeriesDefinition, *, raw_dir: Path) -> Path | None:
    """Resolve the manual fallback CSV path for a series, when configured."""
    if not spec.manual_csv:
        return None
    return raw_dir / spec.manual_csv


def current_timestamp() -> str:
    """Return the current UTC timestamp as ISO 8601."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
