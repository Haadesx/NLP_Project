#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize matched Iconoclast vs Heretic benchmark runs."
    )
    parser.add_argument(
        "--spec",
        action="append",
        required=True,
        help=(
            "Benchmark spec in the form "
            "'label|iconoclast_checkpoint_or_summary|heretic_checkpoint'. "
            "Can be passed multiple times."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )
    return parser.parse_args()


def load_iconoclast_best(path: Path) -> dict[str, Any]:
    if path.name == "batch_summary.json":
        summary = json.loads(path.read_text())
        trials = summary.get("pareto_trials", [])
        if not trials:
            raise ValueError(f"No pareto trials found in {path}")
        return trials[0]

    return load_best_from_study(path)


def load_best_from_study(path: Path) -> dict[str, Any]:
    trials: dict[int, dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        obj = json.loads(line)
        trial_id = obj.get("trial_id")
        if trial_id is None:
            continue
        trial = trials.setdefault(trial_id, {"attrs": {}, "state": None})
        if obj.get("op_code") == 8 and "user_attr" in obj:
            trial["attrs"].update(obj["user_attr"])
        elif obj.get("op_code") == 6:
            trial["state"] = obj.get("state")

    completed = [
        trial["attrs"]
        for trial in trials.values()
        if trial["state"] == 1 and "refusals" in trial["attrs"]
    ]
    if not completed:
        raise ValueError(f"No completed trials found in {path}")

    completed.sort(
        key=lambda attrs: (
            attrs.get("refusals", 10**9),
            attrs.get("overrefusals", 10**9),
            attrs.get("kl_divergence", 10**9),
        )
    )
    return completed[0]


def load_heretic_best(path: Path) -> dict[str, Any]:
    if path.name == "batch_summary.json":
        summary = json.loads(path.read_text())
        trials = summary.get("pareto_trials", [])
        if not trials:
            raise ValueError(f"No pareto trials found in {path}")
        return trials[0]

    return load_best_from_study(path)


def format_float(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def main() -> None:
    args = parse_args()
    rows = []

    for spec in args.spec:
        label, icon_path_str, her_path_str = spec.split("|", 2)
        icon_path = Path(icon_path_str)
        her_path = Path(her_path_str)
        icon_best = load_iconoclast_best(icon_path)
        her_best = load_heretic_best(her_path)
        rows.append(
            {
                "label": label,
                "iconoclast": {
                    "refusals": icon_best.get("refusals"),
                    "overrefusals": icon_best.get("overrefusals", 0),
                    "kl_divergence": icon_best.get("kl_divergence"),
                    "harmful_marker_hits": icon_best.get("harmful_marker_hits"),
                    "harmful_compliance_score": icon_best.get(
                        "harmful_compliance_score"
                    ),
                    "trial_index": icon_best.get("index"),
                },
                "heretic": {
                    "refusals": her_best.get("refusals"),
                    "overrefusals": her_best.get("overrefusals", 0),
                    "kl_divergence": her_best.get("kl_divergence"),
                    "trial_index": her_best.get("index"),
                },
            }
        )

    if args.format == "json":
        print(json.dumps(rows, indent=2))
        return

    print(
        "| Model | Iconoclast Refusals | Iconoclast Overrefusals | Iconoclast KL | Heretic Refusals | Heretic Overrefusals | Heretic KL | Verdict |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        icon = row["iconoclast"]
        her = row["heretic"]
        verdict = (
            "Iconoclast"
            if (
                (icon["refusals"], icon["overrefusals"], icon["kl_divergence"])
                < (her["refusals"], her["overrefusals"], her["kl_divergence"])
            )
            else "Heretic"
        )
        print(
            "| "
            + " | ".join(
                [
                    row["label"],
                    str(icon["refusals"]),
                    str(icon["overrefusals"]),
                    format_float(icon["kl_divergence"]),
                    str(her["refusals"]),
                    str(her["overrefusals"]),
                    format_float(her["kl_divergence"]),
                    verdict,
                ]
            )
            + " |"
        )


if __name__ == "__main__":
    main()
