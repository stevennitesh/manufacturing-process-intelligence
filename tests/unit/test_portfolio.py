# pyright: reportUnknownMemberType=false
from __future__ import annotations

from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path
from statistics import mean
from typing import cast
from xml.etree import ElementTree

import polars as pl
import pytest

from mpi.dashboard import DashboardData
from mpi.portfolio import render_report, scalar_comparison_svg
from scripts import render_portfolio_report


class _TableReader(HTMLParser):
    """Read visible table cells so comparisons do not depend on markup formatting."""

    def __init__(self, html: str) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.cell: list[str] | None = None
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.rows.append([])
        elif tag in {"th", "td"}:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self.cell is not None:
            self.rows[-1].append("".join(self.cell))
            self.cell = None


def _predictions(group: str, factors: dict[str, float]) -> pl.DataFrame:
    observations = [(15, 100.0, 1.0), (15, 101.0, -1.0), (20, 102.0, 3.0)] + [
        (23, 104.0, error) for error in (2.0, -2.0, 4.0)
    ]
    represented = [(15, 100.0, 0.1), (20, 102.0, -0.3), (23, 104.0, 0.2)]
    rows: list[dict[str, object]] = []
    for name, factor in factors.items():
        for protocol, samples in (("primary", observations), ("secondary_id", represented)):
            for index, (experiment, measured, error) in enumerate(samples):
                rows.append(
                    {
                        "unit_id": f"private-cycle-{experiment}-{index}",
                        "protocol": protocol,
                        "fold": (
                            f"holdout_experiment_{experiment}"
                            if protocol == "primary"
                            else "within_experiment"
                        ),
                        "experiment_id": experiment,
                        group: name,
                        "observed_weight_g": measured,
                        "predicted_weight_g": measured + error * factor,
                    }
                )
    return pl.DataFrame(rows)


def _metrics(predictions: pl.DataFrame, group: str) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for (protocol, fold, value), population in predictions.partition_by(
        "protocol", "fold", group, as_dict=True
    ).items():
        errors = [
            abs(cast(float, row["predicted_weight_g"]) - cast(float, row["observed_weight_g"]))
            for row in population.iter_rows(named=True)
        ]
        rows.append(
            {
                "protocol": protocol,
                "fold": fold,
                group: value,
                "mae_g": mean(errors),
            }
        )
    return pl.DataFrame(rows)


@pytest.fixture
def data() -> DashboardData:
    scalar = _predictions("model", {"mean": 1.5, "ridge": 1.2, "pls": 1.0})
    ridge = _predictions("representation", {"A": 1.4, "B": 1.5, "C-PCA": 1.3, "C-PLS": 1.2})
    lightgbm = _predictions("representation", {"A": 1.12, "B": 1.2, "C-PCA": 1.04, "C-PLS": 0.96})
    labeled = scalar.filter((pl.col("model") == "pls") & (pl.col("protocol") == "primary"))
    interval = (
        scalar.filter(pl.col("model") == "pls")
        .drop("model")
        .with_columns(
            pl.when(pl.col("experiment_id") == 15).then(1.0).otherwise(0.0).alias("covered"),
            (pl.col("experiment_id") / 100).alias("interval_width_g"),
            (pl.col("predicted_weight_g") + 0.5).alias("predicted_weight_g"),
        )
    )
    selections = [
        {
            "protocol": "primary",
            "fold": f"holdout_experiment_{experiment}",
            "selected_candidate": {"family": "pls" if experiment == 23 else "lightgbm"},
        }
        for experiment in (15, 20, 23)
    ] + [
        {
            "protocol": "secondary_id",
            "fold": "within_experiment",
            "selected_candidate": {"family": "lightgbm"},
        }
    ]
    return DashboardData(
        quality=labeled.select(
            "unit_id",
            pl.lit("weight").alias("characteristic"),
            pl.col("observed_weight_g").alias("measured_value"),
        ),
        context=labeled.select("unit_id", "experiment_id"),
        signals=pl.DataFrame(),
        scalar_metrics=_metrics(scalar, "model"),
        scalar_predictions=scalar,
        ridge_metrics=_metrics(ridge, "representation"),
        ridge_predictions=ridge,
        lightgbm_metrics=_metrics(lightgbm, "representation"),
        lightgbm_predictions=lightgbm,
        interval_metrics=pl.DataFrame(),
        interval_predictions=interval,
        uncertainty_run={
            "nominal_coverage": 0.9,
            "selections": selections,
            "screens": [
                {
                    "protocol": "primary",
                    "fold": f"holdout_experiment_{experiment}",
                    "inner_blocks": [
                        {"inner_fold": inner} for inner in (15, 20, 23) if inner != experiment
                    ],
                    "mean_relative_reduction": reduction,
                    "passed": reduction >= 0.1,
                }
                for experiment, reduction in ((15, 0.25), (20, 0.05), (23, 0.2))
            ],
        },
        importance=pl.DataFrame(),
        support=pl.DataFrame(),
    )


