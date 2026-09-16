# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
"""M9 post-hoc permutation importance and marginal feature-support diagnostics."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Any, Final, cast

import numpy as np
import polars as pl
from sklearn.inspection import permutation_importance

from mpi.data.canonical import ManufacturingBundle
from mpi.datasets.injection_molding_protocol import SCALAR_PREDICTOR_COLUMNS
from mpi.models.scalar_baselines import EXPECTED_FOLDS, assemble_model_rows
from mpi.models.uncertainty_shift import (
    fit_scalar_candidate,
    predict_scalar_candidate,
    scalar_candidate_from_record,
)

DEFAULT_EXPLANATION_OUTPUT: Final = Path("artifacts/m09")
DEFAULT_M7_RUN: Final = Path("artifacts/m07/run.json")
DEFAULT_M7_PREDICTIONS: Final = Path("artifacts/m07/evaluation_predictions.parquet")
PERMUTATION_SEED: Final = 42
PERMUTATION_REPEATS: Final = 10
PREDICTION_TOLERANCE: Final = 1e-10


@dataclass(frozen=True)
class ExplanationResults:
    """Bounded M9 tables and population-level reproduction evidence."""

    permutation_importance: pl.DataFrame
    feature_support: pl.DataFrame
    populations: tuple[dict[str, object], ...]
    maximum_prediction_difference_g: float


def _selected_candidates(run_record: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
    if run_record.get("features") != list(SCALAR_PREDICTOR_COLUMNS):
        raise ValueError("M7 feature list does not match the current scalar allowlist")
    raw_selections = run_record.get("selections")
    if not isinstance(raw_selections, list):
        raise ValueError("M7 run record lacks selections")
    selections: dict[tuple[str, str], dict[str, object]] = {}
    for raw in raw_selections:
        if not isinstance(raw, dict):
            raise ValueError("M7 selections must be records")
        protocol, fold, selected = (
            raw.get("protocol"),
            raw.get("fold"),
            raw.get("selected_candidate"),
        )
        if (
            not isinstance(protocol, str)
            or not isinstance(fold, str)
            or not isinstance(selected, dict)
        ):
            raise ValueError("M7 selection lacks protocol, fold or selected candidate")
        selections[(protocol, fold)] = cast(dict[str, object], selected)
    if tuple(sorted(selections)) != EXPECTED_FOLDS:
        raise ValueError(
            f"expected M7 selections for {EXPECTED_FOLDS}, observed {tuple(sorted(selections))}"
        )
    return selections


def _verify_run_identity(
    bundle: ManufacturingBundle,
    memberships: pl.DataFrame,
    run_record: dict[str, object],
    membership_sha256: str | None,
) -> None:
    if (
        run_record.get("dataset") != bundle.metadata.dataset
        or run_record.get("source_version") != bundle.metadata.source_version
        or run_record.get("source_archive_sha256") != bundle.metadata.archive_sha256
    ):
        raise ValueError("M7 source identity does not match the prepared bundle")
    if run_record.get("membership_rows") != memberships.height:
        raise ValueError("M7 membership row count does not match the supplied memberships")
    if membership_sha256 is not None and run_record.get("membership_sha256") != membership_sha256:
        raise ValueError("M7 membership identity does not match the supplied memberships")


def feature_support_rows(
    train: pl.DataFrame,
    evaluation: pl.DataFrame,
    population: dict[str, object],
) -> list[dict[str, object]]:
    """Calculate analytic marginal training support for one evaluation population."""
    records: list[dict[str, object]] = []
    for feature in SCALAR_PREDICTOR_COLUMNS:
        train_values = train[feature].to_numpy()
        evaluation_values = evaluation[feature].to_numpy()
        train_mean = float(np.mean(train_values))
        train_std = float(np.std(train_values, ddof=0))
        evaluation_mean = float(np.mean(evaluation_values))
        below = float(np.mean(evaluation_values < np.min(train_values)))
        above = float(np.mean(evaluation_values > np.max(train_values)))
        records.append(
            {
                **population,
                "feature": feature,
                "training_min": float(np.min(train_values)),
                "training_max": float(np.max(train_values)),
                "training_mean": train_mean,
                "training_std": train_std,
                "evaluation_mean": evaluation_mean,
                "fraction_below_training_range": below,
                "fraction_above_training_range": above,
                "fraction_outside_training_range": below + above,
                "standardized_mean_shift": (
                    None if train_std == 0.0 else (evaluation_mean - train_mean) / train_std
                ),
                "constant_training_feature": train_std == 0.0,
            }
        )
    return records


def permutation_importance_rows(
    fitted: Any,
    evaluation: pl.DataFrame,
    population: dict[str, object],
) -> list[dict[str, object]]:
    """Calculate fixed seeded permutation importance for one population."""
    result = cast(
        Any,
        permutation_importance(
            fitted,
            evaluation.select(SCALAR_PREDICTOR_COLUMNS).to_numpy(),
            evaluation["weight_g"].to_numpy(),
            scoring="neg_mean_absolute_error",
            n_repeats=PERMUTATION_REPEATS,
            random_state=PERMUTATION_SEED,
            n_jobs=1,
        ),
    )
    records: list[dict[str, object]] = []
    for index, feature in enumerate(SCALAR_PREDICTOR_COLUMNS):
        repeat_values = np.asarray(result.importances[index], dtype=np.float64)
        records.append(
            {
                **population,
                "feature": feature,
                "importance_mean_g": float(result.importances_mean[index]),
                "importance_std_g": float(result.importances_std[index]),
                "repeat_importance_g": repeat_values.tolist(),
            }
        )
    return records


def _reference_difference(
    protocol: str,
    fold: str,
    evaluation: pl.DataFrame,
    predicted: np.ndarray,
    reference_predictions: pl.DataFrame,
) -> float:
    actual = pl.DataFrame({"unit_id": evaluation["unit_id"], "refitted": predicted})
    reference = reference_predictions.filter(
        (pl.col("protocol") == protocol) & (pl.col("fold") == fold)
    ).select("unit_id", pl.col("predicted_weight_g").alias("saved"))
    compared = actual.join(reference, on="unit_id", how="inner", validate="1:1")
    if compared.height != actual.height or reference.height != actual.height:
        raise ValueError(f"M7 prediction identities do not match {protocol}/{fold}")
    difference = float(
        np.max(np.abs(compared["refitted"].to_numpy() - compared["saved"].to_numpy()))
    )
    if difference > PREDICTION_TOLERANCE:
        raise ValueError(
            f"refitted predictions differ from M7 for {protocol}/{fold}: {difference:.3g} g"
        )
    return difference


def run_predictive_explanation(
    bundle: ManufacturingBundle,
    memberships: pl.DataFrame,
    m7_run_record: dict[str, object],
    m7_predictions: pl.DataFrame,
    *,
    membership_sha256: str | None = None,
) -> ExplanationResults:
    """Refit the four saved M7 models once and explain six evaluation populations."""
    _verify_run_identity(bundle, memberships, m7_run_record, membership_sha256)
    selections = _selected_candidates(m7_run_record)
    rows = assemble_model_rows(bundle, memberships)
    importance_rows: list[dict[str, object]] = []
    support_rows: list[dict[str, object]] = []
    populations: list[dict[str, object]] = []
    maximum_difference = 0.0
    for protocol, fold in EXPECTED_FOLDS:
        fold_rows = rows.filter((pl.col("protocol") == protocol) & (pl.col("fold") == fold))
        train = fold_rows.filter(pl.col("role") == "fit_tune").sort("unit_id")
        evaluation = fold_rows.filter(pl.col("role") == "test").sort("unit_id")
        selected_record = selections[(protocol, fold)]
        candidate = scalar_candidate_from_record(selected_record)
        fitted = fit_scalar_candidate(candidate, train)
        fold_prediction = predict_scalar_candidate(fitted, evaluation)
        maximum_difference = max(
            maximum_difference,
            _reference_difference(protocol, fold, evaluation, fold_prediction, m7_predictions),
        )
        experiments = sorted(evaluation["experiment_id"].unique().to_list())
        if protocol == "primary" and len(experiments) != 1:
            raise ValueError(f"primary population {fold} must contain one experiment")
        for experiment in experiments:
            population_rows = evaluation.filter(pl.col("experiment_id") == experiment).sort(
                "unit_id"
            )
            predicted = predict_scalar_candidate(fitted, population_rows)
            baseline_mae = float(
                np.mean(np.abs(population_rows["weight_g"].to_numpy() - predicted))
            )
            population: dict[str, object] = {
                "protocol": protocol,
                "model_fold": fold,
                "evaluation_experiment_id": experiment,
                "model_family": selected_record["family"],
                "model_settings": json.dumps(
                    selected_record, sort_keys=True, separators=(",", ":")
                ),
                "training_count": train.height,
                "evaluation_count": population_rows.height,
                "baseline_mae_g": baseline_mae,
            }
            populations.append(population)
            importance_rows.extend(permutation_importance_rows(fitted, population_rows, population))
            support_population = {
                key: value for key, value in population.items() if key != "baseline_mae_g"
            }
            support_rows.extend(feature_support_rows(train, population_rows, support_population))
    importance = pl.DataFrame(importance_rows).sort(
        "protocol", "model_fold", "evaluation_experiment_id", "feature"
    )
    support = pl.DataFrame(support_rows).sort(
        "protocol", "model_fold", "evaluation_experiment_id", "feature"
    )
    if importance.height != 96 or support.height != 96 or len(populations) != 6:
        raise ValueError("M9 requires six populations and 96 rows in each explanation table")
    return ExplanationResults(importance, support, tuple(populations), maximum_difference)


def write_predictive_explanation(
    results: ExplanationResults,
    bundle: ManufacturingBundle,
    memberships_path: Path,
    m7_run_path: Path,
    m7_predictions_path: Path,
    output: Path = DEFAULT_EXPLANATION_OUTPUT,
) -> dict[str, object]:
    """Atomically write the two M9 tables and compact reproducibility record."""
    record: dict[str, object] = {
        "dataset": bundle.metadata.dataset,
        "source_version": bundle.metadata.source_version,
        "source_archive_sha256": bundle.metadata.archive_sha256,
        "membership_reference": str(memberships_path),
        "membership_sha256": sha256(memberships_path.read_bytes()).hexdigest(),
        "membership_rows": pl.scan_parquet(memberships_path).select(pl.len()).collect().item(),
        "m7_run_reference": str(m7_run_path),
        "m7_run_sha256": sha256(m7_run_path.read_bytes()).hexdigest(),
        "m7_prediction_reference": str(m7_predictions_path),
        "m7_prediction_sha256": sha256(m7_predictions_path.read_bytes()).hexdigest(),
        "features": list(SCALAR_PREDICTOR_COLUMNS),
        "target": "weight_g",
        "permutation": {
            "scoring": "neg_mean_absolute_error",
            "seed": PERMUTATION_SEED,
            "repeats": PERMUTATION_REPEATS,
            "n_jobs": 1,
        },
        "prediction_reproduction_tolerance_g": PREDICTION_TOLERANCE,
        "maximum_prediction_difference_g": results.maximum_prediction_difference_g,
        "populations": list(results.populations),
        "package_versions": {
            "python": platform.python_version(),
            "numpy": version("numpy"),
            "polars": version("polars"),
            "scikit-learn": version("scikit-learn"),
            "lightgbm": version("lightgbm"),
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    for filename, value in (
        ("permutation_importance.parquet", results.permutation_importance),
        ("feature_support.parquet", results.feature_support),
        ("run.json", record),
    ):
        destination = output / filename
        temporary = output / f".{filename}.tmp"
        try:
            if isinstance(value, pl.DataFrame):
                value.write_parquet(temporary)
            else:
                temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, destination)
        except (OSError, pl.exceptions.PolarsError):
            temporary.unlink(missing_ok=True)
            raise
    return record
