# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Bounded, leakage-safe M6 LightGBM representation comparison."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from itertools import product
from pathlib import Path
from typing import Final, cast

import numpy as np
import polars as pl
from lightgbm import LGBMRegressor

from mpi.data.canonical import ManufacturingBundle
from mpi.models.scalar_baselines import EXPECTED_FOLDS
from mpi.models.trajectory_representations import (
    CHANNELS,
    COMPONENT_COUNTS,
    REPRESENTATION_ORDER,
    SEGMENTS,
    SUMMARY_NAMES,
    Representation,
    TrajectoryData,
    assemble_trajectory_data,
    prepare_representation,
    regression_metrics,
    representation_group_metrics,
    trajectory_arrays,
)

NUM_LEAVES: Final = (7, 15)
MIN_CHILD_SAMPLES: Final = (10, 30)
N_ESTIMATORS: Final = (100, 300)
DEFAULT_LIGHTGBM_OUTPUT: Final = Path("artifacts/m06")


@dataclass(frozen=True)
class LightGBMSetting:
    """One pre-specified LightGBM search setting."""

    num_leaves: int
    min_child_samples: int
    n_estimators: int


@dataclass(frozen=True)
class LightGBMResults:
    """In-memory M6 results ready for inspection or persistence."""

    predictions: pl.DataFrame
    metrics: pl.DataFrame
    selections: tuple[dict[str, object], ...]


def candidate_grid(
    representation: Representation,
) -> tuple[tuple[int | None, LightGBMSetting], ...]:
    """Return the fixed grid in its pre-specified exact-tie selection order."""
    components: tuple[int | None, ...] = (
        (None,) if representation in ("A", "B") else COMPONENT_COUNTS
    )
    return tuple((count, setting) for count in components for setting in _search_settings())


def _search_settings() -> tuple[LightGBMSetting, ...]:
    return tuple(
        LightGBMSetting(leaves, child_samples, estimators)
        for leaves, child_samples, estimators in product(
            NUM_LEAVES, MIN_CHILD_SAMPLES, N_ESTIMATORS
        )
    )


def make_estimator(setting: LightGBMSetting) -> LGBMRegressor:
    """Construct the fixed deterministic CPU estimator for one search setting."""
    return LGBMRegressor(
        objective="regression",
        boosting_type="gbdt",
        learning_rate=0.05,
        max_depth=-1,
        reg_alpha=0.0,
        reg_lambda=1.0,
        num_leaves=setting.num_leaves,
        min_child_samples=setting.min_child_samples,
        n_estimators=setting.n_estimators,
        subsample=1.0,
        subsample_freq=0,
        colsample_bytree=1.0,
        random_state=42,
        n_jobs=1,
        deterministic=True,
        force_col_wise=True,
    )


def _predict(
    setting: LightGBMSetting, prepared: tuple[np.ndarray, np.ndarray, np.ndarray]
) -> np.ndarray:
    train_x, train_y, evaluation_x = prepared
    fitted = make_estimator(setting).fit(train_x, train_y)
    return np.asarray(fitted.predict(evaluation_x), dtype=np.float64)


