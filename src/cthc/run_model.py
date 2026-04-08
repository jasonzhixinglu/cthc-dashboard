"""Top-level orchestration for the fixed-parameter CTHC model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CTHCConfig, load_config
from .export_json import model_result_to_payload
from .kalman import KalmanFilterResult, run_kalman_filter
from .model_matrices import ModelMatrices, build_model_matrices
from .smoother import SmootherResult, run_rts_smoother


@dataclass(frozen=True)
class ModelRunResult:
    """Structured output for the fixed-parameter CTHC pipeline."""

    config: CTHCConfig
    matrices: ModelMatrices
    filter_result: KalmanFilterResult
    smoother_result: SmootherResult
    observed_data: pd.DataFrame
    filtered_states: pd.DataFrame
    smoothed_states: pd.DataFrame
    fitted_values: pd.DataFrame
    output_gap_series: pd.Series
    potential_growth_series: pd.Series
    sector_share_series: pd.DataFrame

    def to_payload(self) -> dict[str, object]:
        """Serialize the result to a JSON-compatible payload."""
        return model_result_to_payload(self)


def run_fixed_parameter_model(
    data: pd.DataFrame,
    *,
    config_path: str | Path = Path("configs/baseline.yaml"),
) -> ModelRunResult:
    """Load config, build matrices, and run filtering and smoothing on a DataFrame."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")

    config = load_config(config_path)
    matrices = build_model_matrices(config)
    observations = _extract_observations(data, matrices.measurement_names)
    filter_result = run_kalman_filter(observations, matrices)
    smoother_result = run_rts_smoother(filter_result, matrices)

    state_index = data.index
    filtered_states = pd.DataFrame(
        filter_result.filtered_states,
        index=state_index,
        columns=matrices.state_names,
    )
    smoothed_states = pd.DataFrame(
        smoother_result.smoothed_states,
        index=state_index,
        columns=matrices.state_names,
    )
    fitted_values = _build_fitted_values(smoothed_states, matrices, state_index)
    output_gap_series = pd.Series(
        smoothed_states["c_t"].to_numpy(copy=False),
        index=state_index,
        name="output_gap",
    )
    potential_growth_series = pd.Series(
        smoothed_states["g_t"].to_numpy(copy=False),
        index=state_index,
        name="potential_growth",
    )
    sector_share_series = _build_sector_share_series(
        smoothed_states=smoothed_states,
        matrices=matrices,
        index=state_index,
    )

    return ModelRunResult(
        config=config,
        matrices=matrices,
        filter_result=filter_result,
        smoother_result=smoother_result,
        observed_data=data.loc[:, list(matrices.measurement_names)].copy(),
        filtered_states=filtered_states,
        smoothed_states=smoothed_states,
        fitted_values=fitted_values,
        output_gap_series=output_gap_series,
        potential_growth_series=potential_growth_series,
        sector_share_series=sector_share_series,
    )


def _extract_observations(
    data: pd.DataFrame,
    measurement_names: tuple[str, ...],
) -> np.ndarray:
    """Return the observation matrix in measurement order."""
    missing_columns = [column for column in measurement_names if column not in data.columns]
    if missing_columns:
        raise ValueError(
            "DataFrame is missing required columns: " + ", ".join(missing_columns)
        )
    return data.loc[:, list(measurement_names)].astype(float).to_numpy()


def _build_fitted_values(
    smoothed_states: pd.DataFrame,
    matrices: ModelMatrices,
    index: pd.Index,
) -> pd.DataFrame:
    """Project smoothed states into measurement space."""
    fitted = smoothed_states.to_numpy(copy=False) @ matrices.measurement.T
    return pd.DataFrame(fitted, index=index, columns=matrices.measurement_names)


def _build_sector_share_series(
    *,
    smoothed_states: pd.DataFrame,
    matrices: ModelMatrices,
    index: pd.Index,
) -> pd.DataFrame:
    """Compute per-sector shares from sector-specific latent components."""
    sector_names = matrices.measurement_names[1:]
    sector_values = np.column_stack(
        [
            smoothed_states[f"theta_{sector_name}"].to_numpy(copy=False)
            for sector_name in sector_names
        ]
    )
    totals = sector_values.sum(axis=1, keepdims=True)
    shares = np.divide(
        sector_values,
        totals,
        out=np.zeros_like(sector_values),
        where=np.abs(totals) > 1e-12,
    )
    return pd.DataFrame(shares, index=index, columns=sector_names)
