"""JSON export helpers for model results and frontend site payloads."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from .run_model import ModelRunResult


def model_result_to_payload(
    result: "ModelRunResult",
    *,
    scenario_name: str = "baseline",
    last_updated: str | None = None,
    include_legacy_aliases: bool = False,
) -> dict[str, object]:
    """Convert a model run result into JSON-serializable frontend payload blocks."""
    resolved_timestamp = last_updated or current_timestamp()
    return {
        "summary": build_summary_payload(
            result,
            scenario_name=scenario_name,
            last_updated=resolved_timestamp,
            include_legacy_aliases=include_legacy_aliases,
        ),
        "series": build_series_payload(
            result,
            scenario_name=scenario_name,
            last_updated=resolved_timestamp,
            include_legacy_aliases=include_legacy_aliases,
        ),
        "sectors": build_sectors_payload(
            result,
            scenario_name=scenario_name,
            last_updated=resolved_timestamp,
            include_legacy_aliases=include_legacy_aliases,
        ),
    }


def model_result_to_json(
    result: "ModelRunResult",
    *,
    indent: int = 2,
    scenario_name: str = "baseline",
    last_updated: str | None = None,
    include_legacy_aliases: bool = False,
) -> str:
    """Serialize the full frontend payload bundle to JSON."""
    return json.dumps(
        model_result_to_payload(
            result,
            scenario_name=scenario_name,
            last_updated=last_updated,
            include_legacy_aliases=include_legacy_aliases,
        ),
        indent=indent,
        sort_keys=True,
    )


def export_site_payload(
    result: "ModelRunResult",
    *,
    output_dir: str | Path = Path("web/public/data"),
    scenario_name: str = "baseline",
    last_updated: str | None = None,
    display_end: str | None = None,
    include_legacy_aliases: bool = False,
) -> dict[str, Path]:
    """Write frontend-ready JSON payload files into the public data directory."""
    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    resolved_timestamp = last_updated or current_timestamp()

    payloads = {
        "summary.json": build_summary_payload(
            result,
            scenario_name=scenario_name,
            last_updated=resolved_timestamp,
            display_end=display_end,
            include_legacy_aliases=include_legacy_aliases,
        ),
        "series.json": build_series_payload(
            result,
            scenario_name=scenario_name,
            last_updated=resolved_timestamp,
            include_legacy_aliases=include_legacy_aliases,
        ),
        "sectors.json": build_sectors_payload(
            result,
            scenario_name=scenario_name,
            last_updated=resolved_timestamp,
            include_legacy_aliases=include_legacy_aliases,
        ),
    }

    written_files: dict[str, Path] = {}
    for filename, payload in payloads.items():
        target_path = resolved_output_dir / filename
        target_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written_files[filename] = target_path
    return written_files


def build_summary_payload(
    result: "ModelRunResult",
    *,
    scenario_name: str,
    last_updated: str,
    display_end: str | None = None,
    include_legacy_aliases: bool = False,
) -> dict[str, object]:
    """Build summary metrics for the frontend."""
    latest_index = result.smoothed_states.index[-1] if len(result.smoothed_states.index) else None
    payload = {
        "last_updated": _normalize_timestamp(last_updated),
        "scenario": scenario_name,
        "display_start": "2005-Q1",
        "display_end": display_end,
        "latest_output_gap": (
            None if latest_index is None
            else result.output_gap_series.iloc[-1] / 100.0
        ),
        "latest_potential_growth": (
            None if latest_index is None
            else result.potential_growth_series.iloc[-1] / 100.0 * 400.0
        ),
        "sample_end": _serialize_scalar(latest_index),
    }
    if include_legacy_aliases:
        payload["scenario_name"] = scenario_name
        payload["latest_period"] = _serialize_scalar(latest_index)
    return _make_serializable(
        payload
    )


def build_series_payload(
    result: "ModelRunResult",
    *,
    scenario_name: str,
    last_updated: str,
    include_legacy_aliases: bool = False,
) -> dict[str, object]:
    """Build time-series payloads for the frontend."""
    dates = [_serialize_scalar(value) for value in result.smoothed_states.index.tolist()]

    # c_t is in log×100 units; divide by 100 to get natural-log deviations
    # (≈ percentage-point output gap, e.g. −2.5 log×100 → −0.025 ≈ −2.5 %)
    output_gap_scaled = result.output_gap_series.to_numpy() / 100.0
    # g_t is a quarterly log×100 growth rate; convert to annualised percent
    # g_t / 100 * 400 = g_t * 4  (e.g. 1.3 log×100/quarter → 5.2 % p.a.)
    potential_growth_scaled = result.potential_growth_series.to_numpy() / 100.0 * 400.0
    # mu_t (trend level) is in log×100; divide by 100 to match observed GDP scale
    gdp_trend_scaled = result.smoothed_states["mu_t"].to_numpy() / 100.0

    gap_bands = _posterior_bands(result, "c_t", output_gap_scaled, scale=1.0 / 100.0)
    growth_bands = _posterior_bands(
        result, "g_t", potential_growth_scaled, scale=400.0 / 100.0
    )

    payload = {
        "last_updated": _normalize_timestamp(last_updated),
        "scenario": scenario_name,
        "dates": dates,
        "output_gap": output_gap_scaled.tolist(),
        "output_gap_p16": gap_bands["p16"],
        "output_gap_p84": gap_bands["p84"],
        "output_gap_p025": gap_bands["p025"],
        "output_gap_p975": gap_bands["p975"],
        "potential_growth": potential_growth_scaled.tolist(),
        "potential_growth_p16": growth_bands["p16"],
        "potential_growth_p84": growth_bands["p84"],
        "potential_growth_p025": growth_bands["p025"],
        "potential_growth_p975": growth_bands["p975"],
        "gdp_observed": result.observed_data["gdp"].tolist(),
        "gdp_trend": gdp_trend_scaled.tolist(),
    }
    if include_legacy_aliases:
        payload["scenario_name"] = scenario_name
        payload["periods"] = dates
        payload["output_gap_series"] = _build_legacy_series_records(
            dates,
            result.output_gap_series.tolist(),
        )
        payload["potential_growth_series"] = _build_legacy_series_records(
            dates,
            result.potential_growth_series.tolist(),
        )
    return _make_serializable(
        payload
    )


def build_sectors_payload(
    result: "ModelRunResult",
    *,
    scenario_name: str,
    last_updated: str,
    include_legacy_aliases: bool = False,
) -> dict[str, object]:
    """Build sector-oriented payloads for the frontend."""
    sector_names = list(result.sector_share_series.columns)
    dates = [_serialize_scalar(value) for value in result.sector_share_series.index.tolist()]
    payload = {
        "last_updated": _normalize_timestamp(last_updated),
        "scenario": scenario_name,
        "dates": dates,
        "sector_names": sector_names,
        "shares": {
            sector_name: result.sector_share_series[sector_name].tolist()
            for sector_name in sector_names
        },
        "theta": {
            sector_name: result.smoothed_states[f"theta_{sector_name}"].tolist()
            for sector_name in sector_names
        },
    }
    if include_legacy_aliases:
        payload["scenario_name"] = scenario_name
        payload["sector_share_series"] = [
            {"index": dates[index], **{
                sector_name: result.sector_share_series[sector_name].tolist()[index]
                for sector_name in sector_names
            }}
            for index in range(len(dates))
        ]
    return _make_serializable(
        payload
    )


def _posterior_bands(
    result: "ModelRunResult",
    state_name: str,
    mean: "np.ndarray",
    *,
    scale: float = 1.0,
) -> dict[str, list]:
    """Return ±1σ and ±2σ posterior bands for a named state.

    Uses the diagonal of smoothed_covariances to get the posterior variance
    at each time point, then builds symmetric bands around the smoothed mean.
    Returns four lists: p16, p84 (±1σ) and p025, p975 (±2σ).
    """
    state_names = result.matrices.state_names
    if state_name not in state_names:
        nones: list = [None] * len(mean)
        return {"p16": nones, "p84": nones, "p025": nones, "p975": nones}

    idx = state_names.index(state_name)
    variances = result.smoother_result.smoothed_covariances[:, idx, idx]
    std = np.sqrt(np.maximum(variances, 0.0)) * scale

    return {
        "p16": (mean - std).tolist(),
        "p84": (mean + std).tolist(),
        "p025": (mean - 2.0 * std).tolist(),
        "p975": (mean + 2.0 * std).tolist(),
    }


def current_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _make_serializable(value: Any) -> Any:
    """Recursively coerce supported scientific Python types to JSON-safe types."""
    if isinstance(value, dict):
        return {str(key): _make_serializable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_make_serializable(item) for item in value]
    if isinstance(value, tuple):
        return [_make_serializable(item) for item in value]
    return _serialize_scalar(value)


def _serialize_scalar(value: Any) -> Any:
    """Coerce scalar values to JSON-safe Python primitives."""
    if value is None:
        return None
    if isinstance(value, np.generic):
        return _serialize_scalar(value.item())
    if isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not np.isfinite(value):
            return None
        return value
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if pd.isna(value):
        return None
    return str(value)


def _normalize_timestamp(value: str) -> str:
    """Convert an ISO timestamp to a frontend-friendly date when possible."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return value


def _build_legacy_series_records(
    dates: list[Any],
    values: list[Any],
) -> list[dict[str, Any]]:
    """Build legacy series records with ``index`` and ``value`` fields."""
    return [
        {"index": dates[index], "value": values[index] if index < len(values) else None}
        for index in range(len(dates))
    ]
