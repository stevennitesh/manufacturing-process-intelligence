# pyright: reportUnknownMemberType=false
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast
from unittest.mock import patch

import polars as pl
import pytest
from streamlit.testing.v1 import AppTest

from mpi.dashboard import (
    DashboardPaths,
    coverage_summary,
    cycle_signal_summary,
    distance_gate_summary,
    experiment_summary,
    headline_mae,
    load_dashboard_data,
    observed_vs_predicted_figure,
    per_experiment_metrics,
    prediction_headline,
    support_heatmap_table,
    uncertainty_headline,
)


def test_cycle_summary_preserves_native_grid_and_pointwise_spread() -> None:
    signals = pl.DataFrame(
        {
            "sample_index": [1, 0, 1, 0, 1, 0],
            "elapsed_time_seconds": [0.004, 0.0] * 3,
            "injection_pressure": [30.0, 0.0, 50.0, 10.0, 100.0, 20.0],
            "injection_flow": [3.0, 0.0, 5.0, 1.0, 10.0, 2.0],
        }
    )
    summary = cycle_signal_summary(signals)
    assert summary["elapsed_time_seconds"].to_list() == [0.0, 0.004]
    # Linear percentiles: 20% of the way between adjacent sorted values.
    for channel, scale in (("injection_pressure", 1), ("injection_flow", 0.1)):
        for stat, expected in {
            "min": [0, 30],
            "p10": [2, 34],
            "median": [10, 50],
            "p90": [18, 90],
            "max": [20, 100],
        }.items():
            assert summary[f"{channel}_{stat}"].to_list() == pytest.approx(
                [value * scale for value in expected]
            )


def test_observed_vs_predicted_uses_one_range_and_equal_scale() -> None:
    selected = pl.DataFrame(
        {
            "observed_weight_g": [114.0, 114.2],
            "predicted_weight_g": [113.1, 113.4],
        }
    )
    figure = observed_vs_predicted_figure(selected, title="Example")
    figure_json = cast(dict[str, object], figure.to_plotly_json())
    layout = cast(dict[str, object], figure_json["layout"])
    xaxis = cast(dict[str, object], layout["xaxis"])
    yaxis = cast(dict[str, object], layout["yaxis"])

    assert xaxis["range"] == yaxis["range"]
    assert xaxis["range"] == pytest.approx((112.99, 114.31))
    assert yaxis["scaleanchor"] == "x"
    assert yaxis["scaleratio"] == 1
    assert layout["height"] == 600


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
    for directory in (paths.m04, paths.m05, paths.m06):
        (directory / "run.json").write_text(json.dumps(identity), encoding="utf-8")
    uncertainty_run = {
        **identity,
        "nominal_coverage": 0.9,
        "development_screen": {
            "retained_fraction": 0.5,
            "primary_fold_minimum_mean_relative_reduction": 0.2,
        },
        "selections": [
            {
                "protocol": "primary",
                "fold": "holdout_experiment_15",
                "selected_candidate": {"family": "pls"},
            },
            {
                "protocol": "secondary_id",
                "fold": "within_experiment",
                "selected_candidate": {"family": "lightgbm"},
            },
        ],
        "screens": [
            {
                "protocol": "primary",
                "fold": "holdout_experiment_15",
                "inner_blocks": [{"inner_fold": 20}],
                "mean_relative_reduction": 0.25,
                "passed": True,
            },
            {
                "protocol": "primary",
                "fold": "holdout_experiment_20",
                "inner_blocks": [{"inner_fold": 15}],
                "mean_relative_reduction": 0.05,
                "passed": False,
            },
        ],
        "m8_eligible": False,
    }
    (paths.m07 / "run.json").write_text(json.dumps(uncertainty_run), encoding="utf-8")

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

    _metrics("model", ("mean", "ridge", "pls")).write_parquet(paths.m04 / "metrics.parquet")
    _predictions("model", ("mean", "ridge", "pls")).write_parquet(paths.m04 / "predictions.parquet")
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

    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    (paths.m09 / "run.json").write_text(
        json.dumps(
            {
                **identity,
                "m7_run_sha256": sha256(paths.m07 / "run.json"),
                "m7_prediction_sha256": sha256(paths.m07 / "evaluation_predictions.parquet"),
            }
        ),
        encoding="utf-8",
    )

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
        "Unseen experiment — equal experiment weight",
        "Unseen experiment — pooled cycles",
        "Represented conditions — pooled cycles",
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
        "Unseen experiment · experiment 23",
        "Represented conditions · experiment 23",
        "Represented conditions · pooled",
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


