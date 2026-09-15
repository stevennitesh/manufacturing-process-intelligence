# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportPrivateUsage=false
"""Focused wiring, leakage, and reference checks for the public M6 runner."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import cast

import numpy as np
import polars as pl
import pytest
from lightgbm import LGBMRegressor
from sklearn.preprocessing import StandardScaler

import mpi.models.lightgbm_comparison as m6
from mpi.datasets.injection_molding_protocol import SCALAR_PREDICTOR_COLUMNS
from mpi.models.lightgbm_comparison import (
    LightGBMSetting,
    candidate_grid,
    run_lightgbm_comparison,
    write_lightgbm_results,
)
from tests.unit.test_scalar_baselines import _synthetic_inputs
from tests.unit.test_trajectory_representations import _with_signals

TEST_SETTINGS = (
    LightGBMSetting(num_leaves=3, min_child_samples=2, n_estimators=3),
    LightGBMSetting(num_leaves=7, min_child_samples=2, n_estimators=15),
)


def _small_grid(representation: str) -> tuple[tuple[int | None, LightGBMSetting], ...]:
    components = (None,) if representation in ("A", "B") else (2,)
    return tuple((count, setting) for count in components for setting in TEST_SETTINGS)


def _direct_estimator(setting: LightGBMSetting) -> LGBMRegressor:
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


def test_candidate_grid_has_exact_fixed_order() -> None:
    a_grid = candidate_grid("A")
    c_grid = candidate_grid("C-PCA")

    assert len(a_grid) == 8
    assert len(c_grid) == 24
    assert [components for components, _ in c_grid] == [2] * 8 + [4] * 8 + [8] * 8
    assert [setting for _, setting in a_grid] == [
        LightGBMSetting(7, 10, 100),
        LightGBMSetting(7, 10, 300),
        LightGBMSetting(7, 30, 100),
        LightGBMSetting(7, 30, 300),
        LightGBMSetting(15, 10, 100),
        LightGBMSetting(15, 10, 300),
        LightGBMSetting(15, 30, 100),
        LightGBMSetting(15, 30, 300),
    ]


def test_public_runner_preserves_unit_alignment_under_row_shuffling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(m6, "candidate_grid", _small_grid)
    bare_bundle, memberships = _synthetic_inputs()
    bundle = _with_signals(bare_bundle)
    expected = run_lightgbm_comparison(bundle, memberships)
    shuffled = replace(
        bundle,
        signals=bundle.signals.sample(fraction=1.0, shuffle=True, seed=31),
        process_features=bundle.process_features.sample(fraction=1.0, shuffle=True, seed=32),
        quality=bundle.quality.sample(fraction=1.0, shuffle=True, seed=33),
    )

    actual = run_lightgbm_comparison(
        shuffled, memberships.sample(fraction=1.0, shuffle=True, seed=34)
    )

    assert actual.predictions.equals(expected.predictions)
    assert actual.metrics.equals(expected.metrics)
    assert actual.selections == expected.selections


def test_public_runner_excludes_calibration_and_evaluation_labels_from_fit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(m6, "candidate_grid", _small_grid)
    bare_bundle, memberships = _synthetic_inputs()
    bundle = _with_signals(bare_bundle)
    expected = run_lightgbm_comparison(bundle, memberships)
    fold_memberships = memberships.filter(
        (pl.col("protocol") == "primary") & (pl.col("fold") == "holdout_experiment_15")
    )
    protected_ids = fold_memberships.filter(pl.col("role") != "fit_tune")["unit_id"]
    changed = replace(
        bundle,
        quality=bundle.quality.with_columns(
            pl.when(pl.col("unit_id").is_in(protected_ids.implode()))
            .then(pl.col("measured_value") + 1_000_000.0)
            .otherwise(pl.col("measured_value"))
        ),
    )

    actual = run_lightgbm_comparison(changed, memberships)
    selected_fold = (pl.col("protocol") == "primary") & (pl.col("fold") == "holdout_experiment_15")
    assert (
        actual.predictions.filter(selected_fold)
        .drop("observed_weight_g")
        .equals(expected.predictions.filter(selected_fold).drop("observed_weight_g"))
    )
    expected_selections = tuple(
        row
        for row in expected.selections
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    )
    actual_selections = tuple(
        row
        for row in actual.selections
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    )
    assert actual_selections == expected_selections
    assert (
        not actual.metrics.filter(selected_fold)
        .select("mae_g")
        .equals(expected.metrics.filter(selected_fold).select("mae_g"))
    )


def test_direct_lightgbm_reference_and_saved_metrics_match(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(m6, "candidate_grid", _small_grid)
    bare_bundle, memberships = _synthetic_inputs()
    bundle = _with_signals(bare_bundle)
    results = run_lightgbm_comparison(bundle, memberships)
    selection = next(
        row
        for row in results.selections
        if row["protocol"] == "primary"
        and row["fold"] == "holdout_experiment_15"
        and row["representation"] == "A"
    )
    fold = memberships.filter(
        (pl.col("protocol") == "primary") & (pl.col("fold") == "holdout_experiment_15")
    )
    fit_rows = fold.filter(pl.col("role") == "fit_tune").select("unit_id", "inner_fold")
    test_ids = fold.filter(pl.col("role") == "test").sort("unit_id")["unit_id"]
    feature_rows = bundle.process_features.select("unit_id", *SCALAR_PREDICTOR_COLUMNS)
    targets = bundle.quality.select("unit_id", pl.col("measured_value").alias("observed_weight_g"))
    train = fit_rows.join(feature_rows, on="unit_id").join(targets, on="unit_id").sort("unit_id")
    manual_mean_scores: list[float] = []
    for setting in TEST_SETTINGS:
        inner_scores: list[float] = []
        for inner_fold in sorted(train["inner_fold"].unique().to_list()):
            inner_train = train.filter(pl.col("inner_fold") != inner_fold)
            validation = train.filter(pl.col("inner_fold") == inner_fold)
            inner_scaler = StandardScaler().fit(
                inner_train.select(SCALAR_PREDICTOR_COLUMNS).to_numpy()
            )
            fitted = _direct_estimator(setting).fit(
                inner_scaler.transform(inner_train.select(SCALAR_PREDICTOR_COLUMNS).to_numpy()),
                inner_train["observed_weight_g"].to_numpy(),
            )
            predicted = np.asarray(
                fitted.predict(
                    inner_scaler.transform(validation.select(SCALAR_PREDICTOR_COLUMNS).to_numpy())
                ),
                dtype=np.float64,
            )
            inner_scores.append(
                float(np.mean(np.abs(validation["observed_weight_g"].to_numpy() - predicted)))
            )
        manual_mean_scores.append(float(np.mean(inner_scores)))
    assert manual_mean_scores[0] != pytest.approx(manual_mean_scores[1])
    selected_setting = TEST_SETTINGS[int(np.argmin(manual_mean_scores))]
    assert selection["selected_components"] is None
    assert selection["selected_setting"] == {
        "num_leaves": selected_setting.num_leaves,
        "min_child_samples": selected_setting.min_child_samples,
        "n_estimators": selected_setting.n_estimators,
    }
    recorded_scores = cast(list[dict[str, object]], selection["candidate_scores"])
    np.testing.assert_allclose(
        [cast(float, row["mean_inner_mae_g"]) for row in recorded_scores], manual_mean_scores
    )

    evaluation = pl.DataFrame({"unit_id": test_ids}).join(feature_rows, on="unit_id")
    scaler = StandardScaler().fit(train.select(SCALAR_PREDICTOR_COLUMNS).to_numpy())
    independent = _direct_estimator(selected_setting).fit(
        scaler.transform(train.select(SCALAR_PREDICTOR_COLUMNS).to_numpy()),
        train["observed_weight_g"].to_numpy(),
    )
    expected_prediction = np.asarray(
        independent.predict(
            scaler.transform(evaluation.select(SCALAR_PREDICTOR_COLUMNS).to_numpy())
        ),
        dtype=np.float64,
    )
    assert np.ptp(expected_prediction) > 0.0
    assert any(
        cast(int, tree["num_leaves"]) > 1
        for tree in cast(list[dict[str, object]], independent.booster_.dump_model()["tree_info"])
    )
    actual_prediction = results.predictions.filter(
        (pl.col("protocol") == "primary")
        & (pl.col("fold") == "holdout_experiment_15")
        & (pl.col("representation") == "A")
    ).sort("unit_id")
    np.testing.assert_allclose(
        actual_prediction["predicted_weight_g"].to_numpy(), expected_prediction, atol=0.0, rtol=0.0
    )

    memberships_path = tmp_path / "memberships.parquet"
    memberships.write_parquet(memberships_path)
    record = write_lightgbm_results(results, bundle, memberships_path, tmp_path / "results")
    assert results.metrics.height == 16
    metric = results.metrics.filter(
        (pl.col("protocol") == "primary")
        & (pl.col("fold") == "holdout_experiment_15")
        & (pl.col("representation") == "A")
    ).row(0, named=True)
    errors = (
        actual_prediction["observed_weight_g"].to_numpy()
        - actual_prediction["predicted_weight_g"].to_numpy()
    )
    assert metric["mae_g"] == pytest.approx(float(np.mean(np.abs(errors))))
    assert metric["rmse_g"] == pytest.approx(float(np.sqrt(np.mean(np.square(errors)))))
    summaries = cast(list[dict[str, object]], record["summaries"])
    baseline = cast(float, summaries[0]["primary_equal_fold_mean_mae_g"])
    for summary in summaries:
        representation = cast(str, summary["representation"])
        mean_mae = cast(
            float,
            results.metrics.filter(
                (pl.col("protocol") == "primary") & (pl.col("representation") == representation)
            )["mae_g"].mean(),
        )
        assert summary["primary_equal_fold_mean_mae_g"] == pytest.approx(mean_mae)
        assert summary["primary_equal_fold_delta_mae_vs_a_g"] == pytest.approx(baseline - mean_mae)
    effective_settings = cast(list[dict[str, object]], record["estimator_effective_parameters"])
    assert len(effective_settings) == 8
    effective = effective_settings[0]
    assert effective["objective"] == "regression"
    assert effective["n_jobs"] == 1
    assert effective["deterministic"] is True
    assert effective["force_col_wise"] is True
