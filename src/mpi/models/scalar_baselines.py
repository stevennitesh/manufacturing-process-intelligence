# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Leakage-safe scalar benchmarks for Dataset 2 part weight."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Final, Literal, cast

import numpy as np
import polars as pl
from sklearn.base import RegressorMixin
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from mpi.data.canonical import ManufacturingBundle
from mpi.datasets.injection_molding_protocol import EXPECTED_EXPERIMENTS, SCALAR_PREDICTOR_COLUMNS

RIDGE_ALPHAS: Final = (0.1, 1.0, 10.0, 100.0, 1000.0)
PLS_COMPONENTS: Final = (1, 2, 4, 8)
MODEL_ORDER: Final = ("mean", "ridge", "pls")
DEFAULT_BASELINE_OUTPUT: Final = Path("artifacts/m04")
EXPECTED_FOLDS: Final = (
    ("primary", "holdout_experiment_15"),
    ("primary", "holdout_experiment_20"),
    ("primary", "holdout_experiment_23"),
    ("secondary_id", "within_experiment"),
)

ModelName = Literal["mean", "ridge", "pls"]


@dataclass(frozen=True)
class BaselineResults:
    """In-memory results ready for inspection or persistence."""

    predictions: pl.DataFrame
    metrics: pl.DataFrame
    selections: tuple[dict[str, object], ...]


def assemble_model_rows(bundle: ManufacturingBundle, memberships: pl.DataFrame) -> pl.DataFrame:
    """Join model inputs by unit identity before selecting numeric arrays."""
    features = bundle.process_features.select("unit_id", *SCALAR_PREDICTOR_COLUMNS)
    weight_rows = bundle.quality.filter(pl.col("characteristic") == "weight")
    if weight_rows["measurement_unit"].unique().to_list() != ["g"]:
        raise ValueError("M4 target must be weight measured in grams")
    targets = weight_rows.select("unit_id", pl.col("measured_value").alias("weight_g"))
    if features["unit_id"].n_unique() != features.height:
        raise ValueError("scalar features must contain exactly one row per unit_id")
    if targets.height != bundle.units.height or targets["unit_id"].n_unique() != targets.height:
        raise ValueError("weight target must contain exactly one row per unit_id")
    if targets["weight_g"].null_count() or features.null_count().sum_horizontal().item():
        raise ValueError("M4 scalar predictors and weight targets must be complete")

    source_hashes = memberships["source_archive_sha256"].unique().to_list()
    source_versions = memberships["source_version"].unique().to_list()
    if source_hashes != [bundle.metadata.archive_sha256] or source_versions != [
        bundle.metadata.source_version
    ]:
        raise ValueError("membership source identity does not match the prepared bundle")
    observed_folds = tuple(
        memberships.select("protocol", "fold").unique().sort("protocol", "fold").iter_rows()
    )
    if observed_folds != EXPECTED_FOLDS:
        raise ValueError(f"expected M3 protocol/folds {EXPECTED_FOLDS}, observed {observed_folds}")
    if memberships.select("protocol", "fold", "unit_id").n_unique() != memberships.height:
        raise ValueError("memberships must contain one row per protocol/fold/unit")
    if set(memberships["role"].unique()) != {"fit_tune", "calibration", "test"}:
        raise ValueError("memberships must retain fit/tune, calibration and test roles")
    for held_out in EXPECTED_EXPERIMENTS:
        primary_fit_tune = memberships.filter(
            (pl.col("protocol") == "primary")
            & (pl.col("fold") == f"holdout_experiment_{held_out}")
            & (pl.col("role") == "fit_tune")
        )
        development_experiments = set(EXPECTED_EXPERIMENTS) - {held_out}
        if (
            set(primary_fit_tune["experiment_id"]) != development_experiments
            or set(primary_fit_tune["inner_fold"]) != development_experiments
            or primary_fit_tune.filter(pl.col("inner_fold") != pl.col("experiment_id")).height
        ):
            raise ValueError(
                "primary fit/tune inner folds must identify the two development experiments; "
                "regenerate the M3 memberships"
            )

    rows = memberships.join(features, on="unit_id", how="inner", validate="m:1").join(
        targets, on="unit_id", how="inner", validate="m:1"
    )
    if rows.height != memberships.height:
        raise ValueError("every membership must match exactly one feature row and weight target")
    return rows


def _pipeline(model: ModelName, candidate: float | int) -> Pipeline:
    estimator: RegressorMixin
    if model == "ridge":
        estimator = Ridge(alpha=float(candidate), fit_intercept=True)
    elif model == "pls":
        estimator = PLSRegression(n_components=int(candidate), scale=False)
    else:
        raise ValueError(f"mean has no fitted pipeline: {model}")
    return Pipeline([("scale", StandardScaler()), ("model", estimator)])


