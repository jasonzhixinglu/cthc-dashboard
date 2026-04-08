"""Tests for model matrix assembly and helpers."""

from __future__ import annotations

import unittest
import numpy as np

from src.cthc.config import load_config
from src.cthc.model_matrices import build_model_matrices


class ModelMatricesTests(unittest.TestCase):
    """Validate model matrix construction."""

    def test_build_model_matrices_returns_expected_shapes(self) -> None:
        config = load_config()
        matrices = build_model_matrices(config)

        self.assertEqual(matrices.state_names[:4], ("mu_t", "g_t", "c_t", "c_star_t"))
        self.assertEqual(matrices.state_dimension, 9)
        self.assertEqual(matrices.measurement_dimension, 6)
        self.assertEqual(matrices.transition.shape, (9, 9))
        self.assertEqual(matrices.drift.shape, (9,))
        self.assertEqual(matrices.process_covariance.shape, (9, 9))
        self.assertEqual(matrices.measurement.shape, (6, 9))
        self.assertEqual(matrices.measurement_covariance.shape, (6, 6))

    def test_sector_measurement_rows_include_mu_cycle_and_sector_state(self) -> None:
        config = load_config()
        matrices = build_model_matrices(config)

        imports_row = matrices.measurement[1]
        electricity_row = matrices.measurement[2]

        self.assertTrue(np.isclose(matrices.measurement[0, 0], 1.0))
        self.assertTrue(np.isclose(imports_row[0], 1.0))
        self.assertTrue(np.isclose(imports_row[2], 2.560))
        self.assertTrue(np.isclose(imports_row[4], 1.0))
        self.assertTrue(np.isclose(electricity_row[5], 1.0))
        self.assertTrue(np.isclose(matrices.drift[1], -0.025))

    def test_builder_scales_to_arbitrary_sector_count(self) -> None:
        config = load_config()
        config = type(config)(
            trend=config.trend,
            cycle=config.cycle,
            measurement=type(config.measurement)(
                names=("imports", "electricity"),
                error_std=(
                    config.measurement.sigma_eps_star,
                    config.measurement.sigma_tau,
                ),
                sigma_eps_star=config.measurement.sigma_eps_star,
                sigma_tau=config.measurement.sigma_tau,
                sigma_psi=config.measurement.sigma_psi,
            ),
            loadings=config.loadings,
            state=config.state,
            transition_matrix=config.transition_matrix,
            design_matrix=config.design_matrix,
            process_covariance=config.process_covariance,
            measurement_covariance=config.measurement_covariance,
            control_matrix=config.control_matrix,
            control_vector=config.control_vector,
        )
        matrices = build_model_matrices(config)

        self.assertEqual(matrices.transition.shape, (6, 6))
        self.assertEqual(matrices.measurement.shape, (3, 6))
        self.assertEqual(matrices.measurement_covariance.shape, (3, 3))


if __name__ == "__main__":
    unittest.main()
