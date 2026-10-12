# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Render aggregate saved evidence for the public, offline portfolio report."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from html import escape
from typing import cast

import polars as pl

from mpi.dashboard import (
    DashboardData,
    distance_gate_summary,
    experiment_summary,
    headline_mae,
    per_experiment_metrics,
    uncertainty_headline,
)

_POOLED_PRIMARY = "Unseen experiment — pooled cycles"
_EQUAL_PRIMARY = "Unseen experiment — equal experiment weight"
_POOLED_ID = "Represented conditions — pooled cycles"
_REPRESENTATIONS = {
    "A": "A · Scalars only",
    "B": "B · Scalars + trajectory summaries",
    "C-PCA": "C-PCA · Scalars + PCA signal components",
    "C-PLS": "C-PLS · Scalars + supervised PLS signal components",
}
_FAMILIES = {"mean": "Training mean", "ridge": "Ridge", "pls": "PLS", "lightgbm": "LightGBM"}
_PLACEHOLDER = re.compile(r"@@([^@]+)@@")


def _finite(value: object) -> float:
    result = float(cast(float, value))
    if not math.isfinite(result):
        raise ValueError("Report evidence contains a missing or non-finite aggregate.")
    return result


def _mae(headlines: pl.DataFrame, group: str, value: str, population: str) -> float:
    selected = headlines.filter((pl.col(group) == value) & (pl.col("population") == population))
    if selected.height != 1:
        raise ValueError(f"Expected one saved aggregate for {group}={value}, {population}.")
    return _finite(selected.item(0, "mae_g"))