def _arrays(rows: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    return _predictors(rows), rows["weight_g"].to_numpy()


def _predictors(rows: pl.DataFrame) -> np.ndarray:
    return rows.select(SCALAR_PREDICTOR_COLUMNS).to_numpy()


def _mae(observed: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(observed - predicted)))


def _fit_and_predict(
    model: ModelName, candidate: float | int, train: pl.DataFrame, evaluation: pl.DataFrame
) -> np.ndarray:
    train_x, train_y = _arrays(train)
    fitted = _pipeline(model, candidate).fit(train_x, train_y)
    return np.asarray(fitted.predict(_predictors(evaluation)), dtype=np.float64).reshape(-1)


def _select_candidate(
    model: ModelName, fit_tune: pl.DataFrame
) -> tuple[float | int, list[dict[str, object]]]:
    candidates: tuple[float | int, ...]
    if model == "ridge":
        candidates = RIDGE_ALPHAS
    elif model == "pls":
        candidates = PLS_COMPONENTS
    else:
        raise ValueError(f"mean has no candidate selection: {model}")

    inner_folds = sorted(fit_tune["inner_fold"].drop_nulls().unique().to_list())
    if len(inner_folds) < 2 or fit_tune["inner_fold"].null_count():
        raise ValueError("fit/tune rows require at least two complete inner folds")
    scores: list[dict[str, object]] = []
    best_candidate = candidates[0]
    best_score = float("inf")
    for candidate in candidates:
        fold_scores: list[dict[str, object]] = []
        for inner_fold in inner_folds:
            inner_train = fit_tune.filter(pl.col("inner_fold") != inner_fold)
            inner_validation = fit_tune.filter(pl.col("inner_fold") == inner_fold)
            predicted = _fit_and_predict(model, candidate, inner_train, inner_validation)
            fold_scores.append(
                {
                    "inner_fold": inner_fold,
                    "mae_g": _mae(inner_validation["weight_g"].to_numpy(), predicted),
                }
            )
        mean_mae = float(np.mean([cast(float, score["mae_g"]) for score in fold_scores]))
        scores.append(
            {
                "candidate": candidate,
                "inner_fold_scores": fold_scores,
                "mean_inner_mae_g": mean_mae,
            }
        )
        if mean_mae < best_score:
            best_candidate, best_score = candidate, mean_mae
    return best_candidate, scores


def _metric_row(
    protocol: str,
    fold: str,
    model: ModelName,
    selected_parameter: float | int | None,
    observed: np.ndarray,
    predicted: np.ndarray,
) -> dict[str, object]:
    errors = observed - predicted
    denominator = float(np.sum(np.square(observed - np.mean(observed))))
    r2 = 1.0 - float(np.sum(np.square(errors))) / denominator if denominator > 0 else None
    return {
        "protocol": protocol,
        "fold": fold,
        "model": model,
        "selected_parameter": selected_parameter,
        "evaluation_count": len(observed),
        "mae_g": _mae(observed, predicted),
        "rmse_g": float(np.sqrt(np.mean(np.square(errors)))),
        "r2": r2,
    }


def run_scalar_baselines(bundle: ManufacturingBundle, memberships: pl.DataFrame) -> BaselineResults:
    """Run Mean, Ridge and PLS for every M3 protocol/fold."""
    rows = assemble_model_rows(bundle, memberships)
    prediction_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    selections: list[dict[str, object]] = []
    fold_keys = rows.select("protocol", "fold").unique().sort("protocol", "fold")
    for protocol, fold in fold_keys.iter_rows():
        fold_rows = rows.filter((pl.col("protocol") == protocol) & (pl.col("fold") == fold))
        if set(fold_rows["role"]) != {"fit_tune", "calibration", "test"}:
            raise ValueError(f"fold {protocol}/{fold} must retain all three M3 roles")
        fit_tune = fold_rows.filter(pl.col("role") == "fit_tune").sort("unit_id")
        evaluation = fold_rows.filter(pl.col("role") == "test").sort("unit_id")
        if not fit_tune.height or not evaluation.height:
            raise ValueError(f"fold {protocol}/{fold} lacks fit/tune or evaluation rows")
        observed = evaluation["weight_g"].to_numpy()
        for model in MODEL_ORDER:
            selected_parameter: float | int | None = None
            inner_scores: list[dict[str, object]] = []
            if model == "mean":
                fit_mean = fit_tune["weight_g"].mean()
                if fit_mean is None:
                    raise ValueError(f"fold {protocol}/{fold} has no fit/tune target mean")
                predicted = np.full(evaluation.height, cast(float, fit_mean))
            else:
                selected_parameter, inner_scores = _select_candidate(model, fit_tune)
                predicted = _fit_and_predict(model, selected_parameter, fit_tune, evaluation)
            selections.append(
                {
                    "protocol": protocol,
                    "fold": fold,
                    "model": model,
                    "selected_parameter": selected_parameter,
                    "candidate_scores": inner_scores,
                }
            )
            metric_rows.append(
                _metric_row(protocol, fold, model, selected_parameter, observed, predicted)
            )
            for unit_id, experiment_id, cycle_counter, actual, estimate in zip(
                evaluation["unit_id"],
                evaluation["experiment_id"],
                evaluation["cycle_counter"],
                observed,
                predicted,
                strict=True,
            ):
                prediction_rows.append(
                    {
                        "unit_id": unit_id,
                        "protocol": protocol,
                        "fold": fold,
                        "model": model,
                        "experiment_id": experiment_id,
                        "cycle_counter": cycle_counter,
                        "observed_weight_g": actual,
                        "predicted_weight_g": estimate,
                    }
                )
    return BaselineResults(
        predictions=pl.DataFrame(prediction_rows).sort("protocol", "fold", "model", "unit_id"),
        metrics=pl.DataFrame(metric_rows).sort("protocol", "fold", "model"),
        selections=tuple(selections),
    )