def test_loaded_summaries_follow_fixture_values_and_membership(tmp_path: Path) -> None:
    data = load_dashboard_data(_write_dashboard_fixture(tmp_path))

    experiments, between_fraction = experiment_summary(data)
    assert experiments.to_dicts() == [
        {"experiment_id": 15, "labeled_cycles": 1, "mean_weight_g": 100.0},
        {"experiment_id": 20, "labeled_cycles": 1, "mean_weight_g": 101.0},
    ]
    assert between_fraction == pytest.approx(1.0)
    prediction = prediction_headline(data)
    assert prediction["Represented conditions — pooled cycles"] == pytest.approx(0.15)
    assert prediction["Unseen experiment — pooled cycles"] == pytest.approx(1.5)
    assert prediction["Unseen experiment — equal experiment weight"] == pytest.approx(1.5)
    uncertainty = uncertainty_headline(data)
    assert uncertainty["primary_empirical_coverage"] == 0.0
    assert uncertainty["secondary_id_mean_width_g"] == pytest.approx(0.2)
    gate = distance_gate_summary(data.uncertainty_run)
    assert gate["Mean development MAE reduction"].to_list() == pytest.approx([0.25, 0.05])
    assert gate["Experiment excluded from development"].to_list() == [15, 20]
    assert gate["Experiments used for screening"].to_list() == ["20", "15"]


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
    with pytest.raises(FileNotFoundError, match=r"run_uncertainty_shift\.py") as error:
        load_dashboard_data(DashboardPaths(bundle=tmp_path / "missing"))
    message = str(error.value)
    assert "From the repository root" in message
    assert message.index("data acquire injection_molding") < message.index(
        "data prepare injection_molding"
    )


@pytest.mark.parametrize("field", ["source_archive_sha256", "membership_sha256"])
def test_loader_rejects_mixed_milestone_lineage(tmp_path: Path, field: str) -> None:
    paths = _write_dashboard_fixture(tmp_path)
    record_path = paths.m05 / "run.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record[field] = "different-run"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match=f"Artifact lineage mismatch:.*{field}"):
        load_dashboard_data(paths)


@pytest.mark.parametrize("artifact", ["run", "predictions"])
def test_loader_rejects_m7_artifact_hash_mismatch(tmp_path: Path, artifact: str) -> None:
    paths = _write_dashboard_fixture(tmp_path)
    if artifact == "run":
        record_path = paths.m07 / "run.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["changed_after_explanation"] = True
        record_path.write_text(json.dumps(record), encoding="utf-8")
        expected_field = "m7_run_sha256"
    else:
        prediction_path = paths.m07 / "evaluation_predictions.parquet"
        pl.read_parquet(prediction_path).with_columns(
            (pl.col("predicted_weight_g") + 0.01).alias("predicted_weight_g")
        ).write_parquet(prediction_path)
        expected_field = "m7_prediction_sha256"

    with pytest.raises(ValueError, match=expected_field):
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
    assert app.title[0].value == "Injection Molding · Part-Weight Prediction Under Process Shift"
    assert [tab.label for tab in app.tabs] == [
        "Data & process",
        "Prediction & generalization",
        "Reliability under shift",
    ]
    assert len(app.selectbox) >= 10
    assert any("not confidence intervals" in caption.value for caption in app.caption)
    rendered_markdown = " ".join("\n".join(markdown.value for markdown in app.markdown).split())
    subheaders = " ".join(subheader.value for subheader in app.subheader)
    assert "Study flow" in subheaders
    assert "Observed experiment groups" in subheaders
    assert "weight never enters as a predictor" in rendered_markdown
    assert "harder transfer question" in rendered_markdown
    assert "not prospective untouched holdouts" in rendered_markdown
    assert "100.00% of observed weight variation" in " ".join(info.value for info in app.info)
    assert "completed-cycle weight estimate" in rendered_markdown
    assert "What was learned" in subheaders
    assert "Selective-measurement development gate" in subheaders
    assert "Which inputs did the uncertainty-study models rely on?" in subheaders
    assert any("loaded all-fold gate failed" in warning.value for warning in app.warning)
    assert "Expand the labeled operating envelope" in rendered_markdown
    assert "Future monitoring and intended-use details" in " ".join(
        expander.label for expander in app.expander
    )
    assert "Method and reading guide" in " ".join(expander.label for expander in app.expander)
    assert (
        next(box for box in app.selectbox if box.label == "Model / representation").value == "pls"
    )
    assert app.selectbox(key="importance_experiment").value == 20
    captions = " ".join(caption.value for caption in app.caption)
    assert "Mean signed error (predicted - measured)" in captions
    assert "they are not measurements of screening performance" in captions
    assert "exchangeability assumption" in captions
    all_visible_text = " ".join(
        [rendered_markdown, captions]
        + [element.value for element in (*app.success, *app.error, *app.info, *app.warning)]
    )
    assert "0.150 g" in all_visible_text
    assert "1.500 g" in all_visible_text
    assert "0.114" not in all_visible_text
    assert "70.45%" not in all_visible_text
    assert "0.550 g" not in all_visible_text
    protocol_selector = app.selectbox(key="prediction_protocol")
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
            assert representation.options == [
                "Scalars only",
                "Scalars + trajectory summaries",
            ]
            representation.select("Scalars + trajectory summaries").run(timeout=10)
            assert not app.exception
            selected = next(box for box in app.selectbox if box.label == "Model / representation")
            assert selected.value == "B"
        app.selectbox(key="prediction_experiment").select(20).run(timeout=10)
        assert (
            next(box for box in app.selectbox if box.label == "Model / representation").value == "B"
        )


