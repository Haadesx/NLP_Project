import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from iconoclast.direction import (
    compute_benign_subspace_basis,
    project_directions_out_of_subspace,
)


class DirectionTests(unittest.TestCase):
    def test_benign_subspace_projection_removes_principal_good_direction(self):
        good_residuals = torch.tensor(
            [
                [[3.0, 0.0, 0.0]],
                [[1.0, 0.0, 0.0]],
                [[-1.0, 0.0, 0.0]],
                [[-3.0, 0.0, 0.0]],
            ]
        )
        basis = compute_benign_subspace_basis(good_residuals, rank=1)
        directions = torch.tensor([[1.0, 1.0, 0.0]])

        projected = project_directions_out_of_subspace(directions, basis)

        self.assertAlmostEqual(projected[0, 0].item(), 0.0, places=5)
        self.assertAlmostEqual(projected[0, 1].item(), 1.0, places=5)
        self.assertAlmostEqual(projected[0, 2].item(), 0.0, places=5)

    def test_zero_rank_benign_subspace_is_disabled(self):
        good_residuals = torch.tensor(
            [
                [[1.0, 0.0]],
                [[-1.0, 0.0]],
            ]
        )
        basis = compute_benign_subspace_basis(good_residuals, rank=0)
        directions = torch.tensor([[0.6, 0.8]])

        projected = project_directions_out_of_subspace(directions, basis)

        self.assertTrue(torch.equal(projected, directions))


if __name__ == "__main__":
    unittest.main()
