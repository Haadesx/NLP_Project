# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026  Philipp Emanuel Weidmann <pew@worldwidemann.com> + contributors

import torch
import torch.linalg as LA
from torch import Tensor

from .config import DirectionMethod


def normalize_rows(tensor: Tensor) -> Tensor:
    norms = LA.vector_norm(tensor, dim=1, keepdim=True)
    return tensor / torch.clamp(norms, min=1e-12)


def compute_direction_candidates(
    good_residuals: Tensor,
    bad_residuals: Tensor,
    variance_floor: float,
) -> dict[DirectionMethod, Tensor]:
    good_means = good_residuals.mean(dim=0)
    bad_means = bad_residuals.mean(dim=0)

    mean_directions = normalize_rows(bad_means - good_means)

    good_medians = good_residuals.median(dim=0).values
    bad_medians = bad_residuals.median(dim=0).values
    median_directions = normalize_rows(bad_medians - good_medians)

    good_var = good_residuals.var(dim=0, correction=0)
    bad_var = bad_residuals.var(dim=0, correction=0)
    pooled_var = 0.5 * (good_var + bad_var)
    variance_scaled_delta = (bad_means - good_means) / torch.sqrt(
        pooled_var + variance_floor
    )
    variance_directions = normalize_rows(variance_scaled_delta)

    return {
        DirectionMethod.MEAN: mean_directions,
        DirectionMethod.MEDIAN: median_directions,
        DirectionMethod.VARIANCE: variance_directions,
    }


def blend_directions(first: Tensor, second: Tensor, blend: float) -> Tensor:
    return normalize_rows(first.lerp(second, blend))


def orthogonalize_directions(
    directions: Tensor,
    reference_vectors: Tensor,
) -> Tensor:
    reference_directions = normalize_rows(reference_vectors)
    projection = torch.sum(directions * reference_directions, dim=1, keepdim=True)
    return normalize_rows(directions - projection * reference_directions)


def compute_benign_subspace_basis(
    good_residuals: Tensor,
    rank: int,
) -> Tensor | None:
    if rank <= 0:
        return None

    _, n_layers, hidden_size = good_residuals.shape
    max_rank = min(rank, good_residuals.shape[0] - 1, hidden_size)
    if max_rank <= 0:
        return None

    centered_residuals = good_residuals - good_residuals.mean(dim=0, keepdim=True)
    basis_vectors: list[Tensor] = []
    for layer_index in range(n_layers):
        layer_residuals = centered_residuals[:, layer_index, :]
        if torch.count_nonzero(layer_residuals).item() == 0:
            basis_vectors.append(
                torch.empty(
                    0,
                    hidden_size,
                    dtype=good_residuals.dtype,
                    device=good_residuals.device,
                )
            )
            continue

        _, _, right_singular_vectors = torch.pca_lowrank(
            layer_residuals,
            q=max_rank,
            center=False,
        )
        basis_vectors.append(right_singular_vectors.transpose(0, 1))

    return torch.stack(basis_vectors, dim=0)


def project_directions_out_of_subspace(
    directions: Tensor,
    subspace_basis: Tensor | None,
    dampening: float = 1.0,
) -> Tensor:
    if subspace_basis is None or subspace_basis.shape[1] == 0 or dampening <= 0.0:
        return directions

    normalized_basis = normalize_rows(subspace_basis.reshape(-1, subspace_basis.shape[-1]))
    normalized_basis = normalized_basis.reshape(subspace_basis.shape)
    projections = torch.einsum(
        "lh,lkh->lk",
        directions,
        normalized_basis,
    )
    projected = directions - dampening * torch.einsum(
        "lk,lkh->lh",
        projections,
        normalized_basis,
    )
    return normalize_rows(projected)
