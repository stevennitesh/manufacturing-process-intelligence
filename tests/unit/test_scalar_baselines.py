# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Focused leakage and numerical checks for the actual M4 training path."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import cast

import numpy as np
import polars as pl
import pytest
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from mpi.data.canonical import BundleMetadata, ManufacturingBundle
from mpi.datasets.injection_molding_protocol import (
    SCALAR_PREDICTOR_COLUMNS,
    build_memberships,
)
from mpi.models.scalar_baselines import (
    RIDGE_ALPHAS,
    run_scalar_baselines,
    write_scalar_baseline_results,
)


def _synthetic_inputs() -> tuple[ManufacturingBundle, pl.DataFrame]:
    unit_rows: list[dict[str, object]] = []
    feature_rows: list[dict[str, object]] = []
    quality_rows: list[dict[str, object]] = []
    context_rows: list[dict[str, object]] = []
    for experiment in (15, 20, 23):
        for within_experiment in range(12):
            cycle = experiment * 100 + within_experiment
            unit_id = f"unit-{cycle}"
            operation_id = f"operation-{cycle}"
            unit_rows.append({"unit_id": unit_id, "cycle_counter": cycle})
            random_values = np.random.default_rng(cycle).normal(size=len(SCALAR_PREDICTOR_COLUMNS))
            values = {
                name: float(random_values[index] + experiment * 0.03 + within_experiment * 0.01)
                for index, name in enumerate(SCALAR_PREDICTOR_COLUMNS)
            }
            feature_rows.append(
                {
                    "unit_id": unit_id,
                    "operation_id": operation_id,
                    **values,
                    "forbidden_context": float(cycle * 10_000),
                }
            )
            weight = (
                50.0
                + experiment * 0.07
                + within_experiment * 0.11
                + float(random_values[0]) * 0.3
                - float(random_values[1]) * 0.2
            )
            quality_rows.append(
                {
                    "unit_id": unit_id,
                    "operation_id": operation_id,
                    "characteristic": "weight",
                    "measured_value": weight,
                    "measurement_unit": "g",
                }
            )
            context_rows.append(
                {"unit_id": unit_id, "operation_id": operation_id, "experiment_id": experiment}
            )
    metadata = BundleMetadata(
        dataset="injection_molding",
        candidate="dataset2",
        source_version="synthetic-v1",
        archive_size=1,
        archive_sha256="a" * 64,
        source_contract_reference="synthetic",
        citations=(),
        license_name="synthetic",
        license_url="https://example.invalid",
        scalar_lineage=(),
        signal_lineage=(),
        transformations=(),
        exclusions=(),
        limitations=(),
        retained_optional_source_groups=(),
        retained_optional_process_fields=(),
    )
    units = pl.DataFrame(unit_rows)
    context = pl.DataFrame(context_rows)
    bundle = ManufacturingBundle(
        units=units,
        operations=pl.DataFrame(),
        process_features=pl.DataFrame(feature_rows),
        signals=pl.DataFrame(),
        quality=pl.DataFrame(quality_rows),
        context=context,
        metadata=metadata,
    )
    memberships = build_memberships(
        units,
        context,
        source_version=metadata.source_version,
        source_archive_sha256=metadata.archive_sha256,
    )
    return bundle, memberships


def _fixed_fold(table: pl.DataFrame) -> pl.DataFrame:
    result = table.filter(
        (pl.col("protocol") == "primary") & (pl.col("fold") == "holdout_experiment_15")
    )
    return result.sort("model", "unit_id") if "unit_id" in result.columns else result.sort("model")


def test_identity_alignment_and_exact_feature_allowlist_are_row_order_independent() -> None:
    bundle, memberships = _synthetic_inputs()
    expected = run_scalar_baselines(bundle, memberships)
    shuffled = replace(
        bundle,
        process_features=bundle.process_features.sample(fraction=1.0, shuffle=True, seed=9),
        quality=bundle.quality.sample(fraction=1.0, shuffle=True, seed=10),
    )

    actual = run_scalar_baselines(shuffled, memberships.sample(fraction=1.0, shuffle=True, seed=11))

    assert actual.predictions.equals(expected.predictions)
    assert actual.metrics.equals(expected.metrics)


