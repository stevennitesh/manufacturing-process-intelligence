# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Focused numerical, boundary, and ordinary-path checks for M9."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import numpy as np
import polars as pl
import pytest
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import mpi.models.predictive_explanation as m9
from mpi.data.canonical import ManufacturingBundle
from mpi.datasets.injection_molding_protocol import SCALAR_PREDICTOR_COLUMNS
from mpi.models.scalar_baselines import EXPECTED_FOLDS, assemble_model_rows
from mpi.models.uncertainty_shift import (
    ScalarCandidate,
    fit_scalar_candidate,
    predict_scalar_candidate,
    scalar_candidate_from_record,
)
from tests.unit.test_scalar_baselines import _synthetic_inputs


def _m7_inputs(
    bundle: ManufacturingBundle, memberships: pl.DataFrame
) -> tuple[dict[str, object], pl.DataFrame]:
    selected: dict[str, object] = {"family": "pls", "components": 1}
    record: dict[str, object] = {
        "dataset": bundle.metadata.dataset,
        "source_version": bundle.metadata.source_version,
        "source_archive_sha256": bundle.metadata.archive_sha256,
        "membership_rows": memberships.height,
        "features": list(SCALAR_PREDICTOR_COLUMNS),
        "selections": [
            {"protocol": protocol, "fold": fold, "selected_candidate": selected}
            for protocol, fold in EXPECTED_FOLDS
        ],
    }
    rows = assemble_model_rows(bundle, memberships)
    predictions: list[dict[str, object]] = []
    candidate = scalar_candidate_from_record(selected)
    for protocol, fold in EXPECTED_FOLDS:
        fold_rows = rows.filter((pl.col("protocol") == protocol) & (pl.col("fold") == fold))
        train = fold_rows.filter(pl.col("role") == "fit_tune").sort("unit_id")
        evaluation = fold_rows.filter(pl.col("role") == "test").sort("unit_id")
        predicted = predict_scalar_candidate(fit_scalar_candidate(candidate, train), evaluation)
        predictions.extend(
            {
                "unit_id": unit_id,
                "protocol": protocol,
                "fold": fold,
                "predicted_weight_g": estimate,
            }
            for unit_id, estimate in zip(evaluation["unit_id"], predicted, strict=True)
        )
    return record, pl.DataFrame(predictions)


def test_support_boundaries_and_zero_variance_are_analytic() -> None:
    train_values: dict[str, list[float]] = {
        feature: [0.0, 1.0, 2.0] for feature in SCALAR_PREDICTOR_COLUMNS
    }
    evaluation_values: dict[str, list[float]] = {
        feature: [0.0, 2.0, -1.0, 3.0] for feature in SCALAR_PREDICTOR_COLUMNS
    }
    constant = SCALAR_PREDICTOR_COLUMNS[1]
    train_values[constant] = [5.0, 5.0, 5.0]
    evaluation_values[constant] = [5.0, 5.0, 4.0, 6.0]
    rows = m9.feature_support_rows(
        pl.DataFrame(train_values), pl.DataFrame(evaluation_values), {"population": "test"}
    )
    varying = next(row for row in rows if row["feature"] == SCALAR_PREDICTOR_COLUMNS[0])
    assert varying["fraction_below_training_range"] == 0.25
    assert varying["fraction_above_training_range"] == 0.25
    assert varying["fraction_outside_training_range"] == 0.5
    assert varying["training_std"] == pytest.approx(np.sqrt(2.0 / 3.0))
    assert varying["standardized_mean_shift"] == pytest.approx(0.0)
    fixed = next(row for row in rows if row["feature"] == constant)
    assert fixed["constant_training_feature"] is True
    assert fixed["standardized_mean_shift"] is None
    assert fixed["fraction_outside_training_range"] == 0.5


def test_known_predictor_importance_matches_independent_seeded_permutation() -> None:
    generator = np.random.default_rng(2026)
    x = generator.normal(size=(60, len(SCALAR_PREDICTOR_COLUMNS)))
    observed = 10.0 + 3.0 * x[:, 0]
    evaluation = pl.DataFrame(
        {name: x[:, index] for index, name in enumerate(SCALAR_PREDICTOR_COLUMNS)}
    ).with_columns(pl.Series("weight_g", observed))
    fitted = Pipeline([("scale", StandardScaler()), ("model", LinearRegression())]).fit(x, observed)
    rows = m9.permutation_importance_rows(fitted, evaluation, {"population": "known"})
    relevant = rows[0]
    irrelevant = rows[1]
    assert cast(float, relevant["importance_mean_g"]) > 2.0
    assert abs(cast(float, irrelevant["importance_mean_g"])) < 1e-12

    seed_source = np.random.RandomState(42)
    rng = np.random.RandomState(seed_source.randint(np.iinfo(np.int32).max + 1))
    indices = np.arange(len(x))
    shuffled = x.copy()
    independently_calculated: list[float] = []
    for _ in range(10):
        rng.shuffle(indices)
        shuffled[:, 0] = shuffled[indices, 0]
        predicted = np.asarray(fitted.predict(shuffled), dtype=np.float64)
        independently_calculated.append(float(np.mean(np.abs(observed - predicted))))
    np.testing.assert_allclose(
        cast(list[float], relevant["repeat_importance_g"]),
        independently_calculated,
        rtol=0.0,
        atol=1e-14,
    )


