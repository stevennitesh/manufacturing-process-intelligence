# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Bounded, leakage-safe M5 trajectory representation comparison."""

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
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from mpi.data.canonical import ManufacturingBundle
from mpi.datasets.injection_molding_protocol import SCALAR_PREDICTOR_COLUMNS
from mpi.models.scalar_baselines import EXPECTED_FOLDS, RIDGE_ALPHAS, assemble_model_rows

COMPONENT_COUNTS: Final = (2, 4, 8)
REPRESENTATION_ORDER: Final = ("A", "B", "C-PCA", "C-PLS")
CHANNELS: Final = ("pressure", "flow")
SUMMARY_NAMES: Final = (
    "sample_mean",
    "population_std",
    "maximum",
    "time_of_first_maximum_seconds",
    "sample_quantile_0_10",
    "sample_quantile_0_50",
    "sample_quantile_0_90",
    "trapezoidal_auc_amplitude_seconds",
    "maximum_adjacent_rate",
    "minimum_adjacent_rate",
    "segment_auc_0_000_4_092",
    "segment_auc_4_092_8_184",
    "segment_auc_8_184_12_276",
)
SEGMENTS: Final = ((0.0, 4.092), (4.092, 8.184), (8.184, 12.276))
DEFAULT_TRAJECTORY_OUTPUT: Final = Path("artifacts/m05")
Representation = Literal["A", "B", "C-PCA", "C-PLS"]


@dataclass(frozen=True)
class TrajectoryData:
    """Unit-aligned scalar, summary, trajectory and target arrays."""

    unit_ids: tuple[str, ...]
    scalars: np.ndarray
    summaries: np.ndarray
    trajectories: np.ndarray
    targets: np.ndarray


@dataclass(frozen=True)
class TrajectoryResults:
    predictions: pl.DataFrame
    metrics: pl.DataFrame
    selections: tuple[dict[str, object], ...]


def _segment_auc(time: np.ndarray, values: np.ndarray, start: float, end: float) -> float:
    if start < time[0] or end > time[-1] or start >= end:
        raise ValueError("segment boundaries must fall inside an increasing trajectory axis")
    interior = (time > start) & (time < end)
    segment_time = np.concatenate(([start], time[interior], [end]))
    segment_values = np.concatenate(
        ([np.interp(start, time, values)], values[interior], [np.interp(end, time, values)])
    )
    return float(np.trapezoid(segment_values, segment_time))


