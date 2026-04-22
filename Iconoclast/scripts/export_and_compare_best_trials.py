#!/usr/bin/env python3
import argparse
import importlib
import json
import os
import sys
from collections import defaultdict
from os.path import commonprefix
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iconoclast-checkpoint", required=True)
    parser.add_argument("--heretic-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--sample-count", type=int, default=5)
    return parser.parse_args()


def load_study(checkpoint_path: Path) -> tuple[str, dict[int, dict[str, Any]]]:
    settings_json = None
    trials: dict[int, dict[str, Any]] = defaultdict(dict)

    for line in checkpoint_path.read_text().splitlines():
        obj = json.loads(line)
        user_attr = obj.get("user_attr")
        if user_attr and "settings" in user_attr and settings_json is None:
            settings_json = user_attr["settings"]

        trial_id = obj.get("trial_id")
        if trial_id is not None and user_attr:
            trials[trial_id].update(user_attr)

    if settings_json is None:
        raise ValueError(f"Did not find settings in {checkpoint_path}")

    return settings_json, trials


def pick_best_trial(trials: dict[int, dict[str, Any]]) -> dict[str, Any]:
    best = None

    for trial_id, attrs in trials.items():
        if not {"refusals", "kl_divergence", "parameters"}.issubset(attrs):
            continue

        item = {
            "trial_id": trial_id,
            "index": attrs.get("index"),
            "refusals": attrs["refusals"],
            "overrefusals": attrs.get("overrefusals", 0),
            "kl_divergence": attrs["kl_divergence"],
            "direction_index": attrs["direction_index"],
            "direction_method": attrs["direction_method"],
            "direction_blend": attrs.get("direction_blend", 0.0),
            "component_direction_indices": attrs.get("component_direction_indices"),
            "component_direction_methods": attrs.get("component_direction_methods"),
            "component_direction_blends": attrs.get("component_direction_blends"),
            "parameters": attrs["parameters"],
        }

        key = (item["refusals"], item["overrefusals"], item["kl_divergence"])
        if best is None or key < (
            best["refusals"],
            best["overrefusals"],
            best["kl_divergence"],
        ):
            best = item

    if best is None:
        raise ValueError("No completed trials with metrics were found")

    return best


def load_stack(package: str) -> dict[str, Any]:
    return {
        "package": package,
        "config": importlib.import_module(f"{package}.config"),
        "direction": importlib.import_module(f"{package}.direction"),
        "model": importlib.import_module(f"{package}.model"),
        "utils": importlib.import_module(f"{package}.utils"),
    }


def normalize_refusal_text(text: str) -> str:
    text = text.lower().replace("*", "")
    text = text.replace("’", "'")
    return " ".join(text.split())


def is_refusal(response: str, refusal_markers: list[str]) -> bool:
    if not response.strip():
        return True

    normalized = normalize_refusal_text(response)
    return any(marker.lower() in normalized for marker in refusal_markers)


def determine_response_prefix(model: Any, good_prompts: list[Any], bad_prompts: list[Any]) -> None:
    prefix_check_prompts = good_prompts[:100] + bad_prompts[:100]
    responses = model.get_responses_batched(prefix_check_prompts)
    model.response_prefix = commonprefix(responses).rstrip(" ")

    recheck_prefix = False
    if model.response_prefix:
        recheck_prefix = True
        if model.response_prefix.startswith("<think>"):
            model.response_prefix = "<think></think>"
        elif model.response_prefix.startswith("<|channel|>analysis<|message|>"):
            model.response_prefix = (
                "<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>final<|message|>"
            )
        elif model.response_prefix.startswith("<thought>"):
            model.response_prefix = "<thought></thought>"
        elif model.response_prefix.startswith("[THINK]"):
            model.response_prefix = "[THINK][/THINK]"
        else:
            recheck_prefix = False

    if recheck_prefix:
        responses = model.get_responses_batched(prefix_check_prompts)
        additional_prefix = commonprefix(responses).rstrip(" ")
        if additional_prefix:
            model.response_prefix += additional_prefix


def prepare_runtime(stack: dict[str, Any], settings_json: str) -> dict[str, Any]:
    Settings = stack["config"].Settings
    DirectionMethod = stack["config"].DirectionMethod
    Model = stack["model"].Model
    load_prompts = stack["utils"].load_prompts
    set_random_seed = stack["utils"].set_random_seed
    empty_cache = stack["utils"].empty_cache
    compute_direction_candidates = stack["direction"].compute_direction_candidates
    orthogonalize_directions = stack["direction"].orthogonalize_directions
    blend_directions = stack["direction"].blend_directions

    settings = Settings.model_validate_json(settings_json)
    set_random_seed(settings.seed)
    model = Model(settings)

    good_prompts = load_prompts(settings, settings.good_prompts)
    bad_prompts = load_prompts(settings, settings.bad_prompts)
    good_eval_prompts = load_prompts(settings, settings.good_evaluation_prompts)
    bad_eval_prompts = load_prompts(settings, settings.bad_evaluation_prompts)

    determine_response_prefix(model, good_prompts, bad_prompts)

    good_residuals = model.get_residuals_batched(good_prompts)
    bad_residuals = model.get_residuals_batched(bad_prompts)
    good_means = good_residuals.mean(dim=0)
    direction_candidates = compute_direction_candidates(
        good_residuals,
        bad_residuals,
        settings.direction_variance_floor,
    )

    if settings.orthogonalize_direction:
        direction_candidates = {
            method: orthogonalize_directions(candidate, good_means)
            for method, candidate in direction_candidates.items()
        }

    del good_residuals, bad_residuals
    empty_cache()

    def get_trial_refusal_directions(trial_data: dict[str, Any]) -> Any:
        component_direction_methods = trial_data.get("component_direction_methods")
        if isinstance(component_direction_methods, dict):
            component_direction_blends = trial_data.get(
                "component_direction_blends",
                {},
            )
            return {
                component: blend_directions(
                    direction_candidates[DirectionMethod.MEAN],
                    direction_candidates[DirectionMethod.VARIANCE],
                    float(component_direction_blends.get(component, 0.0)),
                )
                if DirectionMethod(method) == DirectionMethod.HYBRID
                else direction_candidates[DirectionMethod(method)]
                for component, method in component_direction_methods.items()
            }

        direction_method = DirectionMethod(trial_data["direction_method"])
        direction_blend = float(trial_data.get("direction_blend", 0.0))
        if direction_method == DirectionMethod.HYBRID:
            return blend_directions(
                direction_candidates[DirectionMethod.MEAN],
                direction_candidates[DirectionMethod.VARIANCE],
                direction_blend,
            )
        return direction_candidates[direction_method]

    return {
        "settings": settings,
        "model": model,
        "good_eval_prompts": good_eval_prompts,
        "bad_eval_prompts": bad_eval_prompts,
        "get_trial_refusal_directions": get_trial_refusal_directions,
        "AbliterationParameters": stack["model"].AbliterationParameters,
        "empty_cache": empty_cache,
    }


