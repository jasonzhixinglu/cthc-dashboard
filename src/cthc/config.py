"""Configuration models and YAML loading for the fixed-parameter CTHC model."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

DEFAULT_CONFIG_PATH = Path("configs/baseline.yaml")

LOADINGS_ORDER = (
    "imports",
    "electricity",
    "industrial_va",
    "retail_sales",
    "fixed_asset_investment",
)


@dataclass(frozen=True)
class StateConfig:
    """Configuration for the latent state vector."""

    names: tuple[str, ...]
    initial_mean: tuple[float, ...]
    initial_covariance: tuple[tuple[float, ...], ...]

    def validate(self) -> None:
        """Validate state dimensions and covariance structure."""
        dimension = len(self.names)
        if dimension == 0:
            raise ValueError("StateConfig.names must not be empty.")
        if len(self.initial_mean) != dimension:
            raise ValueError("StateConfig.initial_mean must match state dimension.")
        _validate_square_matrix(
            self.initial_covariance,
            dimension,
            "StateConfig.initial_covariance",
        )


@dataclass(frozen=True)
class TrendConfig:
    """Trend parameters from the fixed-parameter baseline."""

    g0: float
    d: float
    sigma_u: float

    def validate(self) -> None:
        """Validate trend parameters."""
        if self.sigma_u < 0.0:
            raise ValueError("TrendConfig.sigma_u must be non-negative.")


@dataclass(frozen=True)
class CycleConfig:
    """Cycle parameters from the fixed-parameter baseline."""

    rho_c: float
    lambda_c: float
    sigma_omega: float

    def validate(self) -> None:
        """Validate cycle parameters."""
        if self.sigma_omega < 0.0:
            raise ValueError("CycleConfig.sigma_omega must be non-negative.")


@dataclass(frozen=True)
class MeasurementConfig:
    """Measurement-noise parameters from the fixed-parameter baseline."""

    names: tuple[str, ...]
    error_std: tuple[float, ...]
    sigma_eps_star: float
    sigma_tau: float
    sigma_psi: float

    def validate(self) -> None:
        """Validate measurement noise scales."""
        if not self.names:
            raise ValueError("MeasurementConfig.names must not be empty.")
        if len(self.error_std) != len(self.names):
            raise ValueError("MeasurementConfig.error_std must match measurement names.")
        for value in self.error_std:
            if value < 0.0:
                raise ValueError("MeasurementConfig.error_std must be non-negative.")
        if self.sigma_eps_star < 0.0:
            raise ValueError("MeasurementConfig.sigma_eps_star must be non-negative.")
        if self.sigma_tau < 0.0:
            raise ValueError("MeasurementConfig.sigma_tau must be non-negative.")
        if self.sigma_psi < 0.0:
            raise ValueError("MeasurementConfig.sigma_psi must be non-negative.")


@dataclass(frozen=True)
class LoadingsConfig:
    """Factor loadings for the observed monthly indicators."""

    imports: float
    electricity: float
    industrial_va: float
    retail_sales: float
    fixed_asset_investment: float

    def validate(self) -> None:
        """Validate that all required loadings are numeric."""
        for field_name in LOADINGS_ORDER:
            value = getattr(self, field_name)
            if not isinstance(value, float):
                raise ValueError(f"LoadingsConfig.{field_name} must be numeric.")

    def as_mapping(self) -> Mapping[str, float]:
        """Return loadings in baseline order."""
        return {field_name: getattr(self, field_name) for field_name in LOADINGS_ORDER}


@dataclass(frozen=True)
class CTHCConfig:
    """Full fixed-parameter configuration for a linear Gaussian model."""

    trend: TrendConfig
    cycle: CycleConfig
    measurement: MeasurementConfig
    loadings: LoadingsConfig
    state: StateConfig
    transition_matrix: tuple[tuple[float, ...], ...]
    design_matrix: tuple[tuple[float, ...], ...]
    process_covariance: tuple[tuple[float, ...], ...]
    measurement_covariance: tuple[tuple[float, ...], ...]
    control_matrix: tuple[tuple[float, ...], ...] = ()
    control_vector: tuple[float, ...] = ()

    @property
    def state_dimension(self) -> int:
        """Return the number of latent states."""
        return len(self.state.names)

    @property
    def measurement_dimension(self) -> int:
        """Return the number of observables."""
        return len(self.measurement.names)

    def validate(self) -> None:
        """Validate all configuration dimensions."""
        self.trend.validate()
        self.cycle.validate()
        self.measurement.validate()
        self.loadings.validate()
        self.state.validate()

        _validate_square_matrix(
            self.transition_matrix,
            self.state_dimension,
            "CTHCConfig.transition_matrix",
        )
        _validate_matrix(
            self.design_matrix,
            self.measurement_dimension,
            self.state_dimension,
            "CTHCConfig.design_matrix",
        )
        _validate_square_matrix(
            self.process_covariance,
            self.state_dimension,
            "CTHCConfig.process_covariance",
        )
        _validate_square_matrix(
            self.measurement_covariance,
            self.measurement_dimension,
            "CTHCConfig.measurement_covariance",
        )

        has_control_matrix = bool(self.control_matrix)
        has_control_vector = bool(self.control_vector)
        if has_control_matrix != has_control_vector:
            raise ValueError(
                "CTHCConfig.control_matrix and CTHCConfig.control_vector must "
                "either both be provided or both be empty."
            )
        if has_control_matrix:
            _validate_matrix(
                self.control_matrix,
                self.state_dimension,
                len(self.control_vector),
                "CTHCConfig.control_matrix",
            )


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> CTHCConfig:
    """Load a fixed-parameter CTHC configuration from YAML."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw_config = yaml.safe_load(handle)

    if not isinstance(raw_config, dict):
        raise ValueError(f"Config file '{config_path}' must contain a YAML mapping.")

    return build_config_from_mapping(raw_config)


