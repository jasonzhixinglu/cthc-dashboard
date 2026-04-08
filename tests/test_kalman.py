"""Tests for the Kalman filter implementation."""

from __future__ import annotations

import unittest
import numpy as np

from src.cthc.config import build_config
from src.cthc.model_matrices import build_model_matrices
from src.cthc.kalman import run_kalman_filter
from src.cthc.smoother import run_rts_smoother


class KalmanTests(unittest.TestCase):
    """Validate core filter behavior."""

    def test_filter_and_smoother_handle_synthetic_missing_data(self) -> None:
        config = build_config(
            state_names=("level",),
            initial_mean=(0.0,),
            initial_covariance=((1.0,),),
            measurement_names=("headline",),
            transition_matrix=((1.0,),),
            design_matrix=((1.0,),),
            process_covariance=((0.1,),),
            measurement_covariance=((0.2,),),
        )
        matrices = build_model_matrices(config)
        observations = np.array([[1.0], [np.nan], [1.0], [1.0]], dtype=np.float64)

        filter_result = run_kalman_filter(observations, matrices)
        smoother_result = run_rts_smoother(filter_result, matrices)

        self.assertEqual(filter_result.predicted_states.shape, (4, 1))
        self.assertEqual(filter_result.filtered_states.shape, (4, 1))
        self.assertEqual(smoother_result.smoothed_states.shape, (4, 1))
        self.assertAlmostEqual(
            filter_result.predicted_states[1, 0],
            filter_result.filtered_states[0, 0],
        )
        self.assertAlmostEqual(
            filter_result.filtered_states[1, 0],
            filter_result.predicted_states[1, 0],
        )
        self.assertGreater(filter_result.filtered_states[-1, 0], 0.8)
        self.assertLess(filter_result.filtered_states[-1, 0], 1.01)
        self.assertTrue(np.isfinite(filter_result.log_likelihood))
        self.assertAlmostEqual(
            smoother_result.log_likelihood,
            filter_result.log_likelihood,
        )


if __name__ == "__main__":
    unittest.main()