def _render(data: DashboardData, template: str) -> str:
    return render_report(
        data,
        template,
        source_version="synthetic-source",
        source_archive_sha256="synthetic-source-hash",
        membership_sha256="synthetic-membership-hash",
    )


def test_scalar_aggregations_match_independent_unequal_group_reference(data: DashboardData) -> None:
    result = _render(
        data,
        "@@PLS_ID_MAE@@|@@PLS_HELDOUT_MAE@@|@@PLS_EQUAL_MAE@@|@@ID_COUNT@@|@@HELDOUT_COUNT@@",
    )
    pooled = mean([1, 1, 3, 2, 2, 4])
    equal = mean([mean([1, 1]), 3, mean([2, 2, 4])])
    assert result == f"{mean([0.1, 0.3, 0.2]):.3f}|{pooled:.3f}|{equal:.3f}|3|6"
    rows = _TableReader(_render(data, "@@SCALAR_TABLE@@")).rows[1:]
    assert rows == [
        ["15", "Represented conditions", "1", "0.100", "+0.100"],
        ["15", "Unseen experiment", "2", "1.000", "+0.000"],
        ["20", "Represented conditions", "1", "0.300", "-0.300"],
        ["20", "Unseen experiment", "1", "3.000", "+3.000"],
        ["23", "Represented conditions", "1", "0.200", "+0.200"],
        ["23", "Unseen experiment", "3", "2.667", "+1.333"],
    ]


def test_experiment_means_and_between_fraction_match_reference(data: DashboardData) -> None:
    groups = ([100, 101], [102], [104, 104, 104])
    weights = [value for group in groups for value in group]
    overall = mean(weights)
    between = sum(len(group) * (mean(group) - overall) ** 2 for group in groups)
    total = sum((value - overall) ** 2 for value in weights)
    assert _render(data, "@@LABELED_COUNT@@|@@EXPERIMENT_COUNT@@|@@BETWEEN_PERCENT@@") == (
        f"6|3|{between / total * 100:.2f}"
    )
    rows = _TableReader(_render(data, "@@EXPERIMENT_TABLE@@")).rows[1:]
    assert [row[:3] for row in rows] == [
        ["15", "2", "100.500"],
        ["20", "1", "102.000"],
        ["23", "3", "104.000"],
    ]


def test_trajectory_comparison_uses_equal_experiment_weight(data: DashboardData) -> None:
    reference = mean([1, 3, mean([2, 2, 4])])
    rows = _TableReader(_render(data, "@@TRAJECTORY_TABLE@@")).rows[1:]
    assert [row[1:] for row in rows] == [
        [f"{reference * ridge:.3f}", f"{reference * lightgbm:.3f}"]
        for ridge, lightgbm in ((1.4, 1.12), (1.5, 1.2), (1.3, 1.04), (1.2, 0.96))
    ]


def test_interval_aggregations_and_selections_follow_saved_predictions(data: DashboardData) -> None:
    rows = _TableReader(_render(data, "@@INTERVAL_TABLE@@")).rows[1:]
    assert rows[0] == [
        "Represented conditions · pooled",
        "LightGBM",
        "3",
        "33.3% (1/3)",
        "0.193",
        "0.500",
    ]
    assert rows[1] == [
        "Unseen experiment · pooled",
        "LightGBM / PLS",
        "6",
        "33.3% (2/6)",
        "0.198",
        "2.333",
    ]
    assert rows[-1][1] == "PLS"
    assert _render(data, "@@ID_COVERAGE@@|@@HELDOUT_COVERAGE@@|@@NOMINAL_COVERAGE@@") == (
        "33.3|33.3|90.0"
    )
    assert _render(data, "@@ID_INTERVAL_WIDTH@@|@@HELDOUT_INTERVAL_WIDTH@@") == "0.193|0.198"
    gate = _TableReader(_render(data, "@@GATE_TABLE@@")).rows[1:]
    assert gate == [
        ["15", "20 and 23", "25.0%", "Yes"],
        ["20", "15 and 23", "5.0%", "No"],
        ["23", "15 and 20", "20.0%", "Yes"],
    ]