def _summaries(metrics: pl.DataFrame, predictions: pl.DataFrame) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for model in MODEL_ORDER:
        primary_metrics = metrics.filter(
            (pl.col("protocol") == "primary") & (pl.col("model") == model)
        )
        primary_predictions = predictions.filter(
            (pl.col("protocol") == "primary") & (pl.col("model") == model)
        )
        pooled_mae = _mae(
            primary_predictions["observed_weight_g"].to_numpy(),
            primary_predictions["predicted_weight_g"].to_numpy(),
        )
        equal_fold_mean = primary_metrics["mae_g"].mean()
        if equal_fold_mean is None:
            raise ValueError(f"model {model} has no primary fold metrics")
        summaries.append(
            {
                "model": model,
                "primary_equal_fold_mean_mae_g": cast(float, equal_fold_mean),
                "primary_pooled_sample_weighted_mae_g": pooled_mae,
            }
        )
    return summaries


def prediction_diagnostics(predictions: pl.DataFrame) -> list[dict[str, object]]:
    """Post-hoc per-experiment metrics; never used for fitting or model selection."""
    diagnostics: list[dict[str, object]] = []
    for (protocol, fold, model, experiment), rows in predictions.partition_by(
        ["protocol", "fold", "model", "experiment_id"], as_dict=True
    ).items():
        observed = rows["observed_weight_g"].to_numpy()
        predicted = rows["predicted_weight_g"].to_numpy()
        metric = _metric_row(protocol, fold, model, None, observed, predicted)
        metric.pop("selected_parameter")
        metric.update(
            experiment_id=experiment,
            mean_signed_error_g=float(np.mean(predicted - observed)),
        )
        diagnostics.append(metric)
    return sorted(
        diagnostics,
        key=lambda row: tuple(str(row[k]) for k in ("protocol", "fold", "model", "experiment_id")),
    )


def write_scalar_baseline_results(
    results: BaselineResults,
    bundle: ManufacturingBundle,
    memberships_path: Path,
    output: Path = DEFAULT_BASELINE_OUTPUT,
) -> dict[str, object]:
    """Write predictions, metrics and a concise reproducibility record."""
    output.mkdir(parents=True, exist_ok=True)
    record: dict[str, object] = {
        "dataset": bundle.metadata.dataset,
        "source_version": bundle.metadata.source_version,
        "source_archive_sha256": bundle.metadata.archive_sha256,
        "membership_reference": str(memberships_path),
        "membership_sha256": sha256(memberships_path.read_bytes()).hexdigest(),
        "membership_rows": pl.scan_parquet(memberships_path).select(pl.len()).collect().item(),
        "features": list(SCALAR_PREDICTOR_COLUMNS),
        "target": "weight_g",
        "ridge_alphas": list(RIDGE_ALPHAS),
        "pls_components": list(PLS_COMPONENTS),
        "selection_metric": "equal-weight mean inner-validation MAE in grams",
        "selections": list(results.selections),
        "summaries": _summaries(results.metrics, results.predictions),
        "posthoc_diagnostics": prediction_diagnostics(results.predictions),
        "package_versions": {
            "python": platform.python_version(),
            "numpy": version("numpy"),
            "polars": version("polars"),
            "scikit-learn": version("scikit-learn"),
        },
    }
    files: tuple[tuple[str, object], ...] = (
        ("predictions.parquet", results.predictions),
        ("metrics.parquet", results.metrics),
        ("run.json", record),
    )
    for filename, value in files:
        destination = output / filename
        temporary = output / f".{filename}.tmp"
        try:
            if isinstance(value, pl.DataFrame):
                value.write_parquet(temporary)
            else:
                temporary.write_text(
                    json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
            os.replace(temporary, destination)
        except (OSError, pl.exceptions.PolarsError):
            temporary.unlink(missing_ok=True)
            raise
    return record