def fit_predict_lightgbm(
    representation: Representation,
    components: int | None,
    setting: LightGBMSetting,
    train: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    evaluation: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> np.ndarray:
    """Prepare one representation train-locally, fit LightGBM, and predict."""
    return _predict(setting, prepare_representation(representation, components, train, evaluation))


def select_lightgbm_candidate(
    representation: Representation, data: TrajectoryData, fit_tune: pl.DataFrame
) -> tuple[int | None, LightGBMSetting, list[dict[str, object]]]:
    """Select by equal-weight mean group-aware inner-fold MAE; first exact tie wins."""
    inner_folds = sorted(fit_tune["inner_fold"].drop_nulls().unique().to_list())
    if len(inner_folds) < 2 or fit_tune["inner_fold"].null_count():
        raise ValueError("fit/tune rows require at least two complete inner folds")

    scores: list[dict[str, object]] = []
    candidates = candidate_grid(representation)
    best = candidates[0]
    best_score = float("inf")
    prepared_by_components: dict[
        int | None, list[tuple[object, tuple[np.ndarray, np.ndarray, np.ndarray], np.ndarray]]
    ] = {}
    for components, _ in candidates:
        if components in prepared_by_components:
            continue
        prepared_folds: list[
            tuple[object, tuple[np.ndarray, np.ndarray, np.ndarray], np.ndarray]
        ] = []
        for inner_fold in inner_folds:
            train_rows = fit_tune.filter(pl.col("inner_fold") != inner_fold).sort("unit_id")
            validation_rows = fit_tune.filter(pl.col("inner_fold") == inner_fold).sort("unit_id")
            validation = trajectory_arrays(data, validation_rows)
            prepared_folds.append(
                (
                    inner_fold,
                    prepare_representation(
                        representation,
                        components,
                        trajectory_arrays(data, train_rows),
                        validation,
                    ),
                    validation[3],
                )
            )
        prepared_by_components[components] = prepared_folds

    for components, setting in candidates:
        fold_scores: list[dict[str, object]] = []
        for inner_fold, prepared, observed in prepared_by_components[components]:
            predicted = _predict(setting, prepared)
            fold_scores.append(
                {
                    "inner_fold": inner_fold,
                    "mae_g": float(np.mean(np.abs(observed - predicted))),
                }
            )
        mean_mae = float(np.mean([cast(float, row["mae_g"]) for row in fold_scores]))
        scores.append(
            {
                "components": components,
                "num_leaves": setting.num_leaves,
                "min_child_samples": setting.min_child_samples,
                "n_estimators": setting.n_estimators,
                "inner_fold_scores": fold_scores,
                "mean_inner_mae_g": mean_mae,
            }
        )
        if mean_mae < best_score:
            best, best_score = (components, setting), mean_mae
    return best[0], best[1], scores


def run_lightgbm_comparison(
    bundle: ManufacturingBundle, memberships: pl.DataFrame
) -> LightGBMResults:
    """Evaluate the four exact M5 representations with fixed-grid LightGBM."""
    data, rows = assemble_trajectory_data(bundle, memberships)
    predictions: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    selections: list[dict[str, object]] = []
    for protocol, fold in EXPECTED_FOLDS:
        fold_rows = rows.filter((pl.col("protocol") == protocol) & (pl.col("fold") == fold))
        fit_tune = fold_rows.filter(pl.col("role") == "fit_tune").sort("unit_id")
        evaluation = fold_rows.filter(pl.col("role") == "test").sort("unit_id")
        observed = trajectory_arrays(data, evaluation)[3]
        fold_maes: dict[str, float] = {}
        pending_metrics: list[dict[str, object]] = []
        for representation in REPRESENTATION_ORDER:
            components, setting, scores = select_lightgbm_candidate(representation, data, fit_tune)
            predicted = fit_predict_lightgbm(
                representation,
                components,
                setting,
                trajectory_arrays(data, fit_tune),
                trajectory_arrays(data, evaluation),
            )
            mae, rmse, r2 = regression_metrics(observed, predicted)
            fold_maes[representation] = mae
            pending_metrics.append(
                {
                    "protocol": protocol,
                    "fold": fold,
                    "representation": representation,
                    "selected_components": components,
                    "selected_num_leaves": setting.num_leaves,
                    "selected_min_child_samples": setting.min_child_samples,
                    "selected_n_estimators": setting.n_estimators,
                    "evaluation_count": evaluation.height,
                    "mae_g": mae,
                    "rmse_g": rmse,
                    "r2": r2,
                }
            )
            selections.append(
                {
                    "protocol": protocol,
                    "fold": fold,
                    "representation": representation,
                    "selected_components": components,
                    "selected_setting": {
                        "num_leaves": setting.num_leaves,
                        "min_child_samples": setting.min_child_samples,
                        "n_estimators": setting.n_estimators,
                    },
                    "candidate_scores": scores,
                }
            )
            for unit_id, experiment_id, cycle_counter, actual, estimate in zip(
                evaluation["unit_id"],
                evaluation["experiment_id"],
                evaluation["cycle_counter"],
                observed,
                predicted,
                strict=True,
            ):
                predictions.append(
                    {
                        "unit_id": unit_id,
                        "protocol": protocol,
                        "fold": fold,
                        "representation": representation,
                        "experiment_id": experiment_id,
                        "cycle_counter": cycle_counter,
                        "observed_weight_g": actual,
                        "predicted_weight_g": estimate,
                    }
                )
        for row in pending_metrics:
            row["delta_mae_vs_a_g"] = fold_maes["A"] - cast(float, row["mae_g"])
            metrics.append(row)
    return LightGBMResults(
        predictions=pl.DataFrame(predictions).sort("protocol", "fold", "representation", "unit_id"),
        metrics=pl.DataFrame(metrics).sort("protocol", "fold", "representation"),
        selections=tuple(selections),
    )


def _summaries(results: LightGBMResults) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for representation in REPRESENTATION_ORDER:
        primary_metrics = results.metrics.filter(
            (pl.col("protocol") == "primary") & (pl.col("representation") == representation)
        )
        primary_predictions = results.predictions.filter(
            (pl.col("protocol") == "primary") & (pl.col("representation") == representation)
        )
        secondary = results.metrics.filter(
            (pl.col("protocol") == "secondary_id") & (pl.col("representation") == representation)
        ).row(0, named=True)
        summaries.append(
            {
                "representation": representation,
                "primary_equal_fold_mean_mae_g": cast(float, primary_metrics["mae_g"].mean()),
                "primary_pooled_sample_weighted_mae_g": float(
                    np.mean(
                        np.abs(
                            primary_predictions["observed_weight_g"].to_numpy()
                            - primary_predictions["predicted_weight_g"].to_numpy()
                        )
                    )
                ),
                "primary_equal_fold_delta_mae_vs_a_g": 0.0,
                "secondary_id_pooled": {
                    key: secondary[key] for key in ("evaluation_count", "mae_g", "rmse_g", "r2")
                },
            }
        )
    baseline = cast(float, summaries[0]["primary_equal_fold_mean_mae_g"])
    for summary in summaries:
        summary["primary_equal_fold_delta_mae_vs_a_g"] = baseline - cast(
            float, summary["primary_equal_fold_mean_mae_g"]
        )
    return summaries


def write_lightgbm_results(
    results: LightGBMResults,
    bundle: ManufacturingBundle,
    memberships_path: Path,
    output: Path = DEFAULT_LIGHTGBM_OUTPUT,
) -> dict[str, object]:
    """Atomically write M6 predictions, all 16 metrics, and run record."""
    record: dict[str, object] = {
        "dataset": bundle.metadata.dataset,
        "source_version": bundle.metadata.source_version,
        "source_archive_sha256": bundle.metadata.archive_sha256,
        "membership_reference": str(memberships_path),
        "membership_sha256": sha256(memberships_path.read_bytes()).hexdigest(),
        "membership_rows": pl.scan_parquet(memberships_path).select(pl.len()).collect().item(),
        "feature_definition_reference": (
            "docs/milestones/m05-trajectory-representations.md#exact-representations"
        ),
        "representations": list(REPRESENTATION_ORDER),
        "trajectory_samples_per_channel": 2048,
        "trajectory_column_order": "2,048 pressure samples then 2,048 flow samples",
        "engineered_summary_order_per_channel": list(SUMMARY_NAMES),
        "engineered_channel_order": list(CHANNELS),
        "summary_segment_seconds": [list(item) for item in SEGMENTS],
        "component_counts": list(COMPONENT_COUNTS),
        "fixed_search": {
            "num_leaves": list(NUM_LEAVES),
            "min_child_samples": list(MIN_CHILD_SAMPLES),
            "n_estimators": list(N_ESTIMATORS),
        },
        "candidate_order": (
            "ascending components, then num_leaves, min_child_samples, n_estimators; "
            "A/B omit components"
        ),
        "selection_metric": "equal-weight mean inner-validation MAE in grams",
        "estimator_effective_parameters": [
            make_estimator(setting).get_params() for setting in _search_settings()
        ],
        "preprocessing": (
            "Exact M5 path: all scalers and PCA/PLS fits use inner-training rows only during "
            "selection, then all fit/tune rows for refit. C standardizes trajectory columns, "
            "fits full-SVD PCA or supervised PLS with scale=False, appends scores to scalars, "
            "and standardizes the combined matrix. A/B standardize their full matrices."
        ),
        "selections": list(results.selections),
        "summaries": _summaries(results),
        "per_experiment_metrics": representation_group_metrics(results.predictions),
        "limitations": [
            (
                "M2 explored all three experiments; primary folds are grouped cross-validation, "
                "not an untouched prospective test."
            ),
            "Only three experiments and the small fixed searches limit conclusions.",
            (
                "Improvement reflects the tested features/model combination; lack of improvement "
                "cannot distinguish concept shift, missing context, or representation failure."
            ),
            "ID-only improvement does not prove that features merely encode regime identity.",
            "Outer metrics do not select a global winner or authorize another search.",
        ],
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
        ("predictions.parquet", results.predictions),
        ("metrics.parquet", results.metrics),
        ("run.json", record),
    ):
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
