"""Rauch-Tung-Striebel smoother for the fixed-parameter CTHC model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import cho_factor, cho_solve

from .kalman import KalmanFilterResult
from .model_matrices import ModelMatrices

Matrix = NDArray[np.float64]


@dataclass(frozen=True)
class SmootherResult:
    """Smoothed latent state estimates.

    Array dimensions:
    - ``smoothed_states``: ``(T, n_state)``
    - ``smoothed_covariances``: ``(T, n_state, n_state)``
    - ``log_likelihood``: scalar copied from the filter result
    """

    smoothed_states: Matrix
    smoothed_covariances: NDArray[np.float64]
    log_likelihood: float


def run_rts_smoother(
    filter_result: KalmanFilterResult,
    matrices: ModelMatrices,
) -> SmootherResult:
    """Run a backward Rauch-Tung-Striebel smoothing pass."""
    filtered_states = np.asarray(filter_result.filtered_states, dtype=np.float64)
    filtered_covariances = np.asarray(filter_result.filtered_covariances, dtype=np.float64)
    predicted_states = np.asarray(filter_result.predicted_states, dtype=np.float64)
    predicted_covariances = np.asarray(filter_result.predicted_covariances, dtype=np.float64)

    if filtered_states.ndim != 2 or filtered_states.shape[0] == 0:
        state_dimension = matrices.state_dimension
        return SmootherResult(
            smoothed_states=np.empty((0, state_dimension), dtype=np.float64),
            smoothed_covariances=np.empty((0, state_dimension, state_dimension), dtype=np.float64),
            log_likelihood=float(filter_result.log_likelihood),
        )

    transition = np.asarray(matrices.transition, dtype=np.float64)
    time_count, state_count = filtered_states.shape
    smoothed_states = filtered_states.copy()
    smoothed_covariances = filtered_covariances.copy()

    for time_index in range(time_count - 2, -1, -1):
        predicted_covariance_next = predicted_covariances[time_index + 1]
        chol_factor, lower = cho_factor(predicted_covariance_next, lower=True, check_finite=False)

        smoother_gain = cho_solve(
            (chol_factor, lower),
            (filtered_covariances[time_index] @ transition.T).T,
            check_finite=False,
        ).T

        state_residual = smoothed_states[time_index + 1] - predicted_states[time_index + 1]
        smoothed_states[time_index] = (
            filtered_states[time_index] + smoother_gain @ state_residual
        )

        covariance_residual = (
            smoothed_covariances[time_index + 1] - predicted_covariance_next
        )
        smoothed_covariances[time_index] = _symmetrize(
            filtered_covariances[time_index]
            + smoother_gain @ covariance_residual @ smoother_gain.T
        )

    return SmootherResult(
        smoothed_states=smoothed_states,
        smoothed_covariances=smoothed_covariances,
        log_likelihood=float(filter_result.log_likelihood),
    )


def _symmetrize(matrix: Matrix) -> Matrix:
    """Average a matrix with its transpose for numerical stability."""
    return 0.5 * (matrix + matrix.T)