def test_synthetic_app_does_not_claim_failures_when_loaded_outcomes_reverse(
    tmp_path: Path,
) -> None:
    paths = _write_dashboard_fixture(tmp_path)

    scalar_predictions = pl.read_parquet(paths.m04 / "predictions.parquet").with_columns(
        pl.when(pl.col("protocol") == "primary")
        .then(pl.col("observed_weight_g") + 0.05)
        .otherwise(pl.col("observed_weight_g") + 1.0)
        .alias("predicted_weight_g")
    )
    scalar_predictions.write_parquet(paths.m04 / "predictions.parquet")
    pl.read_parquet(paths.m04 / "metrics.parquet").with_columns(
        pl.when(pl.col("protocol") == "primary").then(0.05).otherwise(1.0).alias("mae_g")
    ).write_parquet(paths.m04 / "metrics.parquet")

    for directory in (paths.m05, paths.m06):
        pl.read_parquet(directory / "metrics.parquet").with_columns(
            pl.when((pl.col("protocol") == "primary") & (pl.col("representation") == "B"))
            .then(0.01)
            .otherwise(pl.col("mae_g"))
            .alias("mae_g")
        ).write_parquet(directory / "metrics.parquet")

    interval_path = paths.m07 / "evaluation_predictions.parquet"
    pl.read_parquet(interval_path).with_columns(
        pl.when(pl.col("protocol") == "primary").then(1.0).otherwise(0.0).alias("covered")
    ).write_parquet(interval_path)
    pl.read_parquet(paths.m07 / "metrics.parquet").with_columns(
        pl.when(pl.col("protocol") == "primary")
        .then(1.0)
        .otherwise(0.0)
        .alias("empirical_coverage")
    ).write_parquet(paths.m07 / "metrics.parquet")

    run_path = paths.m07 / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["m8_eligible"] = True
    for screen in run["screens"]:
        screen["mean_relative_reduction"] = 0.3
        screen["passed"] = True
    run_path.write_text(json.dumps(run), encoding="utf-8")
    m9_path = paths.m09 / "run.json"
    m9 = json.loads(m9_path.read_text(encoding="utf-8"))
    m9["m7_run_sha256"] = hashlib.sha256(run_path.read_bytes()).hexdigest()
    m9["m7_prediction_sha256"] = hashlib.sha256(interval_path.read_bytes()).hexdigest()
    m9_path.write_text(json.dumps(m9), encoding="utf-8")

    app_script = tmp_path / "reversed_app.py"
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
    visible = " ".join(
        [element.value for element in app.markdown]
        + [element.value for element in (*app.success, *app.error, *app.info, *app.warning)]
        + [element.value for element in app.subheader]
    )
    assert "Error was lower when a complete experiment was withheld" in visible
    assert "Coverage was not lower for unseen experiments" in visible
    assert "saved development gate passed" in visible
    assert "loaded results do not show lower coverage" in visible
    for false_claim in (
        "MAE increased",
        "did not establish new-condition transfer",
        "none of these Ridge/LightGBM representations beat",
        "coverage collapsed",
        "development distance gate failed",
        "gate stopped",
        "only 0.0% under",
    ):
        assert false_claim not in visible