def test_stale_mixed_group_primary_inner_folds_are_rejected() -> None:
    bundle, memberships = _synthetic_inputs()
    stale_memberships = memberships.with_columns(
        pl.when((pl.col("protocol") == "primary") & (pl.col("role") == "fit_tune"))
        .then(pl.col("cycle_counter") % 3)
        .otherwise(pl.col("inner_fold"))
        .alias("inner_fold")
    )

    with pytest.raises(ValueError, match="regenerate the M3 memberships"):
        run_scalar_baselines(bundle, stale_memberships)


def test_calibration_and_evaluation_labels_cannot_affect_fit_or_selection() -> None:
    bundle, memberships = _synthetic_inputs()
    expected = run_scalar_baselines(bundle, memberships)
    fold_memberships = memberships.filter(
        (pl.col("protocol") == "primary") & (pl.col("fold") == "holdout_experiment_15")
    )
    calibration_ids = fold_memberships.filter(pl.col("role") == "calibration")["unit_id"]
    evaluation_ids = fold_memberships.filter(pl.col("role") == "test")["unit_id"]
    changed = replace(
        bundle,
        process_features=bundle.process_features.with_columns(
            pl.when(pl.col("unit_id").is_in(calibration_ids.implode()))
            .then(pl.col(SCALAR_PREDICTOR_COLUMNS[0]) + 1_000_000)
            .otherwise(pl.col(SCALAR_PREDICTOR_COLUMNS[0]))
            .alias(SCALAR_PREDICTOR_COLUMNS[0])
        ),
        quality=bundle.quality.with_columns(
            pl.when(
                pl.col("unit_id").is_in(calibration_ids.implode())
                | pl.col("unit_id").is_in(evaluation_ids.implode())
            )
            .then(pl.col("measured_value") + 1_000_000)
            .otherwise(pl.col("measured_value"))
        ),
    )

    actual = run_scalar_baselines(changed, memberships)
    expected_predictions = _fixed_fold(expected.predictions).drop("observed_weight_g")
    actual_predictions = _fixed_fold(actual.predictions).drop("observed_weight_g")
    assert actual_predictions.equals(expected_predictions)
    assert [
        item["selected_parameter"]
        for item in actual.selections
        if item["protocol"] == "primary" and item["fold"] == "holdout_experiment_15"
    ] == [
        item["selected_parameter"]
        for item in expected.selections
        if item["protocol"] == "primary" and item["fold"] == "holdout_experiment_15"
    ]
    assert (
        not _fixed_fold(actual.metrics)
        .select("mae_g")
        .equals(_fixed_fold(expected.metrics).select("mae_g"))
    )

    changed_evaluation_features = replace(
        bundle,
        process_features=bundle.process_features.with_columns(
            pl.when(pl.col("unit_id").is_in(evaluation_ids.implode()))
            .then(pl.col(SCALAR_PREDICTOR_COLUMNS[0]) + 10.0)
            .otherwise(pl.col(SCALAR_PREDICTOR_COLUMNS[0]))
            .alias(SCALAR_PREDICTOR_COLUMNS[0])
        ),
    )
    feature_result = run_scalar_baselines(changed_evaluation_features, memberships)
    expected_fold = _fixed_fold(expected.predictions)
    changed_fold = _fixed_fold(feature_result.predictions)
    assert not changed_fold.filter(pl.col("model") != "mean").equals(
        expected_fold.filter(pl.col("model") != "mean")
    )
    assert [
        item["selected_parameter"]
        for item in feature_result.selections
        if item["protocol"] == "primary" and item["fold"] == "holdout_experiment_15"
    ] == [
        item["selected_parameter"]
        for item in expected.selections
        if item["protocol"] == "primary" and item["fold"] == "holdout_experiment_15"
    ]