def summarize_trajectory(time: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Return the 13 pre-specified summaries for one native trajectory."""
    if time.ndim != 1 or values.shape != time.shape or len(time) < 2:
        raise ValueError("trajectory time and values must be matching one-dimensional arrays")
    elapsed = np.diff(time)
    if not np.isfinite(time).all() or not np.isfinite(values).all() or np.any(elapsed <= 0):
        raise ValueError("trajectory coordinates must be finite with strictly increasing time")
    differences = np.diff(values) / elapsed
    maximum_index = int(np.argmax(values))
    quantiles = np.quantile(values, (0.1, 0.5, 0.9), method="linear")
    return np.asarray(
        [
            np.mean(values),
            np.std(values, ddof=0),
            values[maximum_index],
            time[maximum_index],
            *quantiles,
            np.trapezoid(values, time),
            np.max(differences),
            np.min(differences),
            *(_segment_auc(time, values, start, end) for start, end in SEGMENTS),
        ],
        dtype=np.float64,
    )


def assemble_trajectory_data(
    bundle: ManufacturingBundle, memberships: pl.DataFrame
) -> tuple[TrajectoryData, pl.DataFrame]:
    """Align native signals and model rows by identity and sample index."""
    rows = assemble_model_rows(bundle, memberships)
    unit_rows = rows.select("unit_id", *SCALAR_PREDICTOR_COLUMNS, "weight_g").unique("unit_id")
    unit_rows = unit_rows.sort("unit_id")
    signals = bundle.signals.select(
        "unit_id",
        "operation_id",
        "sample_index",
        "elapsed_time_seconds",
        "injection_pressure",
        "injection_flow",
    ).sort("unit_id", "sample_index")
    if signals.null_count().sum_horizontal().item():
        raise ValueError("M5 trajectory inputs must be complete")
    signal_ids = tuple(signals["unit_id"].unique(maintain_order=True).to_list())
    unit_ids = tuple(unit_rows["unit_id"].to_list())
    if signal_ids != unit_ids:
        raise ValueError(
            "every modeled unit must have exactly one aligned pressure/flow trajectory"
        )
    counts = signals.group_by("unit_id", maintain_order=True).len()
    if counts["len"].n_unique() != 1 or counts["len"][0] != 2048:
        raise ValueError("every modeled unit must retain exactly 2,048 native samples")

    summaries: list[np.ndarray] = []
    trajectories: list[np.ndarray] = []
    for part in signals.partition_by("unit_id", maintain_order=True):
        expected_index = np.arange(part.height, dtype=np.uint32)
        if not np.array_equal(part["sample_index"].to_numpy(), expected_index):
            raise ValueError("sample_index must be complete and ordered within every unit")
        time = part["elapsed_time_seconds"].to_numpy()
        pressure = part["injection_pressure"].to_numpy()
        flow = part["injection_flow"].to_numpy()
        summaries.append(
            np.concatenate((summarize_trajectory(time, pressure), summarize_trajectory(time, flow)))
        )
        trajectories.append(np.concatenate((pressure, flow)))
    return (
        TrajectoryData(
            unit_ids=unit_ids,
            scalars=unit_rows.select(SCALAR_PREDICTOR_COLUMNS).to_numpy(),
            summaries=np.vstack(summaries),
            trajectories=np.vstack(trajectories),
            targets=unit_rows["weight_g"].to_numpy(),
        ),
        rows,
    )


def _indices(data: TrajectoryData) -> dict[str, int]:
    return {unit_id: index for index, unit_id in enumerate(data.unit_ids)}


def _arrays(
    data: TrajectoryData, rows: pl.DataFrame
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    lookup = _indices(data)
    indexes = np.asarray([lookup[value] for value in rows["unit_id"]], dtype=np.int64)
    return (
        data.scalars[indexes],
        data.summaries[indexes],
        data.trajectories[indexes],
        data.targets[indexes],
    )


def _prepare(
    representation: Representation,
    components: int | None,
    train: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    evaluation: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train_scalars, train_summaries, train_trajectories, train_y = train
    evaluation_scalars, evaluation_summaries, evaluation_trajectories, _ = evaluation
    if representation == "A":
        train_combined, evaluation_combined = train_scalars, evaluation_scalars
    elif representation == "B":
        train_combined = np.column_stack((train_scalars, train_summaries))
        evaluation_combined = np.column_stack((evaluation_scalars, evaluation_summaries))
    else:
        if components is None:
            raise ValueError("compressed representations require a component count")
        trajectory_scaler = StandardScaler().fit(train_trajectories)
        scaled_train = np.asarray(trajectory_scaler.transform(train_trajectories), dtype=np.float64)
        scaled_evaluation = np.asarray(
            trajectory_scaler.transform(evaluation_trajectories), dtype=np.float64
        )
        if representation == "C-PCA":
            compressor = PCA(n_components=components, svd_solver="full").fit(scaled_train)
        else:
            compressor = PLSRegression(n_components=components, scale=False).fit(
                scaled_train, train_y
            )
        train_scores = np.asarray(compressor.transform(scaled_train), dtype=np.float64)
        evaluation_scores = np.asarray(compressor.transform(scaled_evaluation), dtype=np.float64)
        train_combined = np.column_stack((train_scalars, train_scores))
        evaluation_combined = np.column_stack((evaluation_scalars, evaluation_scores))
    combined_scaler = StandardScaler().fit(train_combined)
    return (
        np.asarray(combined_scaler.transform(train_combined), dtype=np.float64),
        train_y,
        np.asarray(combined_scaler.transform(evaluation_combined), dtype=np.float64),
    )


def _ridge_predict(alpha: float, prepared: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    train_x, train_y, evaluation_x = prepared
    fitted = Ridge(alpha=alpha, fit_intercept=True).fit(train_x, train_y)
    return np.asarray(fitted.predict(evaluation_x), dtype=np.float64)


def fit_predict_representation(
    representation: Representation,
    alpha: float,
    components: int | None,
    train: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    evaluation: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> np.ndarray:
    prepared = _prepare(representation, components, train, evaluation)
    return np.asarray(_ridge_predict(alpha, prepared), dtype=np.float64)


def _candidate_grid(representation: Representation) -> tuple[tuple[int | None, float], ...]:
    components: tuple[int | None, ...] = (
        (None,) if representation in ("A", "B") else COMPONENT_COUNTS
    )
    return tuple((count, alpha) for count in components for alpha in RIDGE_ALPHAS)


def select_representation_candidate(
    representation: Representation, data: TrajectoryData, fit_tune: pl.DataFrame
) -> tuple[int | None, float, list[dict[str, object]]]:
    inner_folds = sorted(fit_tune["inner_fold"].drop_nulls().unique().to_list())
    if len(inner_folds) < 2 or fit_tune["inner_fold"].null_count():
        raise ValueError("fit/tune rows require at least two complete inner folds")
    scores: list[dict[str, object]] = []
    best = _candidate_grid(representation)[0]
    best_score = float("inf")
    component_options: tuple[int | None, ...] = (
        (None,) if representation in ("A", "B") else COMPONENT_COUNTS
    )
    for components in component_options:
        prepared_folds: list[
            tuple[object, tuple[np.ndarray, np.ndarray, np.ndarray], np.ndarray]
        ] = []
        for inner_fold in inner_folds:
            train_rows = fit_tune.filter(pl.col("inner_fold") != inner_fold).sort("unit_id")
            validation_rows = fit_tune.filter(pl.col("inner_fold") == inner_fold).sort("unit_id")
            prepared_folds.append(
                (
                    inner_fold,
                    _prepare(
                        representation,
                        components,
                        _arrays(data, train_rows),
                        _arrays(data, validation_rows),
                    ),
                    _arrays(data, validation_rows)[3],
                )
            )
        for alpha in RIDGE_ALPHAS:
            fold_scores: list[dict[str, object]] = []
            for inner_fold, prepared, observed in prepared_folds:
                predicted = _ridge_predict(alpha, prepared)
                fold_scores.append(
                    {
                        "inner_fold": inner_fold,
                        "mae_g": float(np.mean(np.abs(observed - predicted))),
                    }
                )
            mean_mae = float(np.mean([cast(float, item["mae_g"]) for item in fold_scores]))
            scores.append(
                {
                    "components": components,
                    "alpha": alpha,
                    "inner_fold_scores": fold_scores,
                    "mean_inner_mae_g": mean_mae,
                }
            )
            if mean_mae < best_score:
                best, best_score = (components, alpha), mean_mae
    return best[0], best[1], scores


def _metrics(observed: np.ndarray, predicted: np.ndarray) -> tuple[float, float, float | None]:
    errors = observed - predicted
    denominator = float(np.sum(np.square(observed - np.mean(observed))))
    return (
        float(np.mean(np.abs(errors))),
        float(np.sqrt(np.mean(np.square(errors)))),
        1.0 - float(np.sum(np.square(errors))) / denominator if denominator > 0 else None,
    )


def run_trajectory_representations(
    bundle: ManufacturingBundle, memberships: pl.DataFrame
) -> TrajectoryResults:
    """Evaluate the four fixed M5 representations on every M3 fold."""
    data, rows = assemble_trajectory_data(bundle, memberships)
    predictions: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    selections: list[dict[str, object]] = []
    for protocol, fold in EXPECTED_FOLDS:
        fold_rows = rows.filter((pl.col("protocol") == protocol) & (pl.col("fold") == fold))
        fit_tune = fold_rows.filter(pl.col("role") == "fit_tune").sort("unit_id")
        evaluation = fold_rows.filter(pl.col("role") == "test").sort("unit_id")
        observed = _arrays(data, evaluation)[3]
        fold_maes: dict[str, float] = {}
        pending_metrics: list[dict[str, object]] = []
        for representation in REPRESENTATION_ORDER:
            components, alpha, scores = select_representation_candidate(
                representation, data, fit_tune
            )
            predicted = fit_predict_representation(
                representation,
                alpha,
                components,
                _arrays(data, fit_tune),
                _arrays(data, evaluation),
            )
            mae, rmse, r2 = _metrics(observed, predicted)
            fold_maes[representation] = mae
            pending_metrics.append(
                {
                    "protocol": protocol,
                    "fold": fold,
                    "representation": representation,
                    "selected_components": components,
                    "selected_alpha": alpha,
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
                    "selected_alpha": alpha,
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
    return TrajectoryResults(
        predictions=pl.DataFrame(predictions).sort("protocol", "fold", "representation", "unit_id"),
        metrics=pl.DataFrame(metrics).sort("protocol", "fold", "representation"),
        selections=tuple(selections),
    )


def _group_metrics(predictions: pl.DataFrame) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for (protocol, fold, representation, experiment), rows in predictions.partition_by(
        ["protocol", "fold", "representation", "experiment_id"], as_dict=True
    ).items():
        mae, rmse, r2 = _metrics(
            rows["observed_weight_g"].to_numpy(), rows["predicted_weight_g"].to_numpy()
        )
        result.append(
            {
                "protocol": protocol,
                "fold": fold,
                "representation": representation,
                "experiment_id": experiment,
                "evaluation_count": rows.height,
                "mae_g": mae,
                "rmse_g": rmse,
                "r2": r2,
            }
        )
    return sorted(
        result,
        key=lambda row: tuple(
            str(row[key]) for key in ("protocol", "fold", "representation", "experiment_id")
        ),
    )


def write_trajectory_results(
    results: TrajectoryResults,
    bundle: ManufacturingBundle,
    memberships_path: Path,
    output: Path = DEFAULT_TRAJECTORY_OUTPUT,
) -> dict[str, object]:
    """Atomically write M5 predictions, metrics, and reproducibility record."""
    primary = results.metrics.filter(pl.col("protocol") == "primary")
    summaries: list[dict[str, object]] = []
    for representation in REPRESENTATION_ORDER:
        metric_rows = primary.filter(pl.col("representation") == representation)
        mean_mae = cast(float, metric_rows["mae_g"].mean())
        summaries.append(
            {
                "representation": representation,
                "primary_equal_fold_mean_mae_g": mean_mae,
                "primary_equal_fold_delta_mae_vs_a_g": 0.0,
            }
        )
    baseline = cast(float, summaries[0]["primary_equal_fold_mean_mae_g"])
    for item in summaries:
        item["primary_equal_fold_delta_mae_vs_a_g"] = baseline - cast(
            float, item["primary_equal_fold_mean_mae_g"]
        )
    record: dict[str, object] = {
        "dataset": bundle.metadata.dataset,
        "source_version": bundle.metadata.source_version,
        "source_archive_sha256": bundle.metadata.archive_sha256,
        "membership_reference": str(memberships_path),
        "membership_sha256": sha256(memberships_path.read_bytes()).hexdigest(),
        "membership_rows": pl.scan_parquet(memberships_path).select(pl.len()).collect().item(),
        "representations": {
            "A": "16 M3 scalars",
            "B": "16 scalars plus 13 fixed summaries per pressure/flow channel",
            "C-PCA": "16 scalars plus joint PCA scores of standardized pressure-then-flow samples",
            "C-PLS": (
                "16 scalars plus joint supervised PLS X scores of standardized "
                "pressure-then-flow samples"
            ),
        },
        "trajectory_samples_per_channel": 2048,
        "trajectory_column_order": "2,048 pressure samples then 2,048 flow samples",
        "engineered_summary_order_per_channel": list(SUMMARY_NAMES),
        "engineered_channel_order": list(CHANNELS),
        "summary_segment_seconds": [list(item) for item in SEGMENTS],
        "ridge_alphas": list(RIDGE_ALPHAS),
        "component_counts": list(COMPONENT_COUNTS),
        "candidate_order": "ascending components then ascending alpha; A/B ascending alpha",
        "selection_metric": "equal-weight mean inner-validation MAE in grams",
        "preprocessing": (
            "All scalers and PCA/PLS fits use inner-training rows only during selection, then "
            "all fit/tune rows for refit. C standardizes trajectory columns, fits PCA with "
            "full SVD or PLS with scale=False, appends scores to scalars, and standardizes "
            "the combined matrix before Ridge. A/B standardize their full matrices."
        ),
        "limitations": [
            (
                "M2 explored all three experiments; primary folds are grouped cross-validation, "
                "not an untouched prospective test."
            ),
            (
                "Only three experiments and two development groups per primary fold limit "
                "shift evidence."
            ),
            "Sample-position scaling can emphasize low-variance trajectory positions.",
            (
                "Amplitudes have unresolved native units; integrals are amplitude-seconds, "
                "not volume or energy."
            ),
            "Outer metrics do not select a representation or authorize feature/grid expansion.",
        ],
        "selections": list(results.selections),
        "summaries": summaries,
        "per_experiment_metrics": _group_metrics(results.predictions),
        "package_versions": {
            "python": platform.python_version(),
            "numpy": version("numpy"),
            "polars": version("polars"),
            "scikit-learn": version("scikit-learn"),
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