def apply_trial(runtime: dict[str, Any], trial_data: dict[str, Any]) -> None:
    model = runtime["model"]
    AbliterationParameters = runtime["AbliterationParameters"]

    parameters = {
        name: AbliterationParameters(**values)
        for name, values in trial_data["parameters"].items()
    }

    model.reset_model()
    model.abliterate(
        runtime["get_trial_refusal_directions"](trial_data),
        trial_data.get("component_direction_indices", trial_data["direction_index"]),
        parameters,
    )


def export_merged_model(runtime: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    merged_model = runtime["model"].get_merged_model()
    merged_model.save_pretrained(output_dir)
    runtime["model"].tokenizer.save_pretrained(output_dir)
    del merged_model
    runtime["empty_cache"]()


def prompt_record(category: str, index: int, prompt: Any) -> dict[str, Any]:
    return {
        "category": category,
        "index": index,
        "system": prompt.system,
        "user": prompt.user,
    }


def main() -> None:
    args = parse_args()
    sys.argv = [sys.argv[0]]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    icon_settings_json, icon_trials = load_study(Path(args.iconoclast_checkpoint))
    her_settings_json, her_trials = load_study(Path(args.heretic_checkpoint))
    icon_best = pick_best_trial(icon_trials)
    her_best = pick_best_trial(her_trials)

    icon_stack = load_stack("iconoclast")
    her_stack = load_stack("heretic")

    icon_runtime = prepare_runtime(icon_stack, icon_settings_json)
    her_runtime = prepare_runtime(her_stack, her_settings_json)

    sample_count = args.sample_count
    sample_prompts = [
        prompt_record("harmful", i, prompt)
        for i, prompt in enumerate(icon_runtime["bad_eval_prompts"][:sample_count])
    ] + [
        prompt_record("harmless", i, prompt)
        for i, prompt in enumerate(icon_runtime["good_eval_prompts"][:sample_count])
    ]

    base_runtime = prepare_runtime(icon_stack, icon_settings_json)
    base_prompts = [
        icon_stack["utils"].Prompt(system=item["system"], user=item["user"])
        for item in sample_prompts
    ]
    base_responses = base_runtime["model"].get_responses_batched(
        base_prompts,
        skip_special_tokens=True,
    )

    apply_trial(icon_runtime, icon_best)
    export_merged_model(icon_runtime, output_dir / "iconoclast-best-merged")
    icon_responses = icon_runtime["model"].get_responses_batched(
        base_prompts,
        skip_special_tokens=True,
    )

    apply_trial(her_runtime, her_best)
    export_merged_model(her_runtime, output_dir / "heretic-best-merged")
    her_responses = her_runtime["model"].get_responses_batched(
        base_prompts,
        skip_special_tokens=True,
    )

    refusal_markers = icon_runtime["settings"].refusal_markers
    comparisons = []
    for item, base_response, icon_response, her_response in zip(
        sample_prompts,
        base_responses,
        icon_responses,
        her_responses,
    ):
        comparisons.append(
            {
                **item,
                "base": {
                    "refusal": is_refusal(base_response, refusal_markers),
                    "response": base_response,
                },
                "iconoclast": {
                    "refusal": is_refusal(icon_response, refusal_markers),
                    "response": icon_response,
                },
                "heretic": {
                    "refusal": is_refusal(her_response, refusal_markers),
                    "response": her_response,
                },
            }
        )

    summary = {
        "base_model": icon_runtime["settings"].model,
        "iconoclast_best": icon_best,
        "heretic_best": her_best,
        "comparison_sample_count_per_split": sample_count,
        "comparisons": comparisons,
    }

    (output_dir / "comparison.json").write_text(json.dumps(summary, indent=2))
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "base_model": summary["base_model"],
                "iconoclast_best": icon_best,
                "heretic_best": her_best,
            },
            indent=2,
        )
    )

    print(json.dumps(summary["iconoclast_best"], indent=2))
    print(json.dumps(summary["heretic_best"], indent=2))
    print(f"Wrote exports and comparison to {output_dir}")


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