def build_config_from_mapping(raw_config: Mapping[str, Any]) -> CTHCConfig:
    """Build a validated config from a parsed mapping."""
    trend_section = _require_mapping(raw_config, "trend")
    cycle_section = _require_mapping(raw_config, "cycle")
    measurement_section = _require_mapping(raw_config, "measurement")
    loadings_section = _require_mapping(raw_config, "loadings")

    trend = TrendConfig(
        g0=_require_float(trend_section, "g0", "trend"),
        d=_require_float(trend_section, "d", "trend"),
        sigma_u=_require_float(trend_section, "sigma_u", "trend"),
    )
    cycle = CycleConfig(
        rho_c=_require_float(cycle_section, "rho_c", "cycle"),
        lambda_c=_require_float(cycle_section, "lambda_c", "cycle"),
        sigma_omega=_require_float(cycle_section, "sigma_omega", "cycle"),
    )
    measurement = MeasurementConfig(
        names=LOADINGS_ORDER,
        error_std=(
            _require_float(
                measurement_section,
                "sigma_eps_star",
                "measurement",
            ),
            _require_float(measurement_section, "sigma_tau", "measurement"),
            _require_float(measurement_section, "sigma_psi", "measurement"),
            _require_float(measurement_section, "sigma_psi", "measurement"),
            _require_float(measurement_section, "sigma_psi", "measurement"),
        ),
        sigma_eps_star=_require_float(
            measurement_section,
            "sigma_eps_star",
            "measurement",
        ),
        sigma_tau=_require_float(measurement_section, "sigma_tau", "measurement"),
        sigma_psi=_require_float(measurement_section, "sigma_psi", "measurement"),
    )
    loadings = LoadingsConfig(
        imports=_require_float(loadings_section, "imports", "loadings"),
        electricity=_require_float(loadings_section, "electricity", "loadings"),
        industrial_va=_require_float(loadings_section, "industrial_va", "loadings"),
        retail_sales=_require_float(loadings_section, "retail_sales", "loadings"),
        fixed_asset_investment=_require_float(
            loadings_section,
            "fixed_asset_investment",
            "loadings",
        ),
    )

    config = _assemble_structured_config(
        trend=trend,
        cycle=cycle,
        measurement=measurement,
        loadings=loadings,
    )
    config.validate()
    return config


