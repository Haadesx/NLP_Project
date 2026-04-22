# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026  Philipp Emanuel Weidmann <pew@worldwidemann.com> + contributors

import logging
import math
import os
import sys
import time
import json
import warnings
from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, version
from os.path import commonprefix
from pathlib import Path
from typing import Any, cast

import huggingface_hub
import numpy as np
import optuna
import questionary
import torch
import torch.nn.functional as F
import transformers
from accelerate.utils import (
    is_mlu_available,
    is_musa_available,
    is_npu_available,
    is_sdaa_available,
    is_xpu_available,
)
from huggingface_hub import ModelCard, ModelCardData
from optuna import Trial, TrialPruned
from optuna.exceptions import ExperimentalWarning
from optuna.samplers import TPESampler
from optuna.storages import JournalStorage
from optuna.storages.journal import JournalFileBackend, JournalFileOpenLock
from optuna.study import StudyDirection
from optuna.trial import TrialState
from pydantic import ValidationError
from questionary import Choice, Style
from rich.table import Table
from rich.traceback import install

from .analyzer import Analyzer
from .config import DirectionMethod, QuantizationMethod, Settings
from .direction import (
    blend_directions,
    compute_benign_subspace_basis,
    compute_direction_candidates,
    orthogonalize_directions,
    project_directions_out_of_subspace,
)
from .evaluator import Evaluator
from .model import AbliterationParameters, Model, get_model_class
from .utils import (
    empty_cache,
    format_duration,
    get_readme_intro,
    get_trial_parameters,
    load_prompts,
    print,
    print_memory_usage,
    prompt_password,
    prompt_path,
    prompt_select,
    prompt_text,
    set_random_seed,
)


def obtain_merge_strategy(settings: Settings) -> str | None:
    """
    Prompts the user for how to proceed with saving the model.
    Provides info to the user if the model is quantized on memory use.
    Returns "merge", "adapter", or None (if cancelled/invalid).
    """

    if settings.quantization == QuantizationMethod.BNB_4BIT:
        print()
        print(
            "Model was loaded with quantization. Merging requires reloading the base model."
        )
        print(
            "[yellow]WARNING: CPU merging requires dequantizing the entire model to system RAM.[/]"
        )
        print("[yellow]This can lead to system freezes if you run out of memory.[/]")

        try:
            # Estimate memory requirements by loading the model structure on the "meta" device.
            # This doesn't consume actual RAM but allows us to inspect the parameter count/dtype.
            #
            # Suppress warnings during meta device loading (e.g., "Some weights were not initialized").
            # These are expected and harmless since we're only inspecting model structure, not running inference.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                meta_model = get_model_class(settings.model).from_pretrained(
                    settings.model,
                    device_map="meta",
                    torch_dtype=torch.bfloat16,
                    trust_remote_code=settings.trust_remote_code,
                )
                footprint_bytes = meta_model.get_memory_footprint()
                footprint_gb = footprint_bytes / (1024**3)
                print(
                    f"[yellow]Estimated RAM required (excluding overhead): [bold]~{footprint_gb:.2f} GB[/][/]"
                )
        except Exception:
            # Fallback if meta loading fails (e.g. owing to custom model code
            # or bitsandbytes quantization config issues on the meta device).
            print(
                "[yellow]Rule of thumb: You need approximately 3x the parameter count in GB RAM.[/]"
            )
            print(
                "[yellow]Example: A 27B model requires ~80GB RAM. A 70B model requires ~200GB RAM.[/]"
            )
        print()

        strategy = prompt_select(
            "How do you want to proceed?",
            choices=[
                Choice(
                    title="Merge LoRA into full model"
                    + (
                        ""
                        if settings.quantization == QuantizationMethod.NONE
                        else " (requires sufficient RAM)"
                    ),
                    value="merge",
                ),
                Choice(
                    title="Cancel",
                    value="cancel",
                ),
            ],
        )

        if strategy == "cancel":
            return None

        return strategy
    else:
        return "merge"


