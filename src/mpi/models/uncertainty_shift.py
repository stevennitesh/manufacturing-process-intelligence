# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""M7 scalar split-conformal evaluation and development error-ranking screen."""

from __future__ import annotations

import json
import math
import os
import platform
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Final, Literal, cast

import numpy as np
import numpy.typing as npt
import polars as pl
from sklearn.base import RegressorMixin
from sklearn.cross_decomposition import PLSRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from mpi.data.canonical import ManufacturingBundle
from mpi.datasets.injection_molding_protocol import SCALAR_PREDICTOR_COLUMNS
from mpi.models.lightgbm_comparison import LightGBMSetting, candidate_grid, make_estimator
from mpi.models.scalar_baselines import EXPECTED_FOLDS, PLS_COMPONENTS, assemble_model_rows

ALPHA: Final = 0.10
N_NEIGHBORS: Final = 5
RETAINED_FRACTION: Final = 0.75
MIN_PRIMARY_REDUCTION: Final = 0.10
DEFAULT_UNCERTAINTY_OUTPUT: Final = Path("artifacts/m07")

Family = Literal["pls", "lightgbm"]


@dataclass(frozen=True)
class ScalarCandidate:
    """One candidate in the fixed exact-tie order."""

    family: Family
    components: int | None = None
    lightgbm_setting: LightGBMSetting | None = None


@dataclass(frozen=True)
class UncertaintyResults:
    """M7 outputs ready for inspection or persistence."""

    evaluation_predictions: pl.DataFrame
    development_predictions: pl.DataFrame
    calibration_predictions: pl.DataFrame
    metrics: pl.DataFrame
    selections: tuple[dict[str, object], ...]
    screens: tuple[dict[str, object], ...]
    gate_passed: bool


def scalar_candidates() -> tuple[ScalarCandidate, ...]:
    """Return four PLS then eight scalar LightGBM candidates."""
    pls = tuple(ScalarCandidate("pls", components=count) for count in PLS_COMPONENTS)
    lightgbm = tuple(
        ScalarCandidate("lightgbm", lightgbm_setting=setting)
        for components, setting in candidate_grid("A")
        if components is None
    )
    return pls + lightgbm


def _candidate_record(candidate: ScalarCandidate) -> dict[str, object]:
    if candidate.family == "pls":
        return {"family": "pls", "components": candidate.components}
    setting = candidate.lightgbm_setting
    if setting is None:
        raise ValueError("LightGBM candidate lacks settings")
    return {
        "family": "lightgbm",
        "num_leaves": setting.num_leaves,
        "min_child_samples": setting.min_child_samples,
        "n_estimators": setting.n_estimators,
    }


def scalar_candidate_from_record(record: dict[str, object]) -> ScalarCandidate:
    """Resolve one saved M7 selected-candidate record to the existing model definition."""
    for candidate in scalar_candidates():
        if _candidate_record(candidate) == record:
            return candidate
    raise ValueError(f"unknown M7 scalar candidate record: {record}")


def _pipeline(candidate: ScalarCandidate) -> Pipeline:
    estimator: RegressorMixin
    if candidate.family == "pls":
        if candidate.components is None:
            raise ValueError("PLS candidate lacks component count")
        estimator = PLSRegression(n_components=candidate.components, scale=False)
    else:
        if candidate.lightgbm_setting is None:
            raise ValueError("LightGBM candidate lacks settings")
        estimator = cast(RegressorMixin, make_estimator(candidate.lightgbm_setting))
    return Pipeline([("scale", StandardScaler()), ("model", estimator)])


def _x(rows: pl.DataFrame) -> np.ndarray:
    return rows.select(SCALAR_PREDICTOR_COLUMNS).to_numpy()


def _fit(candidate: ScalarCandidate, rows: pl.DataFrame) -> Pipeline:
    return _pipeline(candidate).fit(_x(rows), rows["weight_g"].to_numpy())


