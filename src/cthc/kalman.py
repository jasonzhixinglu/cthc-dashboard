"""Linear Gaussian Kalman filter for the fixed-parameter CTHC model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import cho_factor, cho_solve

from .model_matrices import ModelMatrices

Vector = NDArray[np.float64]
Matrix = NDArray[np.float64]


@dataclass(frozen=True)
class KalmanFilterResult:
    """Aggregated Kalman filter output.

    Array dimensions:
    - ``predicted_states``: ``(T, n_state)``
    - ``predicted_covariances``: ``(T, n_state, n_state)``
    - ``filtered_states``: ``(T, n_state)``
    - ``filtered_covariances``: ``(T, n_state, n_state)``
    - ``log_likelihood``: scalar
    """

    predicted_states: Matrix
    predicted_covariances: NDArray[np.float64]
    filtered_states: Matrix
    filtered_covariances: NDArray[np.float64]
    log_likelihood: float


def run_kalman_filter(
    observations: Sequence[Sequence[float | None]] | NDArray[np.float64],
    matrices: ModelMatrices,
) -> KalmanFilterResult:
    """Run a linear Gaussian Kalman filter with NaN-based masking."""
    observation_array = np.asarray(observations, dtype=np.float64)
    if observation_array.ndim != 2:
        raise ValueError("observations must have shape (T, n_measurement).")
    if observation_array.shape[1] != matrices.measurement_dimension:
        raise ValueError("Observation width must match the measurement dimension.")

    transition = np.asarray(matrices.transition, dtype=np.float64)
    drift = np.asarray(matrices.drift, dtype=np.float64)
    measurement = np.asarray(matrices.measurement, dtype=np.float64)
    process_covariance = np.asarray(matrices.process_covariance, dtype=np.float64)
    measurement_covariance = np.asarray(matrices.measurement_covariance, dtype=np.float64)

    state_count = matrices.state_dimension
    time_count = observation_array.shape[0]

    predicted_states = np.zeros((time_count, state_count), dtype=np.float64)
    predicted_covariances = np.zeros((time_count, state_count, state_count), dtype=np.float64)
    filtered_states = np.zeros((time_count, state_count), dtype=np.float64)
    filtered_covariances = np.zeros((time_count, state_count, state_count), dtype=np.float64)

    filtered_state_prev = np.asarray(matrices.initial_mean, dtype=np.float64).copy()
    filtered_covariance_prev = np.asarray(matrices.initial_covariance, dtype=np.float64).copy()
    log_likelihood = 0.0

    for time_index in range(time_count):
        predicted_state = transition @ filtered_state_prev + drift
        predicted_covariance = _symmetrize(
            transition @ filtered_covariance_prev @ transition.T + process_covariance
        )

        predicted_states[time_index] = predicted_state
        predicted_covariances[time_index] = predicted_covariance

        observed_mask = ~np.isnan(observation_array[time_index])
        if not np.any(observed_mask):
            filtered_state = predicted_state
            filtered_covariance = predicted_covariance
        else:
            filtered_state, filtered_covariance, step_log_likelihood = _update_step(
                predicted_state=predicted_state,
                predicted_covariance=predicted_covariance,
                observation=observation_array[time_index, observed_mask],
                measurement=measurement[observed_mask],
                measurement_covariance=measurement_covariance[np.ix_(observed_mask, observed_mask)],
            )
            log_likelihood += step_log_likelihood

        filtered_states[time_index] = filtered_state
        filtered_covariances[time_index] = filtered_covariance
        filtered_state_prev = filtered_state
        filtered_covariance_prev = filtered_covariance

    return KalmanFilterResult(
        predicted_states=predicted_states,
        predicted_covariances=predicted_covariances,
        filtered_states=filtered_states,
        filtered_covariances=filtered_covariances,
        log_likelihood=float(log_likelihood),
    )


def _update_step(
    *,
    predicted_state: Vector,
    predicted_covariance: Matrix,
    observation: Vector,
    measurement: Matrix,
    measurement_covariance: Matrix,
) -> tuple[Vector, Matrix, float]:
    """Update one Kalman filter step using a Cholesky solve."""
    innovation = observation - measurement @ predicted_state
    innovation_covariance = _symmetrize(
        measurement @ predicted_covariance @ measurement.T + measurement_covariance
    )
    chol_factor, lower = cho_factor(innovation_covariance, lower=True, check_finite=False)

    cross_covariance = predicted_covariance @ measurement.T
    kalman_gain = cho_solve(
        (chol_factor, lower),
        cross_covariance.T,
        check_finite=False,
    ).T

    filtered_state = predicted_state + kalman_gain @ innovation

    identity = np.eye(predicted_covariance.shape[0], dtype=np.float64)
    residual_projection = identity - kalman_gain @ measurement
    filtered_covariance = _symmetrize(
        residual_projection @ predicted_covariance @ residual_projection.T
        + kalman_gain @ measurement_covariance @ kalman_gain.T
    )

    solved_innovation = cho_solve(
        (chol_factor, lower),
        innovation,
        check_finite=False,
    )
    log_determinant = 2.0 * np.sum(np.log(np.diag(chol_factor)))
    dimension = observation.shape[0]
    log_likelihood = -0.5 * (
        dimension * np.log(2.0 * np.pi)
        + log_determinant
        + innovation.T @ solved_innovation
    )
    return filtered_state, filtered_covariance, float(log_likelihood)


def _symmetrize(matrix: Matrix) -> Matrix:
    """Average a matrix with its transpose for numerical stability."""
    return 0.5 * (matrix + matrix.T)
