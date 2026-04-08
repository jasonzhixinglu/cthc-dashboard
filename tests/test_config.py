"""Tests for model configuration validation."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.cthc.config import build_config, load_config


class ConfigTests(unittest.TestCase):
    """Validate config shape checking."""

    def test_build_config_accepts_consistent_dimensions(self) -> None:
        config = build_config(
            state_names=("trend", "gap"),
            initial_mean=(0.0, 0.0),
            initial_covariance=((1.0, 0.0), (0.0, 1.0)),
            measurement_names=("inflation",),
            transition_matrix=((1.0, 0.2), (0.0, 0.9)),
            design_matrix=((1.0, 0.0),),
            process_covariance=((0.1, 0.0), (0.0, 0.2)),
            measurement_covariance=((0.3,),),
        )

        self.assertEqual(config.state_dimension, 2)
        self.assertEqual(config.measurement_dimension, 1)

    def test_build_config_rejects_bad_design_shape(self) -> None:
        with self.assertRaises(ValueError):
            build_config(
                state_names=("trend", "gap"),
                initial_mean=(0.0, 0.0),
                initial_covariance=((1.0, 0.0), (0.0, 1.0)),
                measurement_names=("inflation",),
                transition_matrix=((1.0, 0.2), (0.0, 0.9)),
                design_matrix=((1.0,),),
                process_covariance=((0.1, 0.0), (0.0, 0.2)),
                measurement_covariance=((0.3,),),
            )

    def test_load_config_reads_baseline_yaml(self) -> None:
        config = load_config(Path("configs/baseline.yaml"))

        self.assertEqual(
            config.measurement.names,
            (
                "imports",
                "electricity",
                "industrial_va",
                "retail_sales",
                "fixed_asset_investment",
            ),
        )
        self.assertEqual(
            config.state.names,
            ("trend_level", "trend_slope", "cycle", "cycle_aux"),
        )
        self.assertAlmostEqual(config.trend.g0, 6.0)
        self.assertAlmostEqual(config.cycle.rho_c, 0.963)
        self.assertAlmostEqual(config.design_matrix[0][2], 2.560)
        self.assertAlmostEqual(config.measurement_covariance[0][0], 0.872**2)


if __name__ == "__main__":
    unittest.main()