def test_runner_reproduces_predictions_separates_populations_and_refits_once_per_fold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle, memberships = _synthetic_inputs()
    record, reference = _m7_inputs(bundle, memberships)
    original_fit = m9.fit_scalar_candidate
    fit_count = 0

    def counted_fit(candidate: ScalarCandidate, rows: pl.DataFrame) -> Pipeline:
        nonlocal fit_count
        fit_count += 1
        return original_fit(candidate, rows)

    monkeypatch.setattr(m9, "fit_scalar_candidate", counted_fit)
    result = m9.run_predictive_explanation(bundle, memberships, record, reference)

    assert fit_count == 4
    assert result.maximum_prediction_difference_g == 0.0
    assert result.permutation_importance.height == result.feature_support.height == 96
    assert len(result.populations) == 6
    id_rows = result.permutation_importance.filter(pl.col("protocol") == "secondary_id")
    assert set(id_rows["evaluation_experiment_id"]) == {15, 20, 23}
    assert id_rows["model_settings"].n_unique() == 1
    assert all(len(values) == 10 for values in result.permutation_importance["repeat_importance_g"])

    # Independently reproduce sklearn's seeded shuffle sequence for one feature/population.
    population = result.permutation_importance.filter(
        pl.col("feature") == SCALAR_PREDICTOR_COLUMNS[0]
    ).row(0, named=True)
    protocol = str(population["protocol"])
    fold = str(population["model_fold"])
    experiment = int(population["evaluation_experiment_id"])
    rows = assemble_model_rows(bundle, memberships)
    fold_rows = rows.filter((pl.col("protocol") == protocol) & (pl.col("fold") == fold))
    train = fold_rows.filter(pl.col("role") == "fit_tune").sort("unit_id")
    evaluation = fold_rows.filter(
        (pl.col("role") == "test") & (pl.col("experiment_id") == experiment)
    ).sort("unit_id")
    fitted = original_fit(scalar_candidate_from_record({"family": "pls", "components": 1}), train)
    x = evaluation.select(SCALAR_PREDICTOR_COLUMNS).to_numpy()
    observed = evaluation["weight_g"].to_numpy()
    baseline = float(np.mean(np.abs(observed - predict_scalar_candidate(fitted, evaluation))))
    seed_source = np.random.RandomState(42)
    rng = np.random.RandomState(seed_source.randint(np.iinfo(np.int32).max + 1))
    shuffled = x.copy()
    indices = np.arange(len(x))
    repeats: list[float] = []
    for _ in range(10):
        rng.shuffle(indices)
        shuffled[:, 0] = shuffled[indices, 0]
        estimate = np.asarray(fitted.predict(shuffled), dtype=np.float64).reshape(-1)
        repeats.append(float(np.mean(np.abs(observed - estimate))) - baseline)
    np.testing.assert_allclose(population["repeat_importance_g"], repeats, rtol=0.0, atol=1e-15)


def test_evaluation_labels_change_importance_only_and_calibration_labels_change_nothing() -> None:
    bundle, memberships = _synthetic_inputs()
    record, reference = _m7_inputs(bundle, memberships)
    expected = m9.run_predictive_explanation(bundle, memberships, record, reference)
    evaluation_ids = memberships.filter(
        (pl.col("protocol") == "primary")
        & (pl.col("fold") == "holdout_experiment_15")
        & (pl.col("role") == "test")
    )["unit_id"]
    evaluation_changed = replace(
        bundle,
        quality=bundle.quality.with_columns(
            pl.when(pl.col("unit_id").is_in(evaluation_ids.implode()))
            .then(pl.col("measured_value") + pl.col("unit_id").str.slice(-1).cast(pl.Int64) * 10.0)
            .otherwise(pl.col("measured_value"))
        ),
    )
    changed_record, changed_reference = _m7_inputs(evaluation_changed, memberships)
    changed = m9.run_predictive_explanation(
        evaluation_changed, memberships, changed_record, changed_reference
    )
    target_filter = (pl.col("protocol") == "primary") & (
        pl.col("model_fold") == "holdout_experiment_15"
    )
    assert changed.feature_support.filter(target_filter).equals(
        expected.feature_support.filter(target_filter)
    )
    assert not changed.permutation_importance.filter(target_filter).equals(
        expected.permutation_importance.filter(target_filter)
    )
    reference_filter = (pl.col("protocol") == "primary") & (
        pl.col("fold") == "holdout_experiment_15"
    )
    assert changed_reference.filter(reference_filter).equals(reference.filter(reference_filter))
    calibration_ids = memberships.filter(
        (pl.col("protocol") == "primary")
        & (pl.col("fold") == "holdout_experiment_15")
        & (pl.col("role") == "calibration")
    )["unit_id"]
    calibration_changed = replace(
        bundle,
        quality=bundle.quality.with_columns(
            pl.when(pl.col("unit_id").is_in(calibration_ids.implode()))
            .then(pl.col("measured_value") + 1000.0)
            .otherwise(pl.col("measured_value"))
        ),
    )
    calibration_record, calibration_reference = _m7_inputs(calibration_changed, memberships)
    unchanged = m9.run_predictive_explanation(
        calibration_changed, memberships, calibration_record, calibration_reference
    )
    assert unchanged.permutation_importance.filter(target_filter).equals(
        expected.permutation_importance.filter(target_filter)
    )
    assert unchanged.feature_support.filter(target_filter).equals(
        expected.feature_support.filter(target_filter)
    )