def test_grouped_ridge_selection_and_saved_metrics_match_independent_calculation(
    tmp_path: Path,
) -> None:
    bundle, memberships = _synthetic_inputs()
    results = run_scalar_baselines(bundle, memberships)
    joined = (
        memberships.join(
            bundle.process_features.select("unit_id", *SCALAR_PREDICTOR_COLUMNS),
            on="unit_id",
            validate="m:1",
        )
        .join(
            bundle.quality.select("unit_id", pl.col("measured_value").alias("weight_g")),
            on="unit_id",
            validate="m:1",
        )
        .filter((pl.col("protocol") == "primary") & (pl.col("fold") == "holdout_experiment_15"))
    )
    fit_tune = joined.filter(pl.col("role") == "fit_tune")
    manual_scores: list[float] = []
    for alpha in RIDGE_ALPHAS:
        fold_scores: list[float] = []
        for held_out_experiment in (20, 23):
            train = fit_tune.filter(pl.col("experiment_id") != held_out_experiment)
            validation = fit_tune.filter(pl.col("experiment_id") == held_out_experiment)
            fitted = make_pipeline(StandardScaler(), Ridge(alpha=alpha, fit_intercept=True)).fit(
                train.select(SCALAR_PREDICTOR_COLUMNS).to_numpy(), train["weight_g"].to_numpy()
            )
            predicted = fitted.predict(validation.select(SCALAR_PREDICTOR_COLUMNS).to_numpy())
            fold_scores.append(
                float(np.mean(np.abs(validation["weight_g"].to_numpy() - predicted)))
            )
        manual_scores.append(float(np.mean(fold_scores)))
    ridge_selection = next(
        item
        for item in results.selections
        if item["protocol"] == "primary"
        and item["fold"] == "holdout_experiment_15"
        and item["model"] == "ridge"
    )
    assert ridge_selection["selected_parameter"] == RIDGE_ALPHAS[int(np.argmin(manual_scores))]

    evaluation = joined.filter(pl.col("role") == "test").sort("unit_id")
    selected_alpha = cast(float, ridge_selection["selected_parameter"])
    independently_fitted = make_pipeline(
        StandardScaler(), Ridge(alpha=selected_alpha, fit_intercept=True)
    ).fit(fit_tune.select(SCALAR_PREDICTOR_COLUMNS).to_numpy(), fit_tune["weight_g"].to_numpy())
    independent_prediction = independently_fitted.predict(
        evaluation.select(SCALAR_PREDICTOR_COLUMNS).to_numpy()
    )
    saved_prediction = _fixed_fold(results.predictions).filter(pl.col("model") == "ridge")
    np.testing.assert_allclose(saved_prediction["predicted_weight_g"], independent_prediction)

    prediction = _fixed_fold(results.predictions).filter(pl.col("model") == "mean")
    metric = _fixed_fold(results.metrics).filter(pl.col("model") == "mean").row(0, named=True)
    errors = prediction["observed_weight_g"] - prediction["predicted_weight_g"]
    manual_mae = errors.abs().mean()
    manual_mse = errors.pow(2).mean()
    assert manual_mae is not None
    assert manual_mse is not None
    assert metric["mae_g"] == pytest.approx(cast(float, manual_mae))
    assert metric["rmse_g"] == pytest.approx(cast(float, manual_mse) ** 0.5)
    observed = prediction["observed_weight_g"]
    expected_r2 = 1.0 - float(errors.pow(2).sum()) / float(
        ((observed - observed.mean()) ** 2).sum()
    )
    assert metric["r2"] == pytest.approx(expected_r2)

    memberships_path = tmp_path / "memberships.parquet"
    memberships.write_parquet(memberships_path)
    record = write_scalar_baseline_results(results, bundle, memberships_path, tmp_path / "results")
    summaries = cast(list[dict[str, object]], record["summaries"])
    mean_summary = next(item for item in summaries if item["model"] == "mean")
    primary_mean_metrics = results.metrics.filter(
        (pl.col("protocol") == "primary") & (pl.col("model") == "mean")
    )
    assert mean_summary["primary_equal_fold_mean_mae_g"] == pytest.approx(
        cast(float, primary_mean_metrics["mae_g"].mean())
    )
    primary_mean_predictions = results.predictions.filter(
        (pl.col("protocol") == "primary") & (pl.col("model") == "mean")
    )
    pooled_errors = (
        primary_mean_predictions["observed_weight_g"]
        - primary_mean_predictions["predicted_weight_g"]
    )
    assert mean_summary["primary_pooled_sample_weighted_mae_g"] == pytest.approx(
        cast(float, pooled_errors.abs().mean())
    )