def build_config(
    *,
    state_names: Sequence[str],
    initial_mean: Sequence[float],
    initial_covariance: Sequence[Sequence[float]],
    measurement_names: Sequence[str],
    transition_matrix: Sequence[Sequence[float]],
    design_matrix: Sequence[Sequence[float]],
    process_covariance: Sequence[Sequence[float]],
    measurement_covariance: Sequence[Sequence[float]],
    control_matrix: Sequence[Sequence[float]] | None = None,
    control_vector: Sequence[float] | None = None,
) -> CTHCConfig:
    """Build and validate an immutable matrix-based config."""
    normalized_state_names = tuple(state_names)
    normalized_measurement_names = tuple(measurement_names)
    normalized_initial_mean = tuple(float(value) for value in initial_mean)
    normalized_initial_covariance = _to_matrix(initial_covariance)
    normalized_transition_matrix = _to_matrix(transition_matrix)
    normalized_design_matrix = _to_matrix(design_matrix)
    normalized_process_covariance = _to_matrix(process_covariance)
    normalized_measurement_covariance = _to_matrix(measurement_covariance)
    normalized_control_matrix = _to_matrix(control_matrix or ())
    normalized_control_vector = tuple(float(value) for value in (control_vector or ()))

    state = StateConfig(
        names=normalized_state_names,
        initial_mean=normalized_initial_mean,
        initial_covariance=normalized_initial_covariance,
    )
    measurement = MeasurementConfig(
        names=normalized_measurement_names,
        error_std=tuple(
            float(normalized_measurement_covariance[index][index]) ** 0.5
            for index in range(len(normalized_measurement_names))
        ),
        sigma_eps_star=float(normalized_measurement_covariance[0][0]) ** 0.5,
        sigma_tau=float(normalized_measurement_covariance[0][0]) ** 0.5,
        sigma_psi=float(normalized_measurement_covariance[-1][-1]) ** 0.5,
    )
    state.validate()
    _validate_square_matrix(
        normalized_transition_matrix,
        len(normalized_state_names),
        "CTHCConfig.transition_matrix",
    )
    _validate_matrix(
        normalized_design_matrix,
        len(normalized_measurement_names),
        len(normalized_state_names),
        "CTHCConfig.design_matrix",
    )
    _validate_square_matrix(
        normalized_process_covariance,
        len(normalized_state_names),
        "CTHCConfig.process_covariance",
    )
    _validate_square_matrix(
        normalized_measurement_covariance,
        len(normalized_measurement_names),
        "CTHCConfig.measurement_covariance",
    )

    trend = TrendConfig(
        g0=float(normalized_initial_mean[0]) if normalized_initial_mean else 0.0,
        d=float(normalized_initial_mean[1]) if len(normalized_initial_mean) > 1 else 0.0,
        sigma_u=float(normalized_process_covariance[0][0]) ** 0.5,
    )
    cycle = CycleConfig(
        rho_c=float(normalized_transition_matrix[-1][-1]),
        lambda_c=0.0,
        sigma_omega=float(normalized_process_covariance[-1][-1]) ** 0.5,
    )
    loadings = LoadingsConfig(
        imports=_safe_design_value(normalized_design_matrix, 0, 0),
        electricity=_safe_design_value(normalized_design_matrix, 1, 0),
        industrial_va=_safe_design_value(normalized_design_matrix, 2, 0),
        retail_sales=_safe_design_value(normalized_design_matrix, 3, 0),
        fixed_asset_investment=_safe_design_value(normalized_design_matrix, 4, 0),
    )

    config = CTHCConfig(
        trend=trend,
        cycle=cycle,
        measurement=measurement,
        loadings=loadings,
        state=state,
        transition_matrix=normalized_transition_matrix,
        design_matrix=normalized_design_matrix,
        process_covariance=normalized_process_covariance,
        measurement_covariance=normalized_measurement_covariance,
        control_matrix=normalized_control_matrix,
        control_vector=normalized_control_vector,
    )
    config.validate()
    return config