def run():
    # Enable expandable segments to reduce memory fragmentation on multi-GPU setups.
    if (
        "PYTORCH_ALLOC_CONF" not in os.environ
        and "PYTORCH_CUDA_ALLOC_CONF" not in os.environ
    ):
        os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"

    # Modified "Pagga" font from https://budavariam.github.io/asciiart-text/
    try:
        app_version = version("iconoclast-llm")
    except PackageNotFoundError:
        app_version = "dev"

    print(f"[cyan]ICONOCLAST[/]  v{app_version}")
    print("[grey50]Discriminative representation editing for open-weight models[/]")
    print()

    if (
        # There is at least one argument (argv[0] is the program name).
        len(sys.argv) > 1
        # No model has been explicitly provided.
        and "--model" not in sys.argv
        # The last argument is a parameter value rather than a flag (such as "--help").
        and not sys.argv[-1].startswith("-")
    ):
        # Assume the last argument is the model.
        sys.argv.insert(-1, "--model")

    try:
        # The required argument "model" must be provided by the user,
        # either on the command line or in the configuration file.
        settings = Settings()  # ty:ignore[missing-argument]
    except ValidationError as error:
        print(f"[red]Configuration contains [bold]{error.error_count()}[/] errors:[/]")

        for error in error.errors():
            print(f"[bold]{error['loc'][0]}[/]: [yellow]{error['msg']}[/]")

        print()
        print(
            "Run [bold]iconoclast --help[/] or see [bold]config.default.toml[/] for details about configuration parameters."
        )
        return

    print(f"Using random seed [bold]{settings.seed}[/]")
    set_random_seed(settings.seed)

    # Adapted from https://github.com/huggingface/accelerate/blob/main/src/accelerate/commands/env.py
    if torch.cuda.is_available():
        count = torch.cuda.device_count()
        total_vram = sum(torch.cuda.mem_get_info(i)[1] for i in range(count))
        print(
            f"Detected [bold]{count}[/] CUDA device(s) ({total_vram / (1024**3):.2f} GB total VRAM):"
        )
        for i in range(count):
            vram = torch.cuda.mem_get_info(i)[1] / (1024**3)
            print(
                f"* GPU {i}: [bold]{torch.cuda.get_device_name(i)}[/] ({vram:.2f} GB)"
            )
    elif is_xpu_available():
        count = torch.xpu.device_count()
        print(f"Detected [bold]{count}[/] XPU device(s):")
        for i in range(count):
            print(f"* XPU {i}: [bold]{torch.xpu.get_device_name(i)}[/]")
    elif is_mlu_available():
        count = torch.mlu.device_count()  # ty:ignore[unresolved-attribute]
        print(f"Detected [bold]{count}[/] MLU device(s):")
        for i in range(count):
            print(f"* MLU {i}: [bold]{torch.mlu.get_device_name(i)}[/]")  # ty:ignore[unresolved-attribute]
    elif is_sdaa_available():
        count = torch.sdaa.device_count()  # ty:ignore[unresolved-attribute]
        print(f"Detected [bold]{count}[/] SDAA device(s):")
        for i in range(count):
            print(f"* SDAA {i}: [bold]{torch.sdaa.get_device_name(i)}[/]")  # ty:ignore[unresolved-attribute]
    elif is_musa_available():
        count = torch.musa.device_count()  # ty:ignore[unresolved-attribute]
        print(f"Detected [bold]{count}[/] MUSA device(s):")
        for i in range(count):
            print(f"* MUSA {i}: [bold]{torch.musa.get_device_name(i)}[/]")  # ty:ignore[unresolved-attribute]
    elif is_npu_available():
        print(f"NPU detected (CANN version: [bold]{torch.version.cann}[/])")  # ty:ignore[unresolved-attribute]
    elif torch.backends.mps.is_available():
        print("Detected [bold]1[/] MPS device (Apple Metal)")
    else:
        print(
            "[bold yellow]No GPU or other accelerator detected. Operations will be slow.[/]"
        )

    # We don't need gradients as we only do inference.
    torch.set_grad_enabled(False)

    # While determining the optimal batch size, we will try many different batch sizes,
    # resulting in many computation graphs being compiled. Raising the limit (default = 8)
    # avoids errors from TorchDynamo assuming that something is wrong because we
    # recompile too often.
    torch._dynamo.config.cache_size_limit = 64

    # Silence warning spam from Transformers.
    # In my entire career I've never seen a useful warning from that library.
    transformers.logging.set_verbosity_error()

    # Another library that generates warning spam.
    logging.getLogger("lm_eval").setLevel(logging.ERROR)

    # We do our own trial logging, so we don't need the INFO messages
    # about parameters and results.
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    # Silence the warning about multivariate TPE being experimental.
    warnings.filterwarnings("ignore", category=ExperimentalWarning)

    os.makedirs(settings.study_checkpoint_dir, exist_ok=True)

    study_checkpoint_file = os.path.join(
        settings.study_checkpoint_dir,
        "".join(
            [(c if (c.isalnum() or c in ["_", "-"]) else "--") for c in settings.model]
        )
        + ".jsonl",
    )

    lock_obj = JournalFileOpenLock(study_checkpoint_file)
    backend = JournalFileBackend(study_checkpoint_file, lock_obj=lock_obj)
    storage = JournalStorage(backend)

    try:
        existing_study = storage.get_all_studies()[0]
    except IndexError:
        existing_study = None

    if existing_study is not None and settings.evaluate_model is None:
        if settings.exit_after_optimization:
            print()
            print(
                "[yellow]Existing study detected.[/] Reusing stored settings in batch mode."
            )
            settings = Settings.model_validate_json(existing_study.user_attrs["settings"])
        else:
            choices = []

            if existing_study.user_attrs["finished"]:
                print()
                print(
                    (
                        "[green]You have already processed this model.[/] "
                        "You can show the results from the previous run, allowing you to export models or to run additional trials. "
                        "Alternatively, you can ignore the previous run and start from scratch. "
                        "This will delete the checkpoint file and all results from the previous run."
                    )
                )
                choices.append(
                    Choice(
                        title="Show the results from the previous run",
                        value="continue",
                    )
                )
            else:
                print()
                print(
                    (
                        "[yellow]You have already processed this model, but the run was interrupted.[/] "
                        "You can continue the previous run from where it stopped. This will override any specified settings. "
                        "Alternatively, you can ignore the previous run and start from scratch. "
                        "This will delete the checkpoint file and all results from the previous run."
                    )
                )
                choices.append(
                    Choice(
                        title="Continue the previous run",
                        value="continue",
                    )
                )

            choices.append(
                Choice(
                    title="Ignore the previous run and start from scratch",
                    value="restart",
                )
            )

            choices.append(
                Choice(
                    title="Exit program",
                    value="",
                )
            )

            print()
            choice = prompt_select("How would you like to proceed?", choices)

            if choice == "continue":
                settings = Settings.model_validate_json(
                    existing_study.user_attrs["settings"]
                )
            elif choice == "restart":
                os.unlink(study_checkpoint_file)
                backend = JournalFileBackend(study_checkpoint_file, lock_obj=lock_obj)
                storage = JournalStorage(backend)
            elif choice is None or choice == "":
                return

    model = Model(settings)
    print()
    print_memory_usage()

    print()
    print(f"Loading good prompts from [bold]{settings.good_prompts.dataset}[/]...")
    good_prompts = load_prompts(settings, settings.good_prompts)
    print(f"* [bold]{len(good_prompts)}[/] prompts loaded")

    print()
    print(f"Loading bad prompts from [bold]{settings.bad_prompts.dataset}[/]...")
    bad_prompts = load_prompts(settings, settings.bad_prompts)
    print(f"* [bold]{len(bad_prompts)}[/] prompts loaded")

    if settings.batch_size == 0:
        print()
        print("Determining optimal batch size...")

        batch_size = 1
        best_batch_size = -1
        best_performance = -1

        while batch_size <= settings.max_batch_size:
            print(f"* Trying batch size [bold]{batch_size}[/]... ", end="")

            prompts = good_prompts * math.ceil(batch_size / len(good_prompts))
            prompts = prompts[:batch_size]

            try:
                # Warmup run to build the computation graph so that part isn't benchmarked.
                model.get_responses(prompts)

                start_time = time.perf_counter()
                responses = model.get_responses(prompts)
                end_time = time.perf_counter()
            except Exception as error:
                if batch_size == 1:
                    # Even a batch size of 1 already fails.
                    # We cannot recover from this.
                    raise

                print(f"[red]Failed[/] ({error})")
                break

            response_lengths = [
                len(model.tokenizer.encode(response)) for response in responses
            ]
            performance = sum(response_lengths) / (end_time - start_time)

            print(f"[green]Ok[/] ([bold]{performance:.0f}[/] tokens/s)")

            if performance > best_performance:
                best_batch_size = batch_size
                best_performance = performance

            batch_size *= 2

        settings.batch_size = best_batch_size
        print(f"* Chosen batch size: [bold]{settings.batch_size}[/]")

    print()
    print("Checking for common response prefix...")
    prefix_check_prompts = good_prompts[:100] + bad_prompts[:100]
    responses = model.get_responses_batched(prefix_check_prompts)

    # Despite being located in os.path, commonprefix actually performs
    # a naive string operation without any path-specific logic,
    # which is exactly what we need here. Trailing spaces are removed
    # to avoid issues where multiple different tokens that all start
    # with a space character lead to the common prefix ending with
    # a space, which would result in an uncommon tokenization.
    model.response_prefix = commonprefix(responses).rstrip(" ")

    # Suppress CoT output.
    recheck_prefix = False
    if model.response_prefix:
        # When using any of the predefined prefixes below, we need to check that
        # the prefix is actually complete (e.g. not missing a trailing newline).
        recheck_prefix = True
        if model.response_prefix.startswith("<think>"):
            # Most thinking models.
            model.response_prefix = "<think></think>"
        elif model.response_prefix.startswith("<|channel|>analysis<|message|>"):
            # gpt-oss.
            model.response_prefix = "<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>final<|message|>"
        elif model.response_prefix.startswith("<thought>"):
            # Unknown, suggested by user.
            model.response_prefix = "<thought></thought>"
        elif model.response_prefix.startswith("[THINK]"):
            # Unknown, suggested by user.
            model.response_prefix = "[THINK][/THINK]"
        else:
            recheck_prefix = False

    if model.response_prefix:
        print(f"* Prefix found: [bold]{model.response_prefix!r}[/]")
    else:
        print("* None found")

    if recheck_prefix:
        print("* Rechecking with prefix...")
        responses = model.get_responses_batched(prefix_check_prompts)
        additional_prefix = commonprefix(responses).rstrip(" ")
        if additional_prefix:
            model.response_prefix += additional_prefix
            print(f"* Extended prefix found: [bold]{model.response_prefix!r}[/]")

    evaluator = Evaluator(settings, model)

    if settings.evaluate_model is not None:
        print()
        print(f"Loading model [bold]{settings.evaluate_model}[/]...")
        settings.model = settings.evaluate_model
        model.reset_model()
        print("* Evaluating...")
        evaluator.get_score()
        return

    print()
    print("Calculating per-layer refusal directions...")
    print("* Obtaining residuals for good prompts...")
    good_residuals = model.get_residuals_batched(good_prompts)
    print("* Obtaining residuals for bad prompts...")
    bad_residuals = model.get_residuals_batched(bad_prompts)

    good_means = good_residuals.mean(dim=0)
    direction_candidates = compute_direction_candidates(
        good_residuals,
        bad_residuals,
        settings.direction_variance_floor,
    )

    if settings.benign_subspace_rank > 0:
        benign_subspace_basis = compute_benign_subspace_basis(
            good_residuals,
            settings.benign_subspace_rank,
        )
        if benign_subspace_basis is not None:
            direction_candidates = {
                method: project_directions_out_of_subspace(
                    candidate,
                    benign_subspace_basis,
                )
                for method, candidate in direction_candidates.items()
            }

    if settings.orthogonalize_direction:
        # Implements https://huggingface.co/blog/grimjim/projected-abliteration
        # for every candidate direction set rather than only the mean-difference one.
        direction_candidates = {
            method: orthogonalize_directions(candidate, good_means)
            for method, candidate in direction_candidates.items()
        }

    analyzer = Analyzer(settings, model, good_residuals, bad_residuals)

    if settings.print_residual_geometry:
        analyzer.print_residual_geometry()

    if settings.plot_residuals:
        analyzer.plot_residuals()

    # We don't need the residuals after computing refusal directions.
    del good_residuals, bad_residuals, analyzer
    empty_cache()

    components = model.get_abliterable_components()
    last_layer_index = len(model.get_layers()) - 1
    trial_index = 0
    start_index = 0
    start_time = time.perf_counter()

    def build_direction_tensor(
        direction_method: DirectionMethod,
        direction_blend: float,
    ) -> torch.Tensor:
        if direction_method == DirectionMethod.HYBRID:
            return blend_directions(
                direction_candidates[DirectionMethod.MEAN],
                direction_candidates[DirectionMethod.VARIANCE],
                direction_blend,
            )

        return direction_candidates[direction_method]

    def get_trial_direction_indices(
        trial: Trial,
    ) -> float | None | dict[str, float | None]:
        component_direction_scopes = trial.user_attrs.get("component_direction_scopes")
        if isinstance(component_direction_scopes, dict):
            component_direction_indices = trial.user_attrs.get(
                "component_direction_indices",
                {},
            )
            return {
                component: (
                    None
                    if component_direction_scopes.get(component) == "per layer"
                    else component_direction_indices.get(component)
                )
                for component in components
            }

        direction_scope = trial.params.get(
            "direction_scope",
            trial.user_attrs.get("direction_scope", "global"),
        )
        if direction_scope == "per layer":
            return None
        return trial.params.get(
            "direction_index",
            trial.user_attrs.get("direction_index"),
        )

    def get_trial_refusal_directions(
        trial: Trial,
    ) -> torch.Tensor | dict[str, torch.Tensor]:
        component_direction_methods = trial.user_attrs.get("component_direction_methods")
        if isinstance(component_direction_methods, dict):
            component_direction_blends = trial.user_attrs.get(
                "component_direction_blends",
                {},
            )
            return {
                component: build_direction_tensor(
                    DirectionMethod(component_direction_methods[component]),
                    float(component_direction_blends.get(component, 0.0)),
                )
                for component in components
            }

        direction_method = DirectionMethod(
            trial.params.get(
                "direction_method",
                trial.user_attrs.get("direction_method", DirectionMethod.MEAN.value),
            )
        )
        direction_blend = float(
            trial.params.get(
                "direction_blend",
                trial.user_attrs.get("direction_blend", 0.0),
            )
        )
        return build_direction_tensor(direction_method, direction_blend)

    def recompute_objective_score(
        behavior_score: float,
        kl_divergence: float,
    ) -> tuple[float, float]:
        if kl_divergence >= settings.kl_divergence_target:
            kld_score = kl_divergence / settings.kl_divergence_scale
        else:
            kld_score = (
                behavior_score
                * settings.kl_divergence_target
                / settings.kl_divergence_scale
            )
        return (kld_score, behavior_score)

    def should_run_merged_validation(refusals: int) -> bool:
        if settings.merged_validation_interval <= 0:
            return False
        if trial_index == settings.n_trials:
            return True
        if refusals > evaluator.base_refusals:
            return False
        return trial_index % settings.merged_validation_interval == 0

    def compute_merge_penalty(
        adapter_result: Any,
        merged_result: Any,
    ) -> float:
        harmful_count = max(settings.merged_validation_subset_size, 1)
        merge_refusal_gap = max(
            0,
            merged_result.refusals
            - adapter_result.refusals
            - settings.merged_validation_refusal_tolerance,
        ) / harmful_count
        merge_overrefusal_gap = max(
            0,
            merged_result.overrefusals
            - adapter_result.overrefusals
            - settings.merged_validation_overrefusal_tolerance,
        ) / harmful_count
        merge_disclaimer_gap = max(
            0,
            merged_result.harmful_marker_hits
            - adapter_result.harmful_marker_hits
            - settings.merged_validation_disclaimer_tolerance,
        ) / harmful_count
        merge_compliance_gap = max(
            0.0,
            adapter_result.harmful_compliance_score
            - merged_result.harmful_compliance_score
            - settings.merged_validation_compliance_tolerance,
        )
        return settings.merged_consistency_penalty * (
            merge_refusal_gap
            + merge_overrefusal_gap
            + merge_disclaimer_gap
            + merge_compliance_gap
        )

    def objective(trial: Trial) -> tuple[float, float]:
        nonlocal trial_index
        trial_index += 1
        trial.set_user_attr("index", trial_index)
        component_direction_scopes = {}
        component_direction_indices = {}
        component_direction_methods = {}
        component_direction_blends = {}

        if settings.component_specific_directions:
            refusal_directions = {}
            direction_index: float | None | dict[str, float | None] = {}
            for component in components:
                direction_scope = trial.suggest_categorical(
                    f"{component}.direction_scope",
                    ["global", "per layer"],
                )
                sampled_direction_index = trial.suggest_float(
                    f"{component}.direction_index",
                    0.4 * last_layer_index,
                    0.9 * last_layer_index,
                )
                if direction_scope == "per layer":
                    component_direction_indices[component] = None
                else:
                    component_direction_indices[component] = sampled_direction_index
                direction_method = DirectionMethod(
                    trial.suggest_categorical(
                        f"{component}.direction_method",
                        [method.value for method in DirectionMethod],
                    )
                )
                direction_blend = trial.suggest_float(
                    f"{component}.direction_blend",
                    0.0,
                    1.0,
                )
                refusal_directions[component] = build_direction_tensor(
                    direction_method,
                    direction_blend,
                )
                cast(dict[str, float | None], direction_index)[component] = (
                    component_direction_indices[component]
                )
                component_direction_scopes[component] = direction_scope
                component_direction_methods[component] = direction_method.value
                component_direction_blends[component] = direction_blend
            trial.set_user_attr("direction_scope", "mixed")
            trial.set_user_attr("direction_index", None)
            trial.set_user_attr("direction_method", "mixed")
            trial.set_user_attr("direction_blend", 0.0)
            trial.set_user_attr(
                "component_direction_scopes",
                component_direction_scopes,
            )
            trial.set_user_attr(
                "component_direction_indices",
                component_direction_indices,
            )
            trial.set_user_attr(
                "component_direction_methods",
                component_direction_methods,
            )
            trial.set_user_attr(
                "component_direction_blends",
                component_direction_blends,
            )
        else:
            direction_scope = trial.suggest_categorical(
                "direction_scope",
                ["global", "per layer"],
            )
            direction_index = trial.suggest_float(
                "direction_index",
                0.4 * last_layer_index,
                0.9 * last_layer_index,
            )
            if direction_scope == "per layer":
                direction_index = None
            direction_method = DirectionMethod(
                trial.suggest_categorical(
                    "direction_method",
                    [method.value for method in DirectionMethod],
                )
            )
            direction_blend = trial.suggest_float(
                "direction_blend",
                0.0,
                1.0,
            )
            refusal_directions = build_direction_tensor(direction_method, direction_blend)
            trial.set_user_attr("direction_scope", direction_scope)
            trial.set_user_attr("direction_index", direction_index)
            trial.set_user_attr("direction_method", direction_method.value)
            trial.set_user_attr("direction_blend", direction_blend)

        parameters = {}

        for component in components:
            # The parameter ranges are based on experiments with various models
            # and much wider ranges. They are not set in stone and might have to be
            # adjusted for future models.
            max_weight = trial.suggest_float(
                f"{component}.max_weight",
                0.5,
                2.0,
            )
            max_weight_position = trial.suggest_float(
                f"{component}.max_weight_position",
                0.4 * last_layer_index,
                1.0 * last_layer_index,
            )
            # For sampling purposes, min_weight is expressed as a fraction of max_weight,
            # again because multivariate TPE doesn't support variable-range parameters.
            # The value is transformed into the actual min_weight value below.
            min_weight = trial.suggest_float(
                f"{component}.min_weight",
                0.0,
                1.0,
            )
            min_weight_distance = trial.suggest_float(
                f"{component}.min_weight_distance",
                1.0,
                0.6 * last_layer_index,
            )

            parameters[component] = AbliterationParameters(
                max_weight=max_weight,
                max_weight_position=max_weight_position,
                min_weight=(min_weight * max_weight),
                min_weight_distance=min_weight_distance,
            )

        trial.set_user_attr("parameters", {k: asdict(v) for k, v in parameters.items()})

        print()
        print(
            f"Running trial [bold]{trial_index}[/] of [bold]{settings.n_trials}[/]..."
        )
        print("* Parameters:")
        for name, value in get_trial_parameters(trial).items():
            print(f"  * {name} = [bold]{value}[/]")
        print("* Resetting model...")
        model.reset_model()
        print("* Abliterating...")
        model.abliterate(refusal_directions, direction_index, parameters)
        print("* Evaluating...")
        evaluation_result = evaluator.get_score()
        score = evaluation_result.score
        kl_divergence = evaluation_result.kl_divergence
        refusals = evaluation_result.refusals
        overrefusals = evaluation_result.overrefusals
        harmful_marker_hits = evaluation_result.harmful_marker_hits
        harmful_compliance_score = evaluation_result.harmful_compliance_score
        merge_penalty = 0.0

        if should_run_merged_validation(refusals):
            print("* Validating merged-model subset...")
            merged_result = model.evaluate_merged(
                lambda: evaluator.get_subset_score(settings.merged_validation_subset_size)
            )
            merge_penalty = compute_merge_penalty(evaluation_result, merged_result)
            trial.set_user_attr("merged_validated", True)
            trial.set_user_attr("merged_refusals", merged_result.refusals)
            trial.set_user_attr("merged_overrefusals", merged_result.overrefusals)
            trial.set_user_attr(
                "merged_harmful_marker_hits",
                merged_result.harmful_marker_hits,
            )
            trial.set_user_attr(
                "merged_harmful_compliance_score",
                merged_result.harmful_compliance_score,
            )
            trial.set_user_attr("merge_penalty", merge_penalty)
            score = recompute_objective_score(
                evaluation_result.behavior_score + merge_penalty,
                kl_divergence,
            )
        else:
            trial.set_user_attr("merged_validated", False)
            trial.set_user_attr("merge_penalty", 0.0)

        elapsed_time = time.perf_counter() - start_time
        remaining_time = (elapsed_time / (trial_index - start_index)) * (
            settings.n_trials - trial_index
        )
        print()
        print(f"[grey50]Elapsed time: [bold]{format_duration(elapsed_time)}[/][/]")
        if trial_index < settings.n_trials:
            print(
                f"[grey50]Estimated remaining time: [bold]{format_duration(remaining_time)}[/][/]"
            )
        print_memory_usage()

        trial.set_user_attr("kl_divergence", kl_divergence)
        trial.set_user_attr("refusals", refusals)
        trial.set_user_attr("overrefusals", overrefusals)
        trial.set_user_attr("harmful_marker_hits", harmful_marker_hits)
        trial.set_user_attr("harmful_compliance_score", harmful_compliance_score)
        trial.set_user_attr("objective_regime", evaluation_result.objective_regime)
        trial.set_user_attr("harmful_axis_metrics", evaluation_result.harmful_axis_metrics)

        return score

    def objective_wrapper(trial: Trial) -> tuple[float, float]:
        try:
            return objective(trial)
        except KeyboardInterrupt:
            # Stop the study gracefully on Ctrl+C.
            trial.study.stop()
            raise TrialPruned()

    study = optuna.create_study(
        sampler=TPESampler(
            seed=settings.seed,
            n_startup_trials=settings.n_startup_trials,
            n_ei_candidates=128,
            multivariate=True,
        ),
        directions=[StudyDirection.MINIMIZE, StudyDirection.MINIMIZE],
        storage=storage,
        study_name="iconoclast",
        load_if_exists=True,
    )

    study.set_user_attr("settings", settings.model_dump_json())
    study.set_user_attr("finished", False)

    def count_completed_trials() -> int:
        # Count number of complete trials to compute trials to run.
        return sum([(1 if t.state == TrialState.COMPLETE else 0) for t in study.trials])

    def get_completed_trials() -> list[Trial]:
        return [t for t in study.trials if t.state == TrialState.COMPLETE]

    if settings.warm_start_trials and count_completed_trials() == 0:
        print()
        print(
            f"Queueing [bold]{len(settings.warm_start_trials)}[/] warm-start trial(s)..."
        )
        for warm_start_trial in settings.warm_start_trials:
            study.enqueue_trial(dict(warm_start_trial.params))
            if warm_start_trial.description:
                print(f"* {warm_start_trial.description}")

    def get_pareto_trials(completed_trials: list[Trial]) -> list[Trial]:
        sorted_trials = sorted(
            completed_trials,
            key=lambda trial: (
                trial.user_attrs["refusals"],
                trial.user_attrs.get("overrefusals", 0),
                trial.user_attrs["kl_divergence"],
            ),
        )
        min_divergence = math.inf
        min_overrefusals = math.inf
        best_trials = []
        for trial in sorted_trials:
            kl_divergence = trial.user_attrs["kl_divergence"]
            overrefusals = trial.user_attrs.get("overrefusals", 0)
            if (
                overrefusals < min_overrefusals
                or (
                    overrefusals == min_overrefusals
                    and kl_divergence < min_divergence
                )
            ):
                min_overrefusals = overrefusals
                min_divergence = kl_divergence
                best_trials.append(trial)
        return best_trials

    def serialize_trial(trial: Trial) -> dict[str, Any]:
        return {
            "index": trial.user_attrs.get("index"),
            "refusals": trial.user_attrs["refusals"],
            "overrefusals": trial.user_attrs.get("overrefusals", 0),
            "harmful_marker_hits": trial.user_attrs.get("harmful_marker_hits", 0),
            "harmful_compliance_score": trial.user_attrs.get(
                "harmful_compliance_score", 0.0
            ),
            "objective_regime": trial.user_attrs.get("objective_regime"),
            "merge_penalty": trial.user_attrs.get("merge_penalty", 0.0),
            "kl_divergence": trial.user_attrs["kl_divergence"],
            "direction_method": trial.user_attrs.get("direction_method"),
            "direction_scope": trial.user_attrs.get("direction_scope"),
            "direction_index": trial.user_attrs.get("direction_index"),
            "direction_blend": trial.user_attrs.get("direction_blend"),
            "parameters": trial.user_attrs.get("parameters", {}),
            "harmful_axis_metrics": trial.user_attrs.get("harmful_axis_metrics", {}),
        }

    def write_batch_summary(best_trials: list[Trial]) -> Path:
        summary_path = Path(settings.study_checkpoint_dir, "batch_summary.json")
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "model": settings.model,
            "study_checkpoint_dir": settings.study_checkpoint_dir,
            "base_metrics": {
                "refusals": evaluator.base_refusals,
                "overrefusals": evaluator.base_overrefusals,
                "harmful_marker_hits": evaluator.base_harmful_marker_hits,
                "harmful_compliance_score": evaluator.base_harmful_compliance_score,
                "objective_regime": evaluator.objective_regime.value,
            },
            "pareto_trials": [serialize_trial(trial) for trial in best_trials],
        }
        summary_path.write_text(json.dumps(summary, indent=2))
        return summary_path

    start_index = trial_index = count_completed_trials()
    if start_index > 0:
        print()
        print("Resuming existing study.")

    try:
        study.optimize(
            objective_wrapper,
            n_trials=settings.n_trials - count_completed_trials(),
        )
    except KeyboardInterrupt:
        # This additional handler takes care of the small chance that KeyboardInterrupt
        # is raised just between trials, which wouldn't be caught by the handler
        # defined in objective_wrapper above.
        pass

    if count_completed_trials() == settings.n_trials:
        study.set_user_attr("finished", True)

    if settings.exit_after_optimization:
        completed_trials = get_completed_trials()
        print()
        print("[bold green]Optimization finished in batch mode.[/]")
        if not completed_trials:
            print("[yellow]No completed trials were recorded.[/]")
            return

        best_trials = get_pareto_trials(completed_trials)
        summary_path = write_batch_summary(best_trials)

        print("Top Pareto trials:")
        for trial in best_trials[:5]:
            print(
                f"* Trial {trial.user_attrs['index']}: "
                f"refusals={trial.user_attrs['refusals']}/{len(evaluator.bad_prompts)}, "
                f"overrefusals={trial.user_attrs.get('overrefusals', 0)}/{len(evaluator.good_prompts)}, "
                f"markers={trial.user_attrs.get('harmful_marker_hits', 0)}, "
                f"compliance={trial.user_attrs.get('harmful_compliance_score', 0.0):.3f}, "
                f"kl={trial.user_attrs['kl_divergence']:.4f}"
            )

        print(f"Batch summary written to [bold]{summary_path}[/].")
        return

    while True:
        # If no trials at all have been evaluated, the study must have been stopped
        # by pressing Ctrl+C while the first trial was running. In this case, we just
        # re-raise the interrupt to invoke the standard handler defined below.
        completed_trials = get_completed_trials()
        if not completed_trials:
            raise KeyboardInterrupt

        # Get the Pareto front of trials. We can't use study.best_trials directly
        # as get_score() doesn't return the pure KL divergence and refusal count.
        # Note: Unlike study.best_trials, this does not handle objective constraints.
        best_trials = get_pareto_trials(completed_trials)

        choices = [
            Choice(
                title=(
                    f"[Trial {trial.user_attrs['index']:>3}] "
                    f"Refusals: {trial.user_attrs['refusals']:>2}/{len(evaluator.bad_prompts)}, "
                    f"Overrefusals: {trial.user_attrs.get('overrefusals', 0):>2}/{len(evaluator.good_prompts)}, "
                    f"Markers: {trial.user_attrs.get('harmful_marker_hits', 0):>3}, "
                    f"Compliance: {trial.user_attrs.get('harmful_compliance_score', 0.0):.2f}, "
                    f"MergePen: {trial.user_attrs.get('merge_penalty', 0.0):.2f}, "
                    f"Method: {trial.user_attrs.get('direction_method', 'mean')}, "
                    f"KL divergence: {trial.user_attrs['kl_divergence']:.4f}"
                ),
                value=trial,
            )
            for trial in best_trials
        ]

        choices.append(
            Choice(
                title="Run additional trials",
                value="continue",
            )
        )

        choices.append(
            Choice(
                title="Exit program",
                value="",
            )
        )

        print()
        print("[bold green]Optimization finished![/]")
        print()
        print(
            (
                "The following trials resulted in Pareto optimal combinations of refusals and KL divergence. "
                "Trials are ordered to prefer lower harmful refusals first, then lower overrefusals, then lower KL divergence. "
                "After selecting a trial, you will be able to save the model, upload it to Hugging Face, "
                "or chat with it to test how well it works. You can return to this menu later to select a different trial. "
                "[yellow]Note that KL divergence values above 1 usually indicate significant damage to the original model's capabilities.[/]"
            )
        )

        while True:
            print()
            trial = prompt_select("Which trial do you want to use?", choices)

            if trial == "continue":
                while True:
                    try:
                        n_additional_trials = prompt_text(
                            "How many additional trials do you want to run?"
                        )
                        if n_additional_trials is None or n_additional_trials == "":
                            n_additional_trials = 0
                            break
                        n_additional_trials = int(n_additional_trials)
                        if n_additional_trials > 0:
                            break
                        print("[red]Please enter a number greater than 0.[/]")
                    except ValueError:
                        print("[red]Please enter a number.[/]")

                if n_additional_trials == 0:
                    continue

                settings.n_trials += n_additional_trials
                study.set_user_attr("settings", settings.model_dump_json())
                study.set_user_attr("finished", False)

                try:
                    study.optimize(
                        objective_wrapper,
                        n_trials=settings.n_trials - count_completed_trials(),
                    )
                except KeyboardInterrupt:
                    pass

                if count_completed_trials() == settings.n_trials:
                    study.set_user_attr("finished", True)

                break

            elif trial is None or trial == "":
                return

            print()
            print(f"Restoring model from trial [bold]{trial.user_attrs['index']}[/]...")
            print("* Parameters:")
            for name, value in get_trial_parameters(trial).items():
                print(f"  * {name} = [bold]{value}[/]")
            print("* Resetting model...")
            model.reset_model()
            print("* Abliterating...")
            model.abliterate(
                get_trial_refusal_directions(trial),
                get_trial_direction_indices(trial),
                {
                    k: AbliterationParameters(**v)
                    for k, v in trial.user_attrs["parameters"].items()
                },
            )

            while True:
                print()
                action = prompt_select(
                    "What do you want to do with the decensored model?",
                    [
                        "Save the model to a local folder",
                        "Upload the model to Hugging Face",
                        "Chat with the model",
                        "Benchmark the model",
                        "Return to the trial selection menu",
                    ],
                )

                if action is None or action == "Return to the trial selection menu":
                    break

                # All actions are wrapped in a try/except block so that if an error occurs,
                # another action can be tried, instead of the program crashing and losing
                # the optimized model.
                try:
                    match action:
                        case "Save the model to a local folder":
                            save_directory = prompt_path("Path to the folder:")
                            if not save_directory:
                                continue

                            strategy = obtain_merge_strategy(settings)
                            if strategy is None:
                                continue

                            if strategy == "adapter":
                                print("Saving LoRA adapter...")
                                model.model.save_pretrained(save_directory)
                            else:
                                print("Saving merged model...")
                                merged_model = model.get_merged_model()
                                merged_model.save_pretrained(save_directory)
                                del merged_model
                                empty_cache()
                                model.tokenizer.save_pretrained(save_directory)

                            print(f"Model saved to [bold]{save_directory}[/].")

                        case "Upload the model to Hugging Face":
                            # We don't use huggingface_hub.login() because that stores the token on disk,
                            # and since this program will often be run on rented or shared GPU servers,
                            # it's better to not persist credentials.
                            token = huggingface_hub.get_token()
                            if not token:
                                token = prompt_password("Hugging Face access token:")
                            if not token:
                                continue

                            user = huggingface_hub.whoami(token)
                            fullname = user.get(
                                "fullname",
                                user.get("name", "unknown user"),
                            )
                            email = user.get("email", "no email found")
                            print(f"Logged in as [bold]{fullname} ({email})[/]")

                            repo_id = prompt_text(
                                "Name of repository:",
                                default=f"{user['name']}/{Path(settings.model).name}-iconoclast",
                            )

                            visibility = prompt_select(
                                "Should the repository be public or private?",
                                [
                                    "Public",
                                    "Private",
                                ],
                            )
                            if visibility is None:
                                continue
                            private = visibility == "Private"

                            strategy = obtain_merge_strategy(settings)
                            if strategy is None:
                                continue

                            if strategy == "adapter":
                                print("Uploading LoRA adapter...")
                                model.model.push_to_hub(
                                    repo_id,
                                    private=private,
                                    token=token,
                                )
                            else:
                                print("Uploading merged model...")
                                merged_model = model.get_merged_model()
                                merged_model.push_to_hub(
                                    repo_id,
                                    private=private,
                                    token=token,
                                )
                                del merged_model
                                empty_cache()
                                model.tokenizer.push_to_hub(
                                    repo_id,
                                    private=private,
                                    token=token,
                                )

                            # If the model path exists locally and includes the
                            # card, use it directly. If the model path doesn't
                            # exist locally, it can be assumed to be a model
                            # hosted on the Hugging Face Hub, in which case
                            # we can retrieve the model card.
                            model_path = Path(settings.model)
                            if model_path.exists():
                                card_path = (
                                    model_path / huggingface_hub.constants.REPOCARD_NAME
                                )
                                if card_path.exists():
                                    card = ModelCard.load(card_path)
                                else:
                                    card = None
                            else:
                                card = ModelCard.load(settings.model)
                            if card is not None:
                                if card.data is None:
                                    card.data = ModelCardData()
                                if card.data.tags is None:
                                    card.data.tags = []
                                card.data.tags.append("iconoclast")
                                card.data.tags.append("uncensored")
                                card.data.tags.append("decensored")
                                card.data.tags.append("abliterated")
                                card.text = (
                                    get_readme_intro(
                                        settings,
                                        trial,
                                        evaluator.base_refusals,
                                        evaluator.base_overrefusals,
                                        evaluator.good_prompts,
                                        evaluator.bad_prompts,
                                    )
                                    + card.text
                                )
                                card.push_to_hub(repo_id, token=token)

                            print(f"Model uploaded to [bold]{repo_id}[/].")

                        case "Chat with the model":
                            print()
                            print(
                                "[cyan]Press Ctrl+C at any time to return to the menu.[/]"
                            )

                            chat = [
                                {"role": "system", "content": settings.system_prompt},
                            ]

                            while True:
                                try:
                                    message = prompt_text(
                                        "User:",
                                        qmark=">",
                                        unsafe=True,
                                    )
                                    if not message:
                                        break
                                    chat.append({"role": "user", "content": message})

                                    print("[bold]Assistant:[/] ", end="")
                                    response = model.stream_chat_response(chat)
                                    chat.append(
                                        {"role": "assistant", "content": response}
                                    )
                                except (KeyboardInterrupt, EOFError):
                                    # Ctrl+C/Ctrl+D
                                    break

                        case "Benchmark the model":
                            import lm_eval
                            from lm_eval.models.huggingface import HFLM

                            benchmarks = questionary.checkbox(
                                "Which benchmarks do you want to run?",
                                [
                                    Choice(
                                        title=f"{benchmark.name}: {benchmark.description}",
                                        value=benchmark,
                                    )
                                    for benchmark in settings.benchmarks
                                ],
                                style=Style([("highlighted", "reverse")]),
                            ).ask()
                            if not benchmarks:
                                continue

                            scope = prompt_select(
                                (
                                    "Do you want to benchmark the original model along with the decensored model? "
                                    "Benchmarking both models allows you to compare the scores, but it takes twice as much time."
                                ),
                                [
                                    "Benchmark only the decensored model",
                                    "Benchmark both models",
                                ],
                            )
                            if scope is None:
                                continue
                            benchmark_original_model = scope == "Benchmark both models"

                            hflm = HFLM(
                                pretrained=model.model,  # ty:ignore[invalid-argument-type]
                                tokenizer=model.tokenizer,  # ty:ignore[invalid-argument-type]
                            )

                            table = Table()
                            table.add_column("Benchmark")
                            table.add_column("Metric")
                            if benchmark_original_model:
                                table.add_column("This model", justify="right")
                                table.add_column("Original model", justify="right")
                            else:
                                table.add_column("Value", justify="right")

                            try:
                                first_benchmark = True

                                for benchmark in benchmarks:
                                    print(
                                        f"Running benchmark [bold]{benchmark.name}[/]..."
                                    )

                                    def get_results() -> dict[str, Any]:
                                        results = lm_eval.simple_evaluate(
                                            model=hflm,
                                            tasks=[benchmark.task],
                                            batch_size="auto",
                                        )
                                        return results["results"][benchmark.task]

                                    results = get_results()
                                    if benchmark_original_model:
                                        with model.model.disable_adapter():  # ty:ignore[call-non-callable]
                                            original_results = get_results()

                                    first_row = True

                                    for metric, value in results.items():
                                        if metric != "alias":
                                            if first_row and not first_benchmark:
                                                if benchmark_original_model:
                                                    table.add_row("", "", "", "")
                                                else:
                                                    table.add_row("", "", "")

                                            def format_value(value: Any) -> str:
                                                if isinstance(
                                                    value,
                                                    (float, np.floating),
                                                ):
                                                    return f"{value:.4f}"
                                                else:
                                                    return f"{value}"

                                            cells = [
                                                benchmark.name if first_row else "",
                                                metric,
                                                format_value(value),
                                            ]
                                            if benchmark_original_model:
                                                cells.append(
                                                    format_value(
                                                        original_results[metric]
                                                    )
                                                )
                                            table.add_row(*cells)

                                            first_row = False
                                            first_benchmark = False
                            except KeyboardInterrupt:
                                pass

                            # The benchmark run might have been cancelled by the user
                            # before any benchmark was completed, so we only print results
                            # if there actually are some.
                            if table.rows:
                                print(table)

                except Exception as error:
                    print(f"[red]Error: {error}[/]")


def main():
    # Install Rich traceback handler.
    install()

    try:
        run()
    except BaseException as error:
        # Transformers appears to handle KeyboardInterrupt (or BaseException)
        # internally in some places, which can re-raise a different error in the handler,
        # masking the root cause. We therefore check both the error itself and its context.
        if isinstance(error, KeyboardInterrupt) or isinstance(
            error.__context__, KeyboardInterrupt
        ):
            print()
            print("[red]Shutting down...[/]")
        else:
            raise
