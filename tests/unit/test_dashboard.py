# pyright: reportUnknownMemberType=false
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest
from streamlit.testing.v1 import AppTest

from mpi.dashboard import (
    DashboardPaths,
    coverage_summary,
    headline_mae,
    load_dashboard_data,
    per_experiment_metrics,
    support_heatmap_table,
)


def _predictions(group: str, values: tuple[str, ...]) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for group_value in values:
        rows.extend(
            (
                {
                    "unit_id": "u15",
                    "protocol": "primary",
                    "fold": "holdout_experiment_15",
                    group: group_value,
                    "experiment_id": 15,
                    "cycle_counter": 15,
                    "observed_weight_g": 100.0,
                    "predicted_weight_g": 99.0,
                },
                {
                    "unit_id": "u20",
                    "protocol": "primary",
                    "fold": "holdout_experiment_20",
                    group: group_value,
                    "experiment_id": 20,
                    "cycle_counter": 20,
                    "observed_weight_g": 101.0,
                    "predicted_weight_g": 99.0,
                },
                {
                    "unit_id": "u15",
                    "protocol": "secondary_id",
                    "fold": "within_experiment",
                    group: group_value,
                    "experiment_id": 15,
                    "cycle_counter": 15,
                    "observed_weight_g": 100.0,
                    "predicted_weight_g": 99.9,
                },
                {
                    "unit_id": "u20",
                    "protocol": "secondary_id",
                    "fold": "within_experiment",
                    group: group_value,
                    "experiment_id": 20,
                    "cycle_counter": 20,
                    "observed_weight_g": 101.0,
                    "predicted_weight_g": 100.8,
                },
            )
        )
    return pl.DataFrame(rows)


def _metrics(group: str, values: tuple[str, ...]) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for group_value in values:
        rows.extend(
            (
                {
                    "protocol": "primary",
                    "fold": "holdout_experiment_15",
                    group: group_value,
                    "evaluation_count": 1,
                    "mae_g": 1.0,
                },
                {
                    "protocol": "primary",
                    "fold": "holdout_experiment_20",
                    group: group_value,
                    "evaluation_count": 1,
                    "mae_g": 2.0,
                },
                {
                    "protocol": "secondary_id",
                    "fold": "within_experiment",
                    group: group_value,
                    "evaluation_count": 2,
                    "mae_g": 0.15,
                },
            )
        )
    return pl.DataFrame(rows)