def test_static_scalar_preview_preserves_pooled_population_and_error(data: DashboardData) -> None:
    svg = scalar_comparison_svg(data)
    root = ElementTree.fromstring(svg)
    text = [node.text for node in root.findall(".//{http://www.w3.org/2000/svg}text")]
    pooled_error = mean([1, 1, 3, 2, 2, 4])
    represented_error = mean([0.1, 0.3, 0.2])
    assert [value for value in text if value is not None and value.endswith(" g")][:6] == [
        f"{factor * error:.3f} g"
        for factor in (1.5, 1.2, 1.0)
        for error in (represented_error, pooled_error)
    ]
    assert text.count("3 evaluated cycles") == 3
    assert text.count("6 evaluated cycles") == 3
    assert "pooled cycle weighting" in svg
    assert "separate fits" in svg
    assert "private-cycle-" not in svg


def test_renderer_exports_report_and_preview_from_same_saved_evidence(
    data: DashboardData, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = replace(
        data,
        uncertainty_run={
            **data.uncertainty_run,
            "source_version": "synthetic-source",
            "source_archive_sha256": "synthetic-archive",
            "membership_sha256": "synthetic-membership",
        },
    )
    monkeypatch.setattr(render_portfolio_report, "load_dashboard_data", lambda: saved)
    report = tmp_path / "report.html"
    preview = tmp_path / "preview.svg"
    monkeypatch.setattr(
        "sys.argv",
        ["render", "--output", str(report), "--figure-output", str(preview)],
    )
    render_portfolio_report.main()
    expected = render_report(
        saved,
        Path("docs/report/template.html").read_text(encoding="utf-8"),
        source_version="synthetic-source",
        source_archive_sha256="synthetic-archive",
        membership_sha256="synthetic-membership",
    )
    assert report.read_text(encoding="utf-8") == expected
    assert preview.read_text(encoding="utf-8") == scalar_comparison_svg(saved)


def test_small_nonzero_interval_coverage_remains_visible(data: DashboardData) -> None:
    experiment23 = data.interval_predictions.filter(
        (pl.col("protocol") == "primary") & (pl.col("experiment_id") == 23)
    ).head(1)
    repeated = (
        pl.concat([experiment23] * 303)
        .with_row_index("index")
        .with_columns((pl.col("index") == 0).cast(pl.Float64).alias("covered"))
        .drop("index")
    )
    other = data.interval_predictions.filter(
        ~((pl.col("protocol") == "primary") & (pl.col("experiment_id") == 23))
    )
    changed = replace(data, interval_predictions=pl.concat([other, repeated]))
    result = _render(changed, "@@INTERVAL_CHART@@\n@@INTERVAL_TABLE@@")
    rows = _TableReader(result).rows[1:]
    assert rows[-1][2:4] == ["303", "0.33% (1/303)"]
    assert "width:0.3300%" in result
    assert "experiment 23 (1/303 covered)" in result


def test_changed_evidence_changes_render_without_exposing_cycle_rows(data: DashboardData) -> None:
    changed_predictions = data.scalar_predictions.with_columns(
        (pl.col("predicted_weight_g") + 0.5).alias("predicted_weight_g")
    )
    changed = replace(
        data,
        scalar_predictions=changed_predictions,
        scalar_metrics=_metrics(changed_predictions, "model"),
    )
    template = "@@PLS_ID_MAE@@|@@PLS_HELDOUT_MAE@@|@@SCALAR_CHART@@|@@SCALAR_TABLE@@"
    original = _render(data, template)
    updated = _render(changed, template)
    assert original != updated
    assert updated.startswith("0.500|2.333|")
    assert "private-cycle-" not in updated
    assert "unit_id" not in updated
    assert "observed_weight_g" not in updated


@pytest.mark.parametrize("placeholder", ["@@UNKNOWN@@", "@@lowercase@@", "@@BROKEN"])
def test_unknown_or_unfilled_placeholders_fail(data: DashboardData, placeholder: str) -> None:
    with pytest.raises(ValueError, match="placeholder"):
        _render(data, placeholder)


def test_source_identity_is_html_escaped(data: DashboardData) -> None:
    result = render_report(
        data,
        "@@SOURCE_VERSION@@|@@SOURCE_SHA256@@|@@MEMBERSHIP_SHA256@@",
        source_version='<script>alert("source")</script>',
        source_archive_sha256="hash & archive",
        membership_sha256="<membership>",
    )
    assert result == (
        "&lt;script&gt;alert(&quot;source&quot;)&lt;/script&gt;"
        "|hash &amp; archive|&lt;membership&gt;"
    )


def test_missing_model_selection_fails_instead_of_inventing_family(data: DashboardData) -> None:
    changed = replace(data, uncertainty_run={**data.uncertainty_run, "selections": []})
    with pytest.raises(ValueError, match="saved model selection"):
        _render(changed, "@@INTERVAL_TABLE@@")
