import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from iconoclast.config import WarmStartTrial


class ConfigTests(unittest.TestCase):
    def test_warm_start_trial_accepts_mixed_optuna_param_types(self):
        trial = WarmStartTrial.model_validate(
            {
                "description": "Strong per-layer variance anchor",
                "params": {
                    "direction_scope": "per layer",
                    "direction_method": "variance",
                    "direction_blend": 0.42,
                    "attn.o_proj.max_weight": 1.34,
                },
            }
        )

        self.assertEqual(trial.description, "Strong per-layer variance anchor")
        self.assertEqual(trial.params["direction_scope"], "per layer")
        self.assertEqual(trial.params["direction_method"], "variance")
        self.assertAlmostEqual(trial.params["direction_blend"], 0.42)
        self.assertAlmostEqual(trial.params["attn.o_proj.max_weight"], 1.34)


if __name__ == "__main__":
    unittest.main()
