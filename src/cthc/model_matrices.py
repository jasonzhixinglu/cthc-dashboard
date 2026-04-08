"""NumPy-based state-space matrices for the fixed-parameter CTHC model."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin
from typing import Sequence

import numpy as np
from numpy.typing import NDArray

from .config import CTHCConfig

Vector = NDArray[np.float64]
Matrix = NDArray[np.float64]


@dataclass(frozen=True)
class ModelMatrices:
    """Concrete model matrices for the fixed-parameter CTHC state-space model.

    Dimensions for ``n`` sectors:
    - ``transition``: ``(4 + n, 4 + n)``
    - ``drift``: ``(4 + n,)``
    - ``process_covariance``: ``(4 + n, 4 + n)``
    - ``measurement``: ``(1 + n, 4 + n)``
    - ``measurement_covariance``: ``(1 + n, 1 + n)``
    - ``initial_mean``: ``(4 + n,)``
    - ``initial_covariance``: ``(4 + n, 4 + n)``
    """

    state_names: tuple[str, ...]
    measurement_names: tuple[str, ...]
    transition: Matrix
    drift: Vector
    process_covariance: Matrix
    measurement: Matrix
    measurement_covariance: Matrix
    initial_mean: Vector
    initial_covariance: Matrix
    control_matrix: tuple[()] = ()
    control_vector: tuple[()] = ()

    @property
    def state_dimension(self) -> int:
        """Return the state dimension."""
        return int(self.transition.shape[0])

    @property
    def measurement_dimension(self) -> int:
        """Return the measurement dimension."""
        return int(self.measurement.shape[0])

    @property
    def design(self) -> Matrix:
        """Compatibility alias for the observation matrix."""
        return self.measurement


def build_model_matrices(config: CTHCConfig) -> ModelMatrices:
    """Build fixed-parameter CTHC matrices from structured configuration."""
    config.trend.validate()
    config.cycle.validate()
    config.measurement.validate()
    config.loadings.validate()

    if not _has_structured_sector_loadings(config):
        transition = np.asarray(config.transition_matrix, dtype=np.float64)
        measurement = np.asarray(config.design_matrix, dtype=np.float64)
        process_covariance = np.asarray(config.process_covariance, dtype=np.float64)
        measurement_covariance = np.asarray(config.measurement_covariance, dtype=np.float64)
        initial_mean = np.asarray(config.state.initial_mean, dtype=np.float64)
        initial_covariance = np.asarray(config.state.initial_covariance, dtype=np.float64)
        return ModelMatrices(
            state_names=tuple(config.state.names),
            measurement_names=tuple(config.measurement.names),
            transition=transition,
            drift=np.zeros(transition.shape[0], dtype=np.float64),
            process_covariance=process_covariance,
            measurement=measurement,
            measurement_covariance=measurement_covariance,
            initial_mean=initial_mean,
            initial_covariance=initial_covariance,
        )

    sector_names = tuple(config.measurement.names)
    sector_loadings = _extract_sector_loadings(config, sector_names)
    sector_count = len(sector_names)
    state_names = ("mu_t", "g_t", "c_t", "c_star_t") + tuple(
        f"theta_{sector_name}" for sector_name in sector_names
    )
    measurement_names = ("gdp",) + sector_names

    transition = np.eye(4 + sector_count, dtype=np.float64)
    transition[0, 1] = 1.0

    cycle_cos = config.cycle.rho_c * cos(config.cycle.lambda_c)
    cycle_sin = config.cycle.rho_c * sin(config.cycle.lambda_c)
    transition[2, 2] = cycle_cos
    transition[2, 3] = cycle_sin
    transition[3, 2] = -cycle_sin
    transition[3, 3] = cycle_cos

    drift = np.zeros(4 + sector_count, dtype=np.float64)
    drift[1] = float(config.trend.d)

    process_covariance = np.zeros((4 + sector_count, 4 + sector_count), dtype=np.float64)
    process_covariance[1, 1] = float(config.trend.sigma_u) ** 2
    process_covariance[2, 2] = float(config.cycle.sigma_omega) ** 2
    process_covariance[3, 3] = float(config.cycle.sigma_omega) ** 2
    for sector_index in range(sector_count):
        process_covariance[4 + sector_index, 4 + sector_index] = float(config.measurement.sigma_psi) ** 2

    measurement = np.zeros((1 + sector_count, 4 + sector_count), dtype=np.float64)
    measurement[0, 0] = 1.0
    for sector_index, loading in enumerate(sector_loadings):
        measurement_row = 1 + sector_index
        theta_column = 4 + sector_index
        measurement[measurement_row, 0] = 1.0
        measurement[measurement_row, 2] = float(loading)
        measurement[measurement_row, theta_column] = 1.0

    measurement_covariance = np.zeros((1 + sector_count, 1 + sector_count), dtype=np.float64)
    measurement_covariance[0, 0] = float(config.measurement.sigma_eps_star) ** 2
    for sector_index in range(sector_count):
        measurement_covariance[1 + sector_index, 1 + sector_index] = float(config.measurement.sigma_tau) ** 2

    initial_mean = np.zeros(4 + sector_count, dtype=np.float64)
    initial_mean[0] = float(config.trend.g0)
    initial_mean[1] = float(config.trend.d)

    initial_covariance = np.eye(4 + sector_count, dtype=np.float64)
    initial_covariance[0, 0] = 1.0
    initial_covariance[1, 1] = 0.25

    return ModelMatrices(
        state_names=state_names,
        measurement_names=measurement_names,
        transition=transition,
        drift=drift,
        process_covariance=process_covariance,
        measurement=measurement,
        measurement_covariance=measurement_covariance,
        initial_mean=initial_mean,
        initial_covariance=initial_covariance,
    )


def identity(size: int) -> Matrix:
    """Return a square identity matrix with shape ``(size, size)``."""
    return np.eye(size, dtype=np.float64)


def transpose(matrix: Sequence[Sequence[float]] | Matrix) -> Matrix:
    """Return the transpose of a matrix."""
    return np.asarray(matrix, dtype=np.float64).T.copy()


def matrix_add(left: Sequence[Sequence[float]] | Matrix, right: Sequence[Sequence[float]] | Matrix) -> Matrix:
    """Add two matrices of the same shape."""
    return np.asarray(left, dtype=np.float64) + np.asarray(right, dtype=np.float64)


def matrix_subtract(
    left: Sequence[Sequence[float]] | Matrix,
    right: Sequence[Sequence[float]] | Matrix,
) -> Matrix:
    """Subtract one matrix from another."""
    return np.asarray(left, dtype=np.float64) - np.asarray(right, dtype=np.float64)


def matrix_multiply(
    left: Sequence[Sequence[float]] | Matrix,
    right: Sequence[Sequence[float]] | Matrix,
) -> Matrix:
    """Multiply two matrices."""
    return np.asarray(left, dtype=np.float64) @ np.asarray(right, dtype=np.float64)


def matrix_vector_multiply(
    matrix: Sequence[Sequence[float]] | Matrix,
    vector: Sequence[float] | Vector,
) -> Vector:
    """Multiply a matrix by a vector."""
    return np.asarray(matrix, dtype=np.float64) @ np.asarray(vector, dtype=np.float64)


def vector_add(left: Sequence[float] | Vector, right: Sequence[float] | Vector) -> Vector:
    """Add two vectors."""
    return np.asarray(left, dtype=np.float64) + np.asarray(right, dtype=np.float64)


def vector_subtract(left: Sequence[float] | Vector, right: Sequence[float] | Vector) -> Vector:
    """Subtract one vector from another."""
    return np.asarray(left, dtype=np.float64) - np.asarray(right, dtype=np.float64)


def outer_product(left: Sequence[float] | Vector, right: Sequence[float] | Vector) -> Matrix:
    """Compute the outer product of two vectors."""
    return np.outer(
        np.asarray(left, dtype=np.float64),
        np.asarray(right, dtype=np.float64),
    )


def matrix_inverse(matrix: Sequence[Sequence[float]] | Matrix) -> Matrix:
    """Invert a square matrix."""
    return np.linalg.inv(np.asarray(matrix, dtype=np.float64))


def symmetrize(matrix: Sequence[Sequence[float]] | Matrix) -> Matrix:
    """Average a matrix with its transpose for numerical stability."""
    array = np.asarray(matrix, dtype=np.float64)
    return 0.5 * (array + array.T)


def _extract_sector_loadings(config: CTHCConfig, sector_names: Sequence[str]) -> tuple[float, ...]:
    """Read sector loadings from the structured config."""
    loadings: list[float] = []
    for sector_name in sector_names:
        if not hasattr(config.loadings, sector_name):
            raise ValueError(f"Missing loading for sector '{sector_name}'.")
        loadings.append(float(getattr(config.loadings, sector_name)))
    return tuple(loadings)


def _has_structured_sector_loadings(config: CTHCConfig) -> bool:
    """Return whether the config exposes named sector loadings for all measurements."""
    return all(hasattr(config.loadings, sector_name) for sector_name in config.measurement.names)