def _assemble_structured_config(
    *,
    trend: TrendConfig,
    cycle: CycleConfig,
    measurement: MeasurementConfig,
    loadings: LoadingsConfig,
) -> CTHCConfig:
    """Assemble a working state-space representation from baseline parameters."""
    cycle_cos = cycle.rho_c * cos(cycle.lambda_c)
    cycle_sin = cycle.rho_c * sin(cycle.lambda_c)

    state = StateConfig(
        names=("trend_level", "trend_slope", "cycle", "cycle_aux"),
        initial_mean=(trend.g0, trend.d, 0.0, 0.0),
        initial_covariance=(
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 0.25, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
    )

    transition_matrix = (
        (1.0, 1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, cycle_cos, cycle_sin),
        (0.0, 0.0, -cycle_sin, cycle_cos),
    )
    design_matrix = (
        (1.0, 0.0, loadings.imports, 0.0),
        (0.0, 0.0, loadings.electricity, 0.0),
        (0.0, 0.0, loadings.industrial_va, 0.0),
        (0.0, 0.0, loadings.retail_sales, 0.0),
        (0.0, 0.0, loadings.fixed_asset_investment, 0.0),
    )
    process_covariance = (
        (trend.sigma_u**2, 0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0, 0.0),
        (0.0, 0.0, cycle.sigma_omega**2, 0.0),
        (0.0, 0.0, 0.0, cycle.sigma_omega**2),
    )
    error_std = measurement.error_std
    measurement_covariance = tuple(
        tuple(error_std[row] ** 2 if row == column else 0.0 for column in range(len(error_std)))
        for row in range(len(error_std))
    )

    return CTHCConfig(
        trend=trend,
        cycle=cycle,
        measurement=measurement,
        loadings=loadings,
        state=state,
        transition_matrix=transition_matrix,
        design_matrix=design_matrix,
        process_covariance=process_covariance,
        measurement_covariance=measurement_covariance,
    )


def _safe_design_value(
    matrix: Sequence[Sequence[float]],
    row_index: int,
    column_index: int,
) -> float:
    """Read a design-matrix value when present, otherwise return zero."""
    if row_index >= len(matrix):
        return 0.0
    row = matrix[row_index]
    if column_index >= len(row):
        return 0.0
    return float(row[column_index])


def _to_matrix(values: Sequence[Sequence[float]]) -> tuple[tuple[float, ...], ...]:
    """Convert a nested numeric sequence to an immutable matrix."""
    return tuple(tuple(float(value) for value in row) for row in values)


def _require_mapping(
    mapping: Mapping[str, Any],
    key: str,
    parent: str = "config",
) -> Mapping[str, Any]:
    """Require a nested mapping value."""
    value = mapping.get(key)
    if value is None:
        raise ValueError(f"Missing required section '{parent}.{key}'.")
    if not isinstance(value, dict):
        raise ValueError(f"Section '{parent}.{key}' must be a mapping.")
    return value


def _require_float(mapping: Mapping[str, Any], key: str, parent: str) -> float:
    """Require a numeric field."""
    if key not in mapping:
        raise ValueError(f"Missing required field '{parent}.{key}'.")
    value = mapping[key]
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Field '{parent}.{key}' must be numeric.") from error


def _validate_square_matrix(
    matrix: Sequence[Sequence[float]],
    expected_size: int,
    label: str,
) -> None:
    """Validate a square matrix shape."""
    _validate_matrix(matrix, expected_size, expected_size, label)


def _validate_matrix(
    matrix: Sequence[Sequence[float]],
    expected_rows: int,
    expected_columns: int,
    label: str,
) -> None:
    """Validate a general matrix shape."""
    if len(matrix) != expected_rows:
        raise ValueError(f"{label} must have {expected_rows} rows.")
    for row in matrix:
        if len(row) != expected_columns:
            raise ValueError(f"{label} must have {expected_columns} columns.")