def _write_dashboard_fixture(root: Path) -> DashboardPaths:
    paths = DashboardPaths(
        bundle=root / "bundle",
        m04=root / "m04",
        m05=root / "m05",
        m06=root / "m06",
        m07=root / "m07",
        m09=root / "m09",
    )
    for directory in (paths.bundle, paths.m04, paths.m05, paths.m06, paths.m07, paths.m09):
        directory.mkdir(parents=True)
    identity = {
        "dataset": "injection_molding",
        "source_version": "fixture-source",
        "source_archive_sha256": "fixture-archive",
        "membership_sha256": "fixture-memberships",
    }
    (paths.bundle / "metadata.json").write_text(
        json.dumps({**identity, "archive_sha256": identity["source_archive_sha256"]}),
        encoding="utf-8",
    )
    for directory in (paths.m04, paths.m05, paths.m06, paths.m07, paths.m09):
        (directory / "run.json").write_text(
            json.dumps({**identity, "m8_eligible": False}), encoding="utf-8"
        )

    pl.DataFrame(
        {
            "unit_id": ["u15", "u20"],
            "operation_id": ["o15", "o20"],
            "characteristic": ["weight", "weight"],
            "measured_value": [100.0, 101.0],
            "measurement_unit": ["g", "g"],
            "lower_spec": [None, None],
            "upper_spec": [None, None],
        }
    ).write_parquet(paths.bundle / "quality.parquet")
    pl.DataFrame(
        {
            "unit_id": ["u15", "u20"],
            "operation_id": ["o15", "o20"],
            "experiment_id": [15, 20],
        }
    ).write_parquet(paths.bundle / "context.parquet")
    pl.DataFrame(
        {
            "unit_id": ["u15", "u15", "u20", "u20"],
            "operation_id": ["o15", "o15", "o20", "o20"],
            "sample_index": [0, 1, 0, 1],
            "elapsed_time_seconds": [0.0, 0.006, 0.0, 0.006],
            "injection_pressure": [1.0, 2.0, 1.5, 2.5],
            "injection_flow": [0.0, 1.0, 0.0, 1.5],
        }
    ).write_parquet(paths.bundle / "signals.parquet")

    _metrics("model", ("mean", "ridge")).write_parquet(paths.m04 / "metrics.parquet")
    _predictions("model", ("mean", "ridge")).write_parquet(paths.m04 / "predictions.parquet")
    _metrics("representation", ("A", "B")).write_parquet(paths.m05 / "metrics.parquet")
    _predictions("representation", ("A", "B")).write_parquet(paths.m05 / "predictions.parquet")
    _metrics("representation", ("A", "B")).write_parquet(paths.m06 / "metrics.parquet")
    _predictions("representation", ("A", "B")).write_parquet(paths.m06 / "predictions.parquet")

    interval_metrics = pl.DataFrame(
        {
            "protocol": ["primary", "primary", "secondary_id", "secondary_id", "secondary_id"],
            "fold": [
                "holdout_experiment_15",
                "holdout_experiment_20",
                "experiment_15",
                "experiment_20",
                "within_experiment",
            ],
            "evaluation_count": [1, 1, 1, 1, 2],
            "nominal_coverage": [0.9] * 5,
            "empirical_coverage": [0.0, 0.003, 1.0, 1.0, 1.0],
            "mean_width_g": [0.2] * 5,
            "median_width_g": [0.2] * 5,
            "mae_g": [1.0, 2.0, 0.1, 0.2, 0.15],
            "rmse_g": [1.0, 2.0, 0.1, 0.2, 0.15],
            "r2": [0.0] * 5,
        }
    )
    interval_metrics.write_parquet(paths.m07 / "metrics.parquet")
    interval_predictions = (
        _predictions("model", ("selected",))
        .drop("model")
        .with_columns(
            (pl.col("predicted_weight_g") - 0.1).alias("lower_g"),
            (pl.col("predicted_weight_g") + 0.1).alias("upper_g"),
            pl.lit(0.2).alias("interval_width_g"),
            pl.lit(0.0).alias("covered"),
            pl.lit(1.0).alias("distance"),
        )
    )
    interval_predictions.write_parquet(paths.m07 / "evaluation_predictions.parquet")

    population_rows: list[dict[str, object]] = []
    for protocol in ("primary", "secondary_id"):
        for experiment in (15, 20):
            for feature, importance, outside in (
                ("actual_back_pressure", -0.01, 1.0),
                ("cycle_time", 0.02, 0.0),
            ):
                population_rows.append(
                    {
                        "protocol": protocol,
                        "model_fold": (
                            f"holdout_experiment_{experiment}"
                            if protocol == "primary"
                            else "within_experiment"
                        ),
                        "evaluation_experiment_id": experiment,
                        "model_family": "lightgbm",
                        "model_settings": "{}",
                        "training_count": 2,
                        "evaluation_count": 1,
                        "baseline_mae_g": 1.0,
                        "feature": feature,
                        "importance_mean_g": importance,
                        "importance_std_g": 0.001,
                        "repeat_importance_g": [importance],
                        "fraction_outside_training_range": outside,
                    }
                )
    population = pl.DataFrame(population_rows)
    population.drop("fraction_outside_training_range").write_parquet(
        paths.m09 / "permutation_importance.parquet"
    )
    population.select(
        "protocol",
        "model_fold",
        "evaluation_experiment_id",
        "model_family",
        "model_settings",
        "training_count",
        "evaluation_count",
        "feature",
        "fraction_outside_training_range",
    ).write_parquet(paths.m09 / "feature_support.parquet")
    return paths


def test_headline_mae_distinguishes_equal_fold_pooled_and_id() -> None:
    metrics = pl.DataFrame(
        {
            "protocol": ["primary", "primary", "secondary_id"],
            "fold": ["f1", "f2", "within_experiment"],
            "model": ["ridge", "ridge", "ridge"],
            "mae_g": [1.0, 3.0, 0.1],
        }
    )
    predictions = pl.DataFrame(
        {
            "protocol": ["primary"] * 4,
            "model": ["ridge"] * 4,
            "observed_weight_g": [0.0] * 4,
            "predicted_weight_g": [1.0, 3.0, 3.0, 3.0],
        }
    )

    result = headline_mae(metrics, predictions, "model")

    assert result["population"].to_list() == [
        "Primary equal-fold mean",
        "Primary pooled (sample-weighted)",
        "Separate ID pooled",
    ]
    assert result["mae_g"].to_list() == pytest.approx([2.0, 2.5, 0.1])


def test_presentation_helpers_preserve_identity_and_small_coverage() -> None:
    predictions = _predictions("model", ("ridge",))
    per_experiment = per_experiment_metrics(predictions, "model")
    assert set(per_experiment["protocol"].to_list()) == {"primary", "secondary_id"}
    assert set(per_experiment["experiment_id"].to_list()) == {15, 20}
    assert {"mae_g", "rmse_g", "r2"} <= set(per_experiment.columns)

    coverage = coverage_summary(
        pl.DataFrame(
            {
                "protocol": ["primary", "secondary_id", "secondary_id"],
                "fold": ["holdout_experiment_23", "experiment_23", "within_experiment"],
                "empirical_coverage": [0.0033003300330033004, 0.84, 0.86],
            }
        )
    )
    assert coverage["population"].to_list() == [
        "Primary · experiment_23",
        "ID · experiment_23",
        "ID · pooled",
    ]
    assert coverage.item(0, "empirical_coverage") == pytest.approx(0.0033003300330033004)

    support = pl.DataFrame(
        {
            "protocol": ["primary", "secondary_id"],
            "evaluation_experiment_id": [23, 23],
            "feature": ["cycle_time", "cycle_time"],
            "fraction_outside_training_range": [0.25, 0.0],
        }
    )
    assert support_heatmap_table(support, "primary").to_dicts() == [
        {
            "feature": "cycle_time",
            "population": "experiment 23",
            "fraction_outside_training_range": 0.25,
        }
    ]