def _table(caption: str, headings: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    header = "".join(f'<th scope="col">{escape(value)}</th>' for value in headings)
    body = "".join(
        "<tr>"
        + f'<th scope="row">{escape(row[0])}</th>'
        + "".join(f"<td>{escape(value)}</td>" for value in row[1:])
        + "</tr>"
        for row in rows
    )
    return (
        "<table>"
        f"<caption>{escape(caption)}</caption><thead><tr>{header}</tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _bar(label: str, value: str, percent: float, population: str) -> str:
    return (
        '<div class="chart-row">'
        f'<div class="chart-label">{escape(label)}</div><div class="bar-track">'
        f'<div class="bar {population}" style="width:{percent:.4f}%" aria-hidden="true"></div>'
        f'</div><div class="bar-value">{escape(value)}</div></div>'
    )


def _scalar_chart(data: DashboardData, headlines: pl.DataFrame) -> str:
    comparisons = [
        (model, protocol, population, _mae(headlines, "model", model, population))
        for model in ("mean", "ridge", "pls")
        for protocol, population in (("secondary_id", _POOLED_ID), ("primary", _POOLED_PRIMARY))
    ]
    axis_max = max(1.2, math.ceil(max(row[3] for row in comparisons) * 10) / 10)
    chart = [
        '<div class="aggregate-chart" role="group" aria-label="Pooled scalar-model mean '
        'absolute error in grams. Lower is better.">'
    ]
    for model, protocol, _, value in comparisons:
        represented = protocol == "secondary_id"
        n = data.scalar_predictions.filter(
            (pl.col("model") == model) & (pl.col("protocol") == protocol)
        ).height
        population_label = "Represented conditions" if represented else "Unseen experiment"
        label = f"{_FAMILIES[model]} · {population_label} (n={n:,})"
        chart.append(
            _bar(
                label,
                f"{value:.3f} g",
                value / axis_max * 100,
                "represented" if represented else "heldout",
            )
        )
    chart.append(
        f'<div class="chart-axis"><span>0 g</span><span>{axis_max:.1f} g · lower is better</span>'
        "</div></div>"
    )
    return "".join(chart)


def _scalar_table(data: DashboardData) -> str:
    predictions = data.scalar_predictions.filter(pl.col("model") == "pls")
    metrics = per_experiment_metrics(predictions, "model")
    bias = predictions.group_by("protocol", "experiment_id").agg(
        (pl.col("predicted_weight_g") - pl.col("observed_weight_g")).mean().alias("bias_g")
    )
    metrics = metrics.join(bias, on=["protocol", "experiment_id"], validate="1:1")
    rows: list[tuple[str, ...]] = []
    for experiment in metrics["experiment_id"].unique().sort().to_list():
        for protocol, population in (
            ("secondary_id", "Represented conditions"),
            ("primary", "Unseen experiment"),
        ):
            selected = metrics.filter(
                (pl.col("experiment_id") == experiment) & (pl.col("protocol") == protocol)
            )
            if selected.height != 1:
                raise ValueError(f"Missing PLS experiment evidence: {protocol}, {experiment}.")
            row = selected.row(0, named=True)
            rows.append(
                (
                    str(experiment),
                    population,
                    f"{cast(int, row['n']):,}",
                    f"{_finite(row['mae_g']):.3f}",
                    f"{_finite(row['bias_g']):+.3f}",
                )
            )
    return _table(
        "Scalar PLS by experiment. Bias is mean predicted minus measured weight; all errors in g.",
        ("Experiment", "Evaluation population", "Cycles (n)", "MAE (g)", "Signed bias (g)"),
        rows,
    )


def _experiment_table(summary: pl.DataFrame) -> str:
    roles = {
        15: "Moisture-content experiment",
        20: "Moisture-content experiment",
        23: "Mold-temperature experiment",
    }
    rows = [
        (
            str(row["experiment_id"]),
            f"{cast(int, row['labeled_cycles']):,}",
            f"{_finite(row['mean_weight_g']):.3f}",
            roles[cast(int, row["experiment_id"])],
        )
        for row in summary.iter_rows(named=True)
    ]
    return _table(
        "Labeled Dataset 2 cycles and observed group means. "
        "Context describes source experiment roles.",
        ("Experiment", "Labeled cycles", "Mean part weight (g)", "Controlled source context"),
        rows,
    )


def _trajectory_table(data: DashboardData) -> str:
    ridge = headline_mae(data.ridge_metrics, data.ridge_predictions, "representation")
    lightgbm = headline_mae(data.lightgbm_metrics, data.lightgbm_predictions, "representation")
    rows = [
        (
            label,
            f"{_mae(ridge, 'representation', representation, _EQUAL_PRIMARY):.3f}",
            f"{_mae(lightgbm, 'representation', representation, _EQUAL_PRIMARY):.3f}",
        )
        for representation, label in _REPRESENTATIONS.items()
    ]
    return _table(
        "Whole-experiment transfer: mean MAE with equal weight for each held-out experiment.",
        ("Predictor representation", "Ridge MAE (g)", "LightGBM MAE (g)"),
        rows,
    )


def _coverage_text(coverage: float) -> str:
    percent = coverage * 100
    return f"{percent:.2f}%" if 0 < percent < 1 else f"{percent:.1f}%"


def _selected_family(run: dict[str, object], protocol: str, fold: str | None = None) -> str:
    selections = cast(list[dict[str, object]], run["selections"])
    selected = [
        selection
        for selection in selections
        if selection["protocol"] == protocol and (fold is None or selection["fold"] == fold)
    ]
    if not selected or (fold is not None and len(selected) != 1):
        raise ValueError(f"Missing or ambiguous saved model selection: {protocol}, {fold}.")
    families = sorted(
        {
            _FAMILIES[str(cast(dict[str, object], selection["selected_candidate"])["family"])]
            for selection in selected
        }
    )
    return " / ".join(families)


def _interval_evidence(data: DashboardData) -> tuple[str, str]:
    headline = uncertainty_headline(data)
    populations: list[tuple[str, str, str | None, pl.DataFrame]] = [
        (
            "Represented conditions · pooled",
            "secondary_id",
            "within_experiment",
            data.interval_predictions.filter(pl.col("protocol") == "secondary_id"),
        ),
        (
            "Unseen experiment · pooled",
            "primary",
            None,
            data.interval_predictions.filter(pl.col("protocol") == "primary"),
        ),
    ]
    primary = data.interval_predictions.filter(pl.col("protocol") == "primary")
    for (fold,), rows in primary.partition_by("fold", as_dict=True).items():
        populations.append(
            (
                f"Unseen experiment · experiment {str(fold).rsplit('_', maxsplit=1)[-1]}",
                "primary",
                str(fold),
                rows,
            )
        )
    populations[2:] = sorted(populations[2:], key=lambda row: row[0])
    nominal = _finite(data.uncertainty_run["nominal_coverage"]) * 100
    chart = [
        f'<div class="aggregate-chart" style="--coverage-target:{nominal:.4f}%" '
        'role="group" aria-label="Observed prediction-interval '
        f'coverage compared with the {nominal:.1f}% nominal target.">'
    ]
    table_rows: list[tuple[str, ...]] = []
    for label, protocol, fold, predictions in populations:
        if predictions.is_empty():
            raise ValueError(f"Missing prediction-interval evidence: {label}.")
        pooled = label.endswith("pooled")
        coverage = (
            headline[f"{protocol}_empirical_coverage"]
            if pooled
            else _finite(predictions["covered"].mean())
        )
        width = (
            headline[f"{protocol}_mean_width_g"]
            if pooled
            else _finite(predictions["interval_width_g"].mean())
        )
        covered = int(_finite(predictions["covered"].sum()))
        mae = _finite(
            (predictions["predicted_weight_g"] - predictions["observed_weight_g"]).abs().mean()
        )
        coverage_label = _coverage_text(coverage)
        chart.append(
            _bar(
                f"{label} ({covered:,}/{predictions.height:,} covered)",
                coverage_label,
                coverage * 100,
                "represented" if protocol == "secondary_id" else "heldout",
            )
        )
        table_rows.append(
            (
                label,
                _selected_family(data.uncertainty_run, protocol, fold),
                f"{predictions.height:,}",
                f"{coverage_label} ({covered:,}/{predictions.height:,})",
                f"{width:.3f}",
                f"{mae:.3f}",
            )
        )
    chart.append(
        '<div class="chart-axis"><span>0%</span>'
        f"<span>Target {nominal:.1f}% · 100%</span></div></div>"
    )
    table = _table(
        "M07 selected scalar pipelines and prediction intervals; "
        "separate fits from the M04 baseline.",
        (
            "Evaluation population",
            "Selected family",
            "Cycles (n)",
            "Coverage",
            "Mean width (g)",
            "MAE (g)",
        ),
        table_rows,
    )
    return "".join(chart), table


def _gate_table(data: DashboardData) -> str:
    rows = [
        (
            str(row["Experiment excluded from development"]),
            str(row["Experiments used for screening"]),
            f"{_finite(row['Mean development MAE reduction']) * 100:.1f}%",
            str(row["Criterion met?"]),
        )
        for row in distance_gate_summary(data.uncertainty_run).iter_rows(named=True)
    ]
    if not rows:
        raise ValueError("Missing saved primary development-gate evidence.")
    return _table(
        "Development distance gate. These outcomes describe screening data, "
        "not final held-out cycles.",
        (
            "Experiment excluded",
            "Screening experiments",
            "Mean relative MAE reduction",
            "Criterion met?",
        ),
        rows,
    )


def render_report(
    data: DashboardData,
    template: str,
    *,
    source_version: str,
    source_archive_sha256: str,
    membership_sha256: str,
) -> str:
    """Substitute aggregate evidence into a template without writing or fitting models."""
    summary, between_fraction = experiment_summary(data)
    scalar = headline_mae(data.scalar_metrics, data.scalar_predictions, "model")
    intervals = uncertainty_headline(data)
    interval_chart, interval_table = _interval_evidence(data)
    pls_predictions = data.scalar_predictions.filter(pl.col("model") == "pls")
    experiment23 = pls_predictions.filter(
        (pl.col("protocol") == "primary") & (pl.col("experiment_id") == 23)
    )
    interval23 = data.interval_predictions.filter(
        (pl.col("protocol") == "primary") & (pl.col("experiment_id") == 23)
    )
    experiment23_bias = _finite(
        (experiment23["predicted_weight_g"] - experiment23["observed_weight_g"]).mean()
    )
    id_covered = _finite(
        data.interval_predictions.filter(pl.col("protocol") == "secondary_id")["covered"].sum()
    )
    heldout_covered = _finite(
        data.interval_predictions.filter(pl.col("protocol") == "primary")["covered"].sum()
    )
    values = {
        "LABELED_COUNT": f"{cast(int, summary['labeled_cycles'].sum()):,}",
        "EXPERIMENT_COUNT": str(summary.height),
        "EXP23_COUNT": f"{experiment23.height:,}",
        "BETWEEN_PERCENT": f"{between_fraction * 100:.2f}",
        "PLS_ID_MAE": f"{_mae(scalar, 'model', 'pls', _POOLED_ID):.3f}",
        "PLS_HELDOUT_MAE": f"{_mae(scalar, 'model', 'pls', _POOLED_PRIMARY):.3f}",
        "PLS_EQUAL_MAE": f"{_mae(scalar, 'model', 'pls', _EQUAL_PRIMARY):.3f}",
        "PLS_EXP23_BIAS": f"{abs(experiment23_bias):.3f}",
        "ID_COUNT": f"{pls_predictions.filter(pl.col('protocol') == 'secondary_id').height:,}",
        "HELDOUT_COUNT": f"{pls_predictions.filter(pl.col('protocol') == 'primary').height:,}",
        "ID_COVERAGE": f"{intervals['secondary_id_empirical_coverage'] * 100:.1f}",
        "HELDOUT_COVERAGE": f"{intervals['primary_empirical_coverage'] * 100:.1f}",
        "ID_COVERED_COUNT": f"{int(id_covered):,}",
        "HELDOUT_COVERED_COUNT": f"{int(heldout_covered):,}",
        "EXP23_COVERED_COUNT": f"{int(_finite(interval23['covered'].sum())):,}",
        "EXP23_COVERAGE": f"{_finite(interval23['covered'].mean()) * 100:.2f}",
        "NOMINAL_COVERAGE": f"{_finite(data.uncertainty_run['nominal_coverage']) * 100:.1f}",
        "SCALAR_CHART": _scalar_chart(data, scalar),
        "SCALAR_TABLE": _scalar_table(data),
        "EXPERIMENT_TABLE": _experiment_table(summary),
        "TRAJECTORY_TABLE": _trajectory_table(data),
        "INTERVAL_CHART": interval_chart,
        "INTERVAL_TABLE": interval_table,
        "GATE_TABLE": _gate_table(data),
        "SOURCE_VERSION": escape(source_version),
        "SOURCE_SHA256": escape(source_archive_sha256),
        "MEMBERSHIP_SHA256": escape(membership_sha256),
    }
    unknown = set(_PLACEHOLDER.findall(template)) - values.keys()
    if unknown:
        raise ValueError(f"Unknown report placeholders: {', '.join(sorted(unknown))}.")
    result = _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)
    if "@@" in result:
        raise ValueError("Unfilled report placeholder.")
    return result
