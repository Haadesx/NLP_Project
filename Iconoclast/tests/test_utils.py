import random
import sys
import types
import unittest
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

questionary = types.ModuleType("questionary")
questionary.Choice = type("Choice", (), {})
questionary.Style = lambda *args, **kwargs: None
questionary.select = lambda *args, **kwargs: None
questionary.text = lambda *args, **kwargs: None
questionary.path = lambda *args, **kwargs: None
questionary.password = lambda *args, **kwargs: None
sys.modules.setdefault("questionary", questionary)

optuna = types.ModuleType("optuna")
optuna.Trial = type("Trial", (), {})
sys.modules.setdefault("optuna", optuna)

from iconoclast.utils import set_random_seed


class UtilsTests(unittest.TestCase):
    def test_set_random_seed_is_reproducible(self):
        set_random_seed(1234)
        first = (
            random.random(),
            np.random.rand(),
            torch.rand(1).item(),
        )

        set_random_seed(1234)
        second = (
            random.random(),
            np.random.rand(),
            torch.rand(1).item(),
        )

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