def test_per_experiment_metrics_match_reference_and_null_constant_r2() -> None:
    predictions = pl.DataFrame(
        {
            "protocol": ["secondary_id"] * 4,
            "model": ["ridge"] * 4,
            "experiment_id": [15, 15, 20, 20],
            "observed_weight_g": [0.0, 1.0, 1.0, 1.0],
            "predicted_weight_g": [0.0, 2.0, 1.0, 2.0],
        }
    )

    result = per_experiment_metrics(predictions, "model")

    experiment_15 = result.filter(pl.col("experiment_id") == 15).row(0, named=True)
    assert experiment_15["n"] == 2
    assert experiment_15["mae_g"] == pytest.approx(0.5)
    assert experiment_15["rmse_g"] == pytest.approx(2**-0.5)
    assert experiment_15["r2"] == pytest.approx(-1.0)
    assert result.filter(pl.col("experiment_id") == 20).item(0, "r2") is None


def test_missing_inputs_report_reproduction_commands(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"run_uncertainty_shift\.py"):
        load_dashboard_data(DashboardPaths(bundle=tmp_path / "missing"))


@pytest.mark.parametrize("field", ["source_archive_sha256", "membership_sha256"])
def test_loader_rejects_mixed_milestone_lineage(tmp_path: Path, field: str) -> None:
    paths = _write_dashboard_fixture(tmp_path)
    record_path = paths.m05 / "run.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record[field] = "different-run"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match=f"Artifact lineage mismatch:.*{field}"):
        load_dashboard_data(paths)


def test_loader_caches_until_explicit_reload(tmp_path: Path) -> None:
    paths = _write_dashboard_fixture(tmp_path)
    with patch("mpi.dashboard.pl.read_parquet", wraps=pl.read_parquet) as read:
        first = load_dashboard_data(paths)
        reads = read.call_count
        assert reads > 0
        second = load_dashboard_data(paths)
        assert read.call_count == reads
        assert first.signals.equals(second.signals)
        load_dashboard_data.clear()
        load_dashboard_data(paths)
        assert read.call_count == 2 * reads


def test_synthetic_app_renders_three_tabs_and_selectors(tmp_path: Path) -> None:
    paths = _write_dashboard_fixture(tmp_path)
    app_script = tmp_path / "app.py"
    app_script.write_text(
        "from pathlib import Path\n"
        "from mpi.dashboard import DashboardPaths, render_dashboard\n"
        "render_dashboard(DashboardPaths(\n"
        f"    bundle=Path({str(paths.bundle)!r}),\n"
        f"    m04=Path({str(paths.m04)!r}),\n"
        f"    m05=Path({str(paths.m05)!r}),\n"
        f"    m06=Path({str(paths.m06)!r}),\n"
        f"    m07=Path({str(paths.m07)!r}),\n"
        f"    m09=Path({str(paths.m09)!r}),\n"
        "))\n",
        encoding="utf-8",
    )

    app = AppTest.from_file(app_script).run(timeout=10)

    assert not app.exception
    assert app.title[0].value == "Injection Molding · Quality Prediction Under Process Shift"
    assert [tab.label for tab in app.tabs] == [
        "Data & process",
        "Prediction & generalization",
        "Reliability under shift",
    ]
    assert len(app.selectbox) >= 10
    assert any("not prospective untouched holdouts" in info.value for info in app.info)
    assert any("not confidence intervals" in caption.value for caption in app.caption)
    protocol_selector = next(box for box in app.selectbox if box.label == "Protocol")
    protocol_selector.select("secondary_id")
    app.run(timeout=10)
    assert not app.exception
    app.button[0].click().run(timeout=10)
    assert not app.exception
    for family in ("Ridge representations", "LightGBM representations"):
        next(box for box in app.selectbox if box.label == "Model family").select(family).run(
            timeout=10
        )
        for _ in range(3):
            representation = next(
                box for box in app.selectbox if box.label == "Model / representation"
            )
            assert representation.options == ["A", "B"]
            representation.select("B").run(timeout=10)
            assert not app.exception
            selected = next(box for box in app.selectbox if box.label == "Model / representation")
            assert selected.value == "B"
        app.selectbox(key="prediction_experiment").select(20).run(timeout=10)
        assert (
            next(box for box in app.selectbox if box.label == "Model / representation").value == "B"
        )