def fit_scalar_candidate(candidate: ScalarCandidate, rows: pl.DataFrame) -> Pipeline:
    """Refit a fixed M7 scalar candidate on supplied fit/tune rows."""
    return _fit(candidate, rows)


def _predict(fitted: Pipeline, rows: pl.DataFrame) -> np.ndarray:
    return np.asarray(fitted.predict(_x(rows)), dtype=np.float64).reshape(-1)


def predict_scalar_candidate(fitted: Pipeline, rows: pl.DataFrame) -> np.ndarray:
    """Predict with a fixed fitted M7 scalar pipeline."""
    return _predict(fitted, rows)


def conformal_radius(errors: np.ndarray, coverage: float = 0.90) -> tuple[float, int]:
    """Return the finite split-conformal order statistic without rank clipping."""
    values = np.asarray(errors, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("calibration errors must be a nonempty finite vector")
    if (values < 0).any():
        raise ValueError("calibration errors must be nonnegative")
    rank = math.ceil((len(values) + 1) * coverage)
    if rank > len(values):
        raise ValueError(
            f"insufficient calibration rows for finite {coverage:.0%} interval: "
            f"n={len(values)}, required rank={rank}"
        )
    return float(np.sort(values)[rank - 1]), rank


def mean_knn_distance(
    train_x: np.ndarray, query_x: np.ndarray, neighbors: int = N_NEIGHBORS
) -> np.ndarray:
    """Training-standardized mean Euclidean distance to the nearest training rows."""
    train = np.asarray(train_x, dtype=np.float64)
    query = np.asarray(query_x, dtype=np.float64)
    if train.ndim != 2 or query.ndim != 2 or train.shape[1] != query.shape[1]:
        raise ValueError("train/query features must be compatible two-dimensional arrays")
    if len(train) < neighbors:
        raise ValueError(f"distance score requires at least {neighbors} training rows")
    scaler = StandardScaler().fit(train)
    train_scaled: npt.NDArray[np.float64] = np.asarray(scaler.transform(train), dtype=np.float64)
    query_scaled: npt.NDArray[np.float64] = np.asarray(scaler.transform(query), dtype=np.float64)
    distances = np.sqrt(np.sum((query_scaled[:, None, :] - train_scaled[None, :, :]) ** 2, axis=2))
    return np.mean(np.partition(distances, neighbors - 1, axis=1)[:, :neighbors], axis=1)


def ranking_screen_block(
    unit_ids: list[str], distances: np.ndarray, absolute_errors: np.ndarray
) -> dict[str, object]:
    """Apply the fixed 75% retained development screen with identity tie-breaking."""
    if not (len(unit_ids) == len(distances) == len(absolute_errors)) or not unit_ids:
        raise ValueError("screen inputs must be equally sized and nonempty")
    retained_count = math.ceil(RETAINED_FRACTION * len(unit_ids))
    order = sorted(range(len(unit_ids)), key=lambda index: (distances[index], unit_ids[index]))
    retained = np.asarray(order[:retained_count])
    full_mae = float(np.mean(absolute_errors))
    retained_mae = float(np.mean(absolute_errors[retained]))
    reduction = None if full_mae == 0.0 else 1.0 - retained_mae / full_mae
    return {
        "development_count": len(unit_ids),
        "retained_count": retained_count,
        "full_mae_g": full_mae,
        "retained_mae_g": retained_mae,
        "relative_reduction": reduction,
        "passed": reduction is not None and reduction >= MIN_PRIMARY_REDUCTION,
    }


def _selection_and_development(
    protocol: str, fold: str, fit_tune: pl.DataFrame
) -> tuple[ScalarCandidate, dict[str, object], list[dict[str, object]], dict[str, object]]:
    inner_folds = sorted(fit_tune["inner_fold"].drop_nulls().unique().to_list())
    if len(inner_folds) < 2 or fit_tune["inner_fold"].null_count():
        raise ValueError("fit/tune rows require at least two complete inner folds")
    scored: list[tuple[ScalarCandidate, list[dict[str, object]], float]] = []
    for candidate in scalar_candidates():
        fold_scores: list[dict[str, object]] = []
        for inner_fold in inner_folds:
            train = fit_tune.filter(pl.col("inner_fold") != inner_fold).sort("unit_id")
            validation = fit_tune.filter(pl.col("inner_fold") == inner_fold).sort("unit_id")
            predicted = _predict(_fit(candidate, train), validation)
            mae = float(np.mean(np.abs(validation["weight_g"].to_numpy() - predicted)))
            fold_scores.append({"inner_fold": inner_fold, "mae_g": mae})
        scored.append(
            (candidate, fold_scores, float(np.mean([cast(float, x["mae_g"]) for x in fold_scores])))
        )
    selected, _, _ = min(scored, key=lambda item: item[2])
    development_rows: list[dict[str, object]] = []
    block_screens: list[dict[str, object]] = []
    for inner_fold in inner_folds:
        train = fit_tune.filter(pl.col("inner_fold") != inner_fold).sort("unit_id")
        validation = fit_tune.filter(pl.col("inner_fold") == inner_fold).sort("unit_id")
        predicted = _predict(_fit(selected, train), validation)
        errors = np.abs(validation["weight_g"].to_numpy() - predicted)
        distances = mean_knn_distance(_x(train), _x(validation))
        screen = ranking_screen_block(validation["unit_id"].to_list(), distances, errors)
        screen.update(inner_fold=inner_fold)
        block_screens.append(screen)
        for unit_id, experiment_id, actual, estimate, error, distance in zip(
            validation["unit_id"],
            validation["experiment_id"],
            validation["weight_g"],
            predicted,
            errors,
            distances,
            strict=True,
        ):
            development_rows.append(
                {
                    "unit_id": unit_id,
                    "protocol": protocol,
                    "fold": fold,
                    "inner_fold": inner_fold,
                    "experiment_id": experiment_id,
                    "observed_weight_g": actual,
                    "predicted_weight_g": estimate,
                    "absolute_error_g": error,
                    "distance": distance,
                }
            )
    reductions = [item["relative_reduction"] for item in block_screens]
    mean_reduction = (
        None
        if any(value is None for value in reductions)
        else float(np.mean([cast(float, value) for value in reductions]))
    )
    screen_summary: dict[str, object] = {
        "protocol": protocol,
        "fold": fold,
        "inner_blocks": block_screens,
        "mean_relative_reduction": mean_reduction,
        "passed": mean_reduction is not None and mean_reduction >= MIN_PRIMARY_REDUCTION,
    }
    selection: dict[str, object] = {
        "protocol": protocol,
        "fold": fold,
        "selected_candidate": _candidate_record(selected),
        "candidate_scores": [
            {
                **_candidate_record(candidate),
                "inner_fold_scores": fold_scores,
                "mean_inner_mae_g": mean_score,
            }
            for candidate, fold_scores, mean_score in scored
        ],
    }
    return selected, selection, development_rows, screen_summary


def _metrics(observed: np.ndarray, predicted: np.ndarray) -> tuple[float, float, float | None]:
    errors = observed - predicted
    denominator = float(np.sum((observed - np.mean(observed)) ** 2))
    r2 = None if denominator == 0.0 else 1.0 - float(np.sum(errors**2)) / denominator
    return float(np.mean(np.abs(errors))), float(np.sqrt(np.mean(errors**2))), r2


def interval_coverage(observed: np.ndarray, predicted: np.ndarray, radius: float) -> np.ndarray:
    """Return inclusive split-conformal interval membership."""
    actual = np.asarray(observed, dtype=np.float64)
    estimate = np.asarray(predicted, dtype=np.float64)
    return (actual >= estimate - radius) & (actual <= estimate + radius)


def _metric_row(protocol: str, fold: str, rows: pl.DataFrame) -> dict[str, object]:
    observed = rows["observed_weight_g"].to_numpy()
    predicted = rows["predicted_weight_g"].to_numpy()
    mae, rmse, r2 = _metrics(observed, predicted)
    covered = rows["covered"].to_numpy()
    widths = rows["interval_width_g"].to_numpy()
    return {
        "protocol": protocol,
        "fold": fold,
        "evaluation_count": rows.height,
        "nominal_coverage": 1.0 - ALPHA,
        "empirical_coverage": float(np.mean(covered)),
        "mean_width_g": float(np.mean(widths)),
        "median_width_g": float(np.median(widths)),
        "mae_g": mae,
        "rmse_g": rmse,
        "r2": r2,
    }


def run_uncertainty_shift(
    bundle: ManufacturingBundle, memberships: pl.DataFrame
) -> UncertaintyResults:
    """Run fixed development selection/gate, then calibration and evaluation."""
    rows = assemble_model_rows(bundle, memberships)
    evaluation_rows: list[dict[str, object]] = []
    development_rows: list[dict[str, object]] = []
    calibration_rows: list[dict[str, object]] = []
    selections: list[dict[str, object]] = []
    screens: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    prepared_folds: list[
        tuple[str, str, pl.DataFrame, pl.DataFrame, pl.DataFrame, ScalarCandidate]
    ] = []
    for protocol, fold in EXPECTED_FOLDS:
        fold_rows = rows.filter((pl.col("protocol") == protocol) & (pl.col("fold") == fold))
        fit_tune = fold_rows.filter(pl.col("role") == "fit_tune").sort("unit_id")
        calibration = fold_rows.filter(pl.col("role") == "calibration").sort("unit_id")
        evaluation = fold_rows.filter(pl.col("role") == "test").sort("unit_id")
        selected, selection, development, screen = _selection_and_development(
            protocol, fold, fit_tune
        )
        selections.append(selection)
        development_rows.extend(development)
        screens.append(screen)
        prepared_folds.append((protocol, fold, fit_tune, calibration, evaluation, selected))

    gate_passed = all(
        cast(bool, item["passed"]) for item in screens if item["protocol"] == "primary"
    )
    for protocol, fold, fit_tune, calibration, evaluation, selected in prepared_folds:
        selection = next(
            item for item in selections if item["protocol"] == protocol and item["fold"] == fold
        )
        fitted = _fit(selected, fit_tune)
        calibration_prediction = _predict(fitted, calibration)
        calibration_errors = np.abs(calibration["weight_g"].to_numpy() - calibration_prediction)
        radius, rank = conformal_radius(calibration_errors)
        for unit_id, actual, estimate, error in zip(
            calibration["unit_id"],
            calibration["weight_g"],
            calibration_prediction,
            calibration_errors,
            strict=True,
        ):
            calibration_rows.append(
                {
                    "unit_id": unit_id,
                    "protocol": protocol,
                    "fold": fold,
                    "observed_weight_g": actual,
                    "predicted_weight_g": estimate,
                    "absolute_error_g": error,
                }
            )
        selection.update(calibration_count=calibration.height, conformal_rank=rank, radius_g=radius)
        predicted = _predict(fitted, evaluation)
        distances = mean_knn_distance(_x(fit_tune), _x(evaluation))
        covered = interval_coverage(evaluation["weight_g"].to_numpy(), predicted, radius)
        for unit_id, experiment_id, cycle_counter, actual, estimate, distance, is_covered in zip(
            evaluation["unit_id"],
            evaluation["experiment_id"],
            evaluation["cycle_counter"],
            evaluation["weight_g"],
            predicted,
            distances,
            covered,
            strict=True,
        ):
            lower, upper = estimate - radius, estimate + radius
            evaluation_rows.append(
                {
                    "unit_id": unit_id,
                    "protocol": protocol,
                    "fold": fold,
                    "experiment_id": experiment_id,
                    "cycle_counter": cycle_counter,
                    "observed_weight_g": actual,
                    "predicted_weight_g": estimate,
                    "lower_g": lower,
                    "upper_g": upper,
                    "interval_width_g": 2.0 * radius,
                    "covered": is_covered,
                    "distance": distance,
                }
            )
    evaluation_frame = pl.DataFrame(evaluation_rows).sort("protocol", "fold", "unit_id")
    for protocol, fold in EXPECTED_FOLDS:
        subset = evaluation_frame.filter(
            (pl.col("protocol") == protocol) & (pl.col("fold") == fold)
        )
        metric_rows.append(_metric_row(protocol, fold, subset))
        if protocol == "secondary_id":
            for experiment in sorted(subset["experiment_id"].unique().to_list()):
                metric_rows.append(
                    _metric_row(
                        protocol,
                        f"experiment_{experiment}",
                        subset.filter(pl.col("experiment_id") == experiment),
                    )
                )
    return UncertaintyResults(
        evaluation_frame,
        pl.DataFrame(development_rows).sort("protocol", "fold", "inner_fold", "unit_id"),
        pl.DataFrame(calibration_rows).sort("protocol", "fold", "unit_id"),
        pl.DataFrame(metric_rows).sort("protocol", "fold"),
        tuple(selections),
        tuple(screens),
        gate_passed,
    )


def write_uncertainty_results(
    results: UncertaintyResults,
    bundle: ManufacturingBundle,
    memberships_path: Path,
    output: Path = DEFAULT_UNCERTAINTY_OUTPUT,
) -> dict[str, object]:
    """Write M7 evidence atomically in the repository's existing artifact style."""
    primary = results.metrics.filter(pl.col("protocol") == "primary")
    primary_predictions = results.evaluation_predictions.filter(pl.col("protocol") == "primary")
    record: dict[str, object] = {
        "dataset": bundle.metadata.dataset,
        "source_version": bundle.metadata.source_version,
        "source_archive_sha256": bundle.metadata.archive_sha256,
        "membership_reference": str(memberships_path),
        "membership_sha256": sha256(memberships_path.read_bytes()).hexdigest(),
        "membership_rows": pl.scan_parquet(memberships_path).select(pl.len()).collect().item(),
        "features": list(SCALAR_PREDICTOR_COLUMNS),
        "target": "weight_g",
        "candidate_order": [_candidate_record(candidate) for candidate in scalar_candidates()],
        "selection_metric": "equal-weight mean inner-validation MAE in grams",
        "nominal_coverage": 1.0 - ALPHA,
        "conformal_order_statistic": "ceil((n_cal + 1) * 0.90), one-based, no clipping",
        "distance_score": (
            "mean Euclidean distance to five nearest fit/tune rows after "
            "training-only StandardScaler"
        ),
        "development_screen": {
            "retained_fraction": RETAINED_FRACTION,
            "primary_fold_minimum_mean_relative_reduction": MIN_PRIMARY_REDUCTION,
            "selection_affected_optimistic_screen": True,
        },
        "selections": list(results.selections),
        "screens": list(results.screens),
        "m8_eligible": results.gate_passed,
        "primary_summaries": {
            "equal_fold_mean": {
                key: cast(float, primary[key].mean())
                for key in ("empirical_coverage", "mean_width_g", "mae_g", "rmse_g")
            },
            "pooled_sample_weighted": _metric_row("primary", "pooled", primary_predictions),
        },
        "limitations": [
            (
                "Experimental shift and adjacent-cycle dependence may violate exchangeability; "
                "coverage is measured, not guaranteed."
            ),
            (
                "ID and primary use different fitted pipelines and populations; comparison "
                "is descriptive, not paired or causal."
            ),
            "Interval width is constant within each fitted fold and cannot rank unusual cycles.",
            (
                "The selected-candidate development screen reuses validation labels and may "
                "be optimistic; overlapping folds are not independent replications."
            ),
            "Correlated temperature channels can dominate standardized Euclidean distance.",
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
        ("evaluation_predictions.parquet", results.evaluation_predictions),
        ("development_predictions.parquet", results.development_predictions),
        ("calibration_predictions.parquet", results.calibration_predictions),
        ("metrics.parquet", results.metrics),
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
