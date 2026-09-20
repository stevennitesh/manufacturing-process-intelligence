# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Offline presentation of the saved Dataset 2 portfolio evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np
import plotly.graph_objects as go
import plotly.subplots as subplots
import polars as pl
import streamlit as st

from mpi.models.trajectory_representations import regression_metrics


@dataclass(frozen=True)
class DashboardPaths:
    """The current prepared bundle and milestone artifact locations."""

    bundle: Path = Path("data/processed/injection_molding/dataset2")
    m04: Path = Path("artifacts/m04")
    m05: Path = Path("artifacts/m05")
    m06: Path = Path("artifacts/m06")
    m07: Path = Path("artifacts/m07")
    m09: Path = Path("artifacts/m09")


@dataclass(frozen=True)
class DashboardData:
    quality: pl.DataFrame
    context: pl.DataFrame
    signals: pl.DataFrame
    scalar_metrics: pl.DataFrame
    scalar_predictions: pl.DataFrame
    ridge_metrics: pl.DataFrame
    ridge_predictions: pl.DataFrame
    lightgbm_metrics: pl.DataFrame
    lightgbm_predictions: pl.DataFrame
    interval_metrics: pl.DataFrame
    interval_predictions: pl.DataFrame
    uncertainty_run: dict[str, object]
    importance: pl.DataFrame
    support: pl.DataFrame


REPRODUCTION_COMMANDS: Final = """Prepare and reproduce the saved evidence, then retry:

```powershell
uv run mpi data prepare injection_molding --raw-root data/raw/injection_molding
uv run python scripts/create_injection_molding_memberships.py
uv run python scripts/run_scalar_baselines.py
uv run python scripts/run_trajectory_representations.py
uv run python scripts/run_lightgbm_comparison.py
uv run python scripts/run_uncertainty_shift.py
uv run python scripts/run_predictive_explanation.py
```
"""
DEFAULT_PATHS: Final = DashboardPaths()
PROTOCOL_LABELS: Final = {
    "primary": "Unseen experiment — whole experiment held out",
    "secondary_id": "Represented conditions — random cycles held out",
}
MODEL_LABELS: Final = {
    "mean": "Training mean",
    "ridge": "Ridge regression",
    "pls": "Partial least squares (PLS)",
    "lightgbm": "LightGBM",
}
REPRESENTATION_LABELS: Final = {
    "A": "Scalars only",
    "B": "Scalars + trajectory summaries",
    "C-PCA": "Scalars + PCA signal components",
    "C-PLS": "Scalars + supervised PLS signal components",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _required_files(paths: DashboardPaths) -> tuple[Path, ...]:
    return (
        paths.bundle / "metadata.json",
        paths.bundle / "quality.parquet",
        paths.bundle / "context.parquet",
        paths.bundle / "signals.parquet",
        paths.m04 / "metrics.parquet",
        paths.m04 / "predictions.parquet",
        paths.m04 / "run.json",
        paths.m05 / "metrics.parquet",
        paths.m05 / "predictions.parquet",
        paths.m05 / "run.json",
        paths.m06 / "metrics.parquet",
        paths.m06 / "predictions.parquet",
        paths.m06 / "run.json",
        paths.m07 / "metrics.parquet",
        paths.m07 / "evaluation_predictions.parquet",
        paths.m07 / "run.json",
        paths.m09 / "permutation_importance.parquet",
        paths.m09 / "feature_support.parquet",
        paths.m09 / "run.json",
    )


@st.cache_data(show_spinner=False, hash_funcs={DashboardPaths: repr}, max_entries=1)
def load_dashboard_data(paths: DashboardPaths = DEFAULT_PATHS) -> DashboardData:
    """Cache a local snapshot; clear explicitly after regenerating saved evidence."""
    missing = [path for path in _required_files(paths) if not path.is_file()]
    if missing:
        listed = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            f"Dashboard inputs are missing:\n{listed}\n\n{REPRODUCTION_COMMANDS}"
        )
    try:
        metadata = json.loads((paths.bundle / "metadata.json").read_text(encoding="utf-8"))
        runs = {
            directory: json.loads((directory / "run.json").read_text(encoding="utf-8"))
            for directory in (paths.m04, paths.m05, paths.m06, paths.m07, paths.m09)
        }
        identity = {
            "dataset": metadata.get("dataset"),
            "source_version": metadata.get("source_version"),
            "source_archive_sha256": metadata.get("archive_sha256"),
            "membership_sha256": runs[paths.m07].get("membership_sha256"),
        }
        for directory, record in runs.items():
            for field, expected in identity.items():
                if not expected or record.get(field) != expected:
                    raise ValueError(
                        f"Artifact lineage mismatch: {directory / 'run.json'} ({field}). "
                        "Reproduce the milestone artifacts from the same prepared source and "
                        "fixed evaluation memberships, then reload saved evidence."
                    )
        m9_run = runs[paths.m09]
        for field, current_path in (
            ("m7_run_sha256", paths.m07 / "run.json"),
            ("m7_prediction_sha256", paths.m07 / "evaluation_predictions.parquet"),
        ):
            expected_hash = m9_run.get(field)
            if not expected_hash or expected_hash != _sha256(current_path):
                raise ValueError(
                    f"Artifact lineage mismatch: {paths.m09 / 'run.json'} ({field}). "
                    "Reproduce the uncertainty and predictive-explanation artifacts from the "
                    "same saved files, then reload saved evidence."
                )
        return DashboardData(
            quality=pl.read_parquet(paths.bundle / "quality.parquet"),
            context=pl.read_parquet(paths.bundle / "context.parquet"),
            signals=pl.read_parquet(paths.bundle / "signals.parquet"),
            scalar_metrics=pl.read_parquet(paths.m04 / "metrics.parquet"),
            scalar_predictions=pl.read_parquet(paths.m04 / "predictions.parquet"),
            ridge_metrics=pl.read_parquet(paths.m05 / "metrics.parquet"),
            ridge_predictions=pl.read_parquet(paths.m05 / "predictions.parquet"),
            lightgbm_metrics=pl.read_parquet(paths.m06 / "metrics.parquet"),
            lightgbm_predictions=pl.read_parquet(paths.m06 / "predictions.parquet"),
            interval_metrics=pl.read_parquet(paths.m07 / "metrics.parquet"),
            interval_predictions=pl.read_parquet(paths.m07 / "evaluation_predictions.parquet"),
            uncertainty_run=cast(dict[str, object], runs[paths.m07]),
            importance=pl.read_parquet(paths.m09 / "permutation_importance.parquet"),
            support=pl.read_parquet(paths.m09 / "feature_support.parquet"),
        )
    except (OSError, json.JSONDecodeError, pl.exceptions.PolarsError) as error:
        raise ValueError(f"Could not read dashboard inputs: {error}") from error


def headline_mae(metrics: pl.DataFrame, predictions: pl.DataFrame, group: str) -> pl.DataFrame:
    """Return equal-fold primary, pooled primary, and separately fitted pooled ID MAE."""
    rows: list[dict[str, object]] = []
    for value in metrics[group].unique(maintain_order=True).to_list():
        primary = metrics.filter((pl.col(group) == value) & (pl.col("protocol") == "primary"))
        primary_predictions = predictions.filter(
            (pl.col(group) == value) & (pl.col("protocol") == "primary")
        )
        secondary = metrics.filter(
            (pl.col(group) == value)
            & (pl.col("protocol") == "secondary_id")
            & (pl.col("fold") == "within_experiment")
        )
        rows.extend(
            (
                {
                    group: value,
                    "population": "Unseen experiment — equal experiment weight",
                    "mae_g": cast(float, primary["mae_g"].mean()),
                },
                {
                    group: value,
                    "population": "Unseen experiment — pooled cycles",
                    "mae_g": float(
                        np.mean(
                            np.abs(
                                primary_predictions["observed_weight_g"].to_numpy()
                                - primary_predictions["predicted_weight_g"].to_numpy()
                            )
                        )
                    ),
                },
                {
                    group: value,
                    "population": "Represented conditions — pooled cycles",
                    "mae_g": cast(float, secondary.item(0, "mae_g")),
                },
            )
        )
    return pl.DataFrame(rows)


def per_experiment_metrics(predictions: pl.DataFrame, group: str) -> pl.DataFrame:
    """Compute presentation-only metrics while retaining protocol and experiment identity."""
    metric_rows: list[dict[str, object]] = []
    for (protocol, group_value, experiment), rows in predictions.partition_by(
        ["protocol", group, "experiment_id"], as_dict=True
    ).items():
        mae, rmse, r2 = regression_metrics(
            rows["observed_weight_g"].to_numpy(), rows["predicted_weight_g"].to_numpy()
        )
        metric_rows.append(
            {
                "protocol": protocol,
                group: group_value,
                "experiment_id": experiment,
                "n": rows.height,
                "mae_g": mae,
                "rmse_g": rmse,
                "r2": r2,
            }
        )
    return pl.DataFrame(metric_rows).sort("protocol", group, "experiment_id")


def weight_rows(data: DashboardData) -> pl.DataFrame:
    """Join physical weight to source experiment identity once for presentation."""
    return (
        data.quality.filter(pl.col("characteristic") == "weight")
        .select("unit_id", pl.col("measured_value").alias("weight_g"))
        .join(data.context.select("unit_id", "experiment_id"), on="unit_id", validate="1:1")
    )


def experiment_summary(data: DashboardData) -> tuple[pl.DataFrame, float]:
    """Summarize observed experiment membership and between-group weight variation."""
    weights = weight_rows(data)
    summary = (
        weights.group_by("experiment_id")
        .agg(pl.len().alias("labeled_cycles"), pl.mean("weight_g").alias("mean_weight_g"))
        .sort("experiment_id")
    )
    overall_mean = cast(float, weights["weight_g"].mean())
    total_ss = cast(float, ((weights["weight_g"] - overall_mean) ** 2).sum())
    between_ss = sum(
        cast(int, row["labeled_cycles"]) * (cast(float, row["mean_weight_g"]) - overall_mean) ** 2
        for row in summary.iter_rows(named=True)
    )
    between_fraction = between_ss / total_ss if total_ss else 0.0
    return summary, between_fraction


def prediction_headline(data: DashboardData) -> dict[str, float]:
    """Return the scalar PLS comparison used in the reviewer headline."""
    rows = headline_mae(data.scalar_metrics, data.scalar_predictions, "model").filter(
        pl.col("model") == "pls"
    )
    return {str(row["population"]): cast(float, row["mae_g"]) for row in rows.iter_rows(named=True)}


def uncertainty_headline(data: DashboardData) -> dict[str, float]:
    """Return pooled interval evidence for represented and unseen conditions."""
    result: dict[str, float] = {}
    for protocol in ("primary", "secondary_id"):
        rows = data.interval_predictions.filter(pl.col("protocol") == protocol)
        result[f"{protocol}_empirical_coverage"] = cast(float, rows["covered"].mean())
        result[f"{protocol}_mean_width_g"] = cast(float, rows["interval_width_g"].mean())
    return result


def distance_gate_summary(run: dict[str, object]) -> pl.DataFrame:
    """Shape the saved development gate without duplicating its outcomes."""
    screens = cast(list[dict[str, object]], run.get("screens", []))
    rows = []
    for screen in screens:
        if screen.get("protocol") != "primary":
            continue
        fold = str(screen["fold"])
        rows.append(
            {
                "Held-out experiment": int(fold.rsplit("_", maxsplit=1)[-1]),
                "Development MAE reduction": cast(float, screen["mean_relative_reduction"]),
                "Decision": "Pass" if screen.get("passed") else "Fail",
            }
        )
    return pl.DataFrame(rows).sort("Held-out experiment")


def _display_label(value: object) -> str:
    text = str(value)
    return MODEL_LABELS.get(text, REPRESENTATION_LABELS.get(text, text))


def _feature_label(value: object) -> str:
    return str(value).replace("_", " ").title()


def _fold_label(value: object) -> str:
    text = str(value)
    if text == "within_experiment":
        return "All experiment groups"
    return text.replace("holdout_experiment_", "Experiment ").replace("experiment_", "Experiment ")


def coverage_summary(metrics: pl.DataFrame) -> pl.DataFrame:
    """Keep primary and both pooled/per-experiment ID interval results visibly distinct."""
    return metrics.with_columns(
        pl.when(pl.col("protocol") == "primary")
        .then(
            pl.concat_str(
                pl.lit("Unseen experiment · "),
                pl.col("fold").str.replace("holdout_experiment_", "experiment "),
            )
        )
        .when(pl.col("fold") == "within_experiment")
        .then(pl.lit("Represented conditions · pooled"))
        .otherwise(
            pl.concat_str(
                pl.lit("Represented conditions · "),
                pl.col("fold").str.replace("experiment_", "experiment "),
            )
        )
        .alias("population")
    )


def support_heatmap_table(support: pl.DataFrame, protocol: str) -> pl.DataFrame:
    """Return feature-by-population marginal range-departure fractions."""
    return (
        support.filter(pl.col("protocol") == protocol)
        .with_columns(
            pl.concat_str(
                pl.lit("experiment "), pl.col("evaluation_experiment_id").cast(pl.String)
            ).alias("population")
        )
        .select("feature", "population", "fraction_outside_training_range")
        .sort("feature", "population")
    )


def _bar_chart(
    rows: pl.DataFrame, x: str, y: str, color: str, *, title: str, y_title: str
) -> go.Figure:
    figure = go.Figure()
    for name, group_rows in rows.partition_by(color, as_dict=True).items():
        label = str(name[0])
        figure.add_bar(name=label, x=group_rows[x].to_list(), y=group_rows[y].to_list())
    figure.update_layout(
        title=title, barmode="group", xaxis_title="", yaxis_title=y_title, legend_title=""
    )
    return figure


def observed_vs_predicted_figure(selected: pl.DataFrame, *, title: str) -> go.Figure:
    """Plot observed and predicted weights on one padded range with equal scale."""
    low = min(
        cast(float, selected["observed_weight_g"].min()),
        cast(float, selected["predicted_weight_g"].min()),
    )
    high = max(
        cast(float, selected["observed_weight_g"].max()),
        cast(float, selected["predicted_weight_g"].max()),
    )
    padding = max((high - low) * 0.1, 0.001)
    shared_range = [low - padding, high + padding]
    figure = go.Figure()
    figure.add_scatter(
        x=selected["observed_weight_g"].to_list(),
        y=selected["predicted_weight_g"].to_list(),
        mode="markers",
        marker={"size": 9, "opacity": 0.8},
        name="Cycles",
    )
    figure.add_scatter(x=[low, high], y=[low, high], mode="lines", name="Ideal")
    figure.update_layout(
        title=title,
        height=600,
        xaxis={
            "title": "Observed weight (g)",
            "range": shared_range,
            "tickformat": ".3f",
            "constrain": "domain",
        },
        yaxis={
            "title": "Predicted weight (g)",
            "range": shared_range,
            "tickformat": ".3f",
            "scaleanchor": "x",
            "scaleratio": 1,
        },
    )
    return figure


def cycle_signal_summary(signals: pl.DataFrame) -> pl.DataFrame:
    """Pointwise observed spread on the shared native grid; no peak alignment."""
    return (
        signals.group_by("sample_index", "elapsed_time_seconds")
        .agg(
            expression.alias(f"{channel}_{stat}")
            for channel in ("injection_pressure", "injection_flow")
            for stat, expression in (
                ("min", pl.col(channel).min()),
                ("p10", pl.col(channel).quantile(0.1, interpolation="linear")),
                ("median", pl.col(channel).median()),
                ("p90", pl.col(channel).quantile(0.9, interpolation="linear")),
                ("max", pl.col(channel).max()),
            )
        )
        .sort("sample_index")
    )


def _render_data_tab(data: DashboardData) -> None:
    st.header("Data & process")
    st.write(
        "Injection molding injects molten plastic into a mold, holds it under pressure, then "
        "cools and removes the part. Pressure, flow, temperature and timing describe how it was "
        "made. We ask whether these machine records can estimate completed-part weight before "
        "using its physical measurement. Weight is one quality characteristic, not a complete "
        "acceptability verdict. "
        "Dataset 2 contains controlled injection-molding runs for a stacking-box part made from "
        "BASF Ultramid B3EG6, a glass-fiber-reinforced nylon 6 material (PA6-GF30). Each labeled "
        "machine cycle maps to one molded part."
    )
    with st.expander("What one cycle contains—and how it is used"):
        st.markdown(
            "\n".join(
                (
                    "| Dataset component | Role in this project |",
                    "| --- | --- |",
                    "| **Scalar process measurements** | 16 completed-cycle variables form the "
                    "scalar baseline, including injection time, maximum pressure "
                    "and barrel temperatures. |",
                    "| **Pressure and flow trajectories** | 2,048 native-time samples per channel "
                    "test whether dynamic signal shape adds transferable information. |",
                    "| **Experimental context** | Experiment, moisture, mold-temperature and "
                    "charge context describe controlled conditions; they group analysis but are "
                    "not default "
                    "model inputs. |",
                    "| **Physical quality** | Part weight in grams is the target measured after "
                    "molding. Geometry remains deferred because its released scale/mapping is "
                    "unresolved. |",
                )
            )
        )
        st.caption(
            "The source also contains optional cavity-pressure/state data that this bounded MVP "
            "does not use. Signal-only cycles without a matching scalar/quality row have no "
            "supported weight target and are excluded during preparation."
        )
    with st.expander("Process feature glossary"):
        st.markdown(
            """
            - **Maximum injection pressure:** the highest recorded injection-pressure value for
              the completed cycle.
            - **Switchover injection pressure:** the named machine measurement at the transition
              from filling to the next molding phase.
            - **Melt cushion:** material remaining ahead of the screw after injection; the source
              does not establish whether its native value represents travel or volume.
            - **Dosing time:** the recorded duration of preparing material for the next cycle.
            - **Barrel heating zones:** temperature measurements along the machine barrel.
            - **Actual back pressure:** a preserved source measurement whose negative values and
              unresolved semantics do not support interpreting it as an ordinary pressure
              setpoint.

            Machine-native units remain unresolved except where explicitly stated; these labels
            explain the recorded features without adding unit or causal assumptions.
            """
        )

    summary, between_fraction = experiment_summary(data)
    total_cycles = cast(int, summary["labeled_cycles"].sum())
    st.subheader("Study flow")
    st.graphviz_chart(
        """
        digraph pipeline {
            graph [rankdir=LR, bgcolor="transparent", nodesep=0.3, ranksep=0.45];
            node [shape=box, style="rounded,filled", fillcolor="#e8f0fa",
                  color="#7593b8", fontcolor="#172b45", fontname="Arial", fontsize=12];
            edge [color="#7593b8", fontcolor="#8798ab", fontname="Arial", fontsize=10];
            data [label="{total_cycles} molded parts\nMachine scalars + pressure/flow"];
            split [label="Train on represented groups\nTest on a held-out experiment"];
            compare [label="Compare scalar and\ntrajectory models"];
            reliable [label="Calibrate intervals and\ntest reliability under shift"];
            data -> split -> compare -> reliable;
        }
        """.replace("{total_cycles}", str(total_cycles)),
        width="stretch",
    )
    st.markdown(
        "**Completed-cycle scalars + pressure/flow trajectories → predict part weight.** The "
        "model trains on the represented experiment groups and evaluates on one held-out group, "
        "then repeats for every loaded group. Scalars establish the baseline; trajectory "
        "representations test added value; context defines the holdout; weight never enters as "
        "a predictor. Separate "
        "calibration rows are reserved for prediction intervals. The uncertainty branch uses "
        "scalar models; it does not select a trajectory model from evaluation results. "
        "The dashboard reads saved results from these experiments."
    )

    st.subheader("Observed experiment groups")
    contexts = {
        15: "Moisture: raw 0.050 → 0.100 → 0.150",
        20: "Moisture: raw 0.086 → 0.180 → 0.046",
        23: "Mold temperature: raw 80 → 90 → 70",
    }
    st.dataframe(
        summary.with_columns(
            pl.col("experiment_id")
            .replace_strict(contexts, default="Not described")
            .alias("observed_controlled_context")
        ).select("experiment_id", "labeled_cycles", "observed_controlled_context", "mean_weight_g"),
        hide_index=True,
        width="stretch",
        column_config={
            "experiment_id": "Experiment",
            "labeled_cycles": "Labeled cycles",
            "observed_controlled_context": "Observed controlled context",
            "mean_weight_g": st.column_config.NumberColumn("Mean part weight", format="%.3f g"),
        },
    )
    st.warning(
        "Each experiment contains several settings; validation withholds the whole group. "
        "Some released context values or units have documented source limitations. These are "
        "source experiment groups, not verified calendar days. The context identifies "
        "controlled interventions, but other process measurements move with them; it does not "
        "prove that moisture or mold temperature alone caused the weight differences."
    )
    weights = weight_rows(data)

    figure = go.Figure()
    for experiment, rows in (
        weights.sort("experiment_id").partition_by("experiment_id", as_dict=True).items()
    ):
        value = experiment[0]
        figure.add_box(name=f"Experiment {value}", y=rows["weight_g"].to_list(), boxpoints=False)
    figure.update_layout(
        title="Weight distributions differ across experiment groups", yaxis_title="Weight (g)"
    )
    st.plotly_chart(figure, width="stretch")
    st.info(
        f"{between_fraction:.2%} of observed weight variation was between the loaded experiment "
        "groups. That group separation can make pooled validation—especially pooled R²—look "
        "stronger when all groups are represented, motivating the whole-experiment holdout."
    )

    st.subheader("Typical cycle and variation within this experiment")
    experiments = sorted(data.context["experiment_id"].unique().to_list())
    experiment = cast(int, st.selectbox("Experiment", experiments, key="cycle_experiment"))
    candidates = data.context.filter(pl.col("experiment_id") == experiment)["unit_id"].to_list()
    summary = cycle_signal_summary(data.signals.filter(pl.col("unit_id").is_in(candidates)))
    full_range = st.checkbox(
        "Show full observed range (minimum to maximum)", key="cycle_full_range"
    )
    figure = subplots.make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12)
    times = summary["elapsed_time_seconds"].to_list()
    for row, channel, label in (
        (1, "injection_pressure", "Pressure"),
        (2, "injection_flow", "Flow"),
    ):
        bands = [("p10", "p90", "Middle 80%", "rgba(94,180,245,0.3)")]
        if full_range:
            bands.insert(0, ("min", "max", "Minimum to maximum", "rgba(94,180,245,0.12)"))
        for lower, upper, name, color in bands:
            figure.add_scatter(
                x=times,
                y=summary[f"{channel}_{lower}"].to_list(),
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
                row=row,
                col=1,
            )
            figure.add_scatter(
                x=times,
                y=summary[f"{channel}_{upper}"].to_list(),
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor=color,
                name=name,
                legendgroup=name,
                showlegend=row == 1,
                hoverinfo="skip",
                row=row,
                col=1,
            )
        figure.add_scatter(
            x=times,
            y=summary[f"{channel}_median"].to_list(),
            mode="lines",
            name="Median",
            legendgroup="Median",
            showlegend=row == 1,
            line={"color": "#7dc8ff", "width": 2},
            hovertemplate=(
                f"{label} median: %{{y:.2f}}<br>Elapsed time: %{{x:.3f}} s<extra></extra>"
            ),
            row=row,
            col=1,
        )
        figure.update_yaxes(title_text=f"{label} (native units)", row=row, col=1)
    figure.update_xaxes(title_text="Native elapsed time (s)", row=2, col=1)
    figure.update_layout(height=650, legend={"orientation": "h"})
    st.plotly_chart(figure, width="stretch")
    st.caption(
        f"Line: median across {len(candidates)} cycles. Shading: middle 80% of observed cycles "
        "at each elapsed-time point—not a confidence interval. The optional faint band shows "
        "the full observed range. Native timestamps are preserved; peaks are not realigned, "
        "so timing differences contribute to the spread. The median need not be an actual cycle."
    )
    with st.expander("Inspect an individual cycle"):
        _render_individual_cycle(data.signals, candidates)


def _render_individual_cycle(signals: pl.DataFrame, candidates: list[str]) -> None:
    unit_id = str(st.selectbox("Cycle", candidates, key="cycle_unit"))
    cycle = signals.filter(pl.col("unit_id") == unit_id).sort("sample_index")
    signal_figure = go.Figure()
    signal_figure.add_scatter(
        x=cycle["elapsed_time_seconds"].to_list(),
        y=cycle["injection_pressure"].to_list(),
        name="Injection pressure (native units)",
    )
    signal_figure.add_scatter(
        x=cycle["elapsed_time_seconds"].to_list(),
        y=cycle["injection_flow"].to_list(),
        name="Injection flow (native units)",
        yaxis="y2",
    )
    signal_figure.update_layout(
        title=f"Cycle {unit_id.rsplit('/', maxsplit=1)[-1]}",
        xaxis_title="Native elapsed time (s)",
        yaxis={"title": "Pressure amplitude (native units)"},
        yaxis2={"title": "Flow amplitude (native units)", "overlaying": "y", "side": "right"},
        legend={"orientation": "h"},
    )
    st.plotly_chart(signal_figure, width="stretch")


def _prediction_source(data: DashboardData, family: str) -> tuple[pl.DataFrame, str]:
    if family == "Scalar baselines":
        return data.scalar_predictions, "model"
    if family == "Ridge representations":
        return data.ridge_predictions, "representation"
    return data.lightgbm_predictions, "representation"


def _render_prediction_tab(data: DashboardData) -> None:
    st.header("Prediction & generalization")
    prediction = prediction_headline(data)
    id_mae = prediction["Represented conditions — pooled cycles"]
    heldout_mae = prediction["Unseen experiment — pooled cycles"]
    equal_fold_mae = prediction["Unseen experiment — equal experiment weight"]
    if heldout_mae > id_mae:
        comparison_sentence = (
            "Error was higher when a complete experiment was withheld; represented-condition "
            "accuracy did not establish new-condition transfer."
        )
    elif heldout_mae < id_mae:
        comparison_sentence = "Error was lower when a complete experiment was withheld."
    else:
        comparison_sentence = "Pooled error was equal across the two evaluation settings."
    st.success(
        f"Scalar PLS pooled MAE was {id_mae:.3f} g with represented conditions and "
        f"{heldout_mae:.3f} g when a complete experiment was withheld. The predefined "
        f"equal-experiment result was {equal_fold_mae:.3f} g. {comparison_sentence}"
    )
    st.markdown(
        "**Train on the represented experiment groups → evaluate on one held-out group → "
        "repeat for every loaded group.** "
        "The represented-conditions benchmark instead holds out random cycles from every group."
    )
    with st.expander("Method and reading guide"):
        st.markdown(
            "Each group contains multiple settings. Because training and evaluation contain "
            "cycles from the same experiment groups, random-cycle holdout primarily measures "
            "interpolation within represented conditions and may overstate performance for "
            "genuinely new production conditions. The original "
            "paper's random cross-validation asked whether detailed signals improve prediction "
            "within the available condition mixture; this project adds the harder transfer "
            "question. Its features and models also differ, so this is an extension, not an "
            "exact replication.\n\n"
            "**Reading the comparisons:** MAE is average absolute weight error in grams (lower "
            "is better). Equal-experiment gives each experiment equal weight; pooled gives each "
            "cycle equal weight. **Mean** predicts a constant training average; **Ridge** is a "
            "regularized linear model; **PLS** learns components linking correlated inputs to "
            "weight; **LightGBM** learns nonlinear relationships with decision trees.\n\n"
            "The initial exploratory audit inspected all loaded experiments before the grouped "
            "evaluation design was fixed. These are retrospective comparisons, not "
            "prospective untouched holdouts."
        )
    scalar = headline_mae(data.scalar_metrics, data.scalar_predictions, "model")
    scalar_display = scalar.with_columns(
        pl.col("model").replace_strict(MODEL_LABELS, default=pl.col("model")).alias("Model")
    )
    st.plotly_chart(
        _bar_chart(
            scalar_display,
            "Model",
            "mae_g",
            "population",
            title="Scalar baseline error across evaluation settings",
            y_title="MAE (g)",
        ),
        width="stretch",
    )
    st.caption(
        f"The like-weighted reviewer comparison is {id_mae:.3f} g versus {heldout_mae:.3f} g "
        f"pooled MAE. The predefined primary result remains {equal_fold_mae:.3f} g equal-fold "
        "MAE. The evaluation settings use separately fitted pipelines, so the gap is "
        "descriptive rather "
        "than a paired causal effect."
    )

    ridge = headline_mae(data.ridge_metrics, data.ridge_predictions, "representation").with_columns(
        pl.lit("Ridge").alias("model_family")
    )
    lightgbm = headline_mae(
        data.lightgbm_metrics, data.lightgbm_predictions, "representation"
    ).with_columns(pl.lit("LightGBM").alias("model_family"))
    comparisons = pl.concat((ridge, lightgbm))
    population = str(
        st.selectbox(
            "Evaluation setting",
            comparisons["population"].unique(maintain_order=True).to_list(),
        )
    )
    selected_comparison = comparisons.filter(pl.col("population") == population).with_columns(
        pl.col("representation")
        .replace_strict(REPRESENTATION_LABELS, default=pl.col("representation"))
        .alias("Representation")
    )
    st.plotly_chart(
        _bar_chart(
            selected_comparison,
            "Representation",
            "mae_g",
            "model_family",
            title=f"Matched representation comparison · {population}",
            y_title="MAE (g)",
        ),
        width="stretch",
    )
    st.caption(
        "Scalars establish the baseline; trajectory summaries add engineered pressure/flow "
        "features; PCA and supervised PLS add compressed signal components. PCA summarizes "
        "signal variation; PLS compression "
        "learns components associated with training weights, before Ridge/LightGBM predicts. "
        "The chart reports the loaded results for each predefined representation and model "
        "family. It is a descriptive comparison, not an outer-selected deployment winner."
    )

    st.subheader("Did adding trajectories reduce prediction error?")
    st.caption(
        "Each model has its own horizontal scale so small changes remain visible. "
        "Compare the labeled values in grams, not distances between panels. "
        "Left of zero = increased error; right of zero = reduced error."
    )
    for family_name, metrics in (
        ("Ridge", data.ridge_metrics),
        ("LightGBM", data.lightgbm_metrics),
    ):
        primary = metrics.filter(pl.col("protocol") == "primary")
        baseline = primary.filter(pl.col("representation") == "A").select(
            "fold", pl.col("mae_g").alias("scalar_mae_g")
        )
        deltas = (
            primary.filter(pl.col("representation") != "A")
            .join(baseline, on="fold", validate="m:1")
            .with_columns(
                (pl.col("scalar_mae_g") - pl.col("mae_g")).alias("improvement_g"),
                pl.col("fold")
                .str.replace("holdout_experiment_", "Experiment ")
                .alias("experiment"),
            )
            .select("experiment", "representation", "improvement_g")
        )
        representations = sorted(deltas["representation"].unique().to_list())
        experiments = sorted(deltas["experiment"].unique().to_list())
        delta_figure = go.Figure()
        for lane in range(len(representations)):
            delta_figure.add_hrect(
                y0=lane - 0.43,
                y1=lane + 0.43,
                fillcolor="rgba(140,170,200,0.10)" if lane % 2 == 0 else "rgba(140,170,200,0.04)",
                line_width=0,
                layer="below",
            )
        for index, experiment in enumerate(experiments):
            rows = deltas.filter(pl.col("experiment") == experiment).sort("representation")
            values = rows["improvement_g"].to_list()
            positions = [
                representations.index(rep) + (index - (len(experiments) - 1) / 2) * 0.25
                for rep in rows["representation"].to_list()
            ]
            color = ["#7dc8ff", "#ffbe70", "#d59bff"][index]
            for position, value in zip(positions, values, strict=True):
                delta_figure.add_shape(
                    type="line",
                    x0=0,
                    x1=value,
                    y0=position,
                    y1=position,
                    line={"color": color, "width": 3},
                    layer="below",
                )
            delta_figure.add_scatter(
                x=values,
                y=positions,
                mode="markers+text",
                marker={"size": 11, "color": color},
                name=experiment,
                text=[f"{value:+.3f} g" for value in values],
                textposition=["middle left" if value < 0 else "middle right" for value in values],
                cliponaxis=False,
                customdata=[_display_label(rep) for rep in rows["representation"].to_list()],
                hovertemplate=(
                    "%{customdata}<br>MAE reduction: %{x:+.4f} g<extra>%{fullData.name}</extra>"
                ),
            )
        low = min(0.0, cast(float, deltas["improvement_g"].min()))
        high = max(0.0, cast(float, deltas["improvement_g"].max()))
        span = high - low or 0.01
        delta_figure.add_vline(x=0, line_color="#bfc7d0", line_width=2)
        delta_figure.update_layout(
            title=family_name,
            height=440,
            xaxis={
                "title": "MAE reduction versus scalar baseline (g)",
                "range": [low - span * 0.2, high + span * 0.25],
                "zeroline": False,
            },
            yaxis={
                "tickvals": list(range(len(representations))),
                "ticktext": [_display_label(rep) for rep in representations],
                "range": [len(representations) - 0.5, -0.5],
                "showgrid": False,
            },
            legend={"orientation": "h", "y": 1.15},
        )
        st.plotly_chart(delta_figure, width="stretch")
    st.caption(
        "MAE reduction = scalar MAE minus trajectory-augmented MAE. "
        "Each comparison uses the same held-out experiment and model family."
    )

    _, between_fraction = experiment_summary(data)
    st.subheader("What was learned")
    learned, next_step = st.columns(2)
    with learned:
        st.markdown(
            f"""
            **Learned from this experiment**

            - {between_fraction:.2%} of observed weight variation was between experiment groups, so
              pooled performance can hide weak within-condition explanation.
            - The loaded scalar and trajectory comparisons show whether added complexity
              improved each held-out experiment; no global production model was selected.
            - Marginal range departures are reported separately by population; they do not prove
              that range departure caused any prediction error.
            - Predictive importance is reported separately by population; no universal or causal
              sensor ranking is established.
            - This is a completed-cycle weight estimate, not control, conformance or physical
              root-cause analysis.
            """
        )
    with next_step:
        reliability = uncertainty_headline(data)
        coverage_direction = (
            "lower"
            if reliability["primary_empirical_coverage"]
            < reliability["secondary_id_empirical_coverage"]
            else "not lower"
        )
        gate_result = "passed" if data.uncertainty_run.get("m8_eligible") else "failed"
        st.markdown(
            f"""
            **The next analysis asked whether the model could recognize when it was unreliable.**

            Empirical interval coverage was {coverage_direction} for unseen experiments, and the
            saved development distance gate {gate_result}. The Reliability tab shows the loaded
            evidence and the resulting study decision.
            """
        )

    st.subheader("Per-experiment predictions")
    family = str(
        st.selectbox(
            "Model family",
            ("Scalar baselines", "Ridge representations", "LightGBM representations"),
        )
    )
    predictions, group_column = _prediction_source(data, family)
    protocol = str(
        st.selectbox(
            "Evaluation setting",
            ("primary", "secondary_id"),
            key="prediction_protocol",
            format_func=PROTOCOL_LABELS.__getitem__,
        )
    )
    choices = sorted(
        predictions.filter(pl.col("protocol") == protocol)[group_column].unique().to_list()
    )
    default_choice = choices.index("pls") if "pls" in choices else 0
    choice = str(
        st.selectbox(
            "Model / representation",
            choices,
            index=default_choice,
            format_func=_display_label,
        )
    )
    selected = predictions.filter(
        (pl.col("protocol") == protocol) & (pl.col(group_column) == choice)
    )
    experiments = sorted(selected["experiment_id"].unique().to_list())
    default_experiment = experiments.index(23) if protocol == "primary" and 23 in experiments else 0
    experiment = cast(
        int,
        st.selectbox(
            "Evaluation experiment",
            experiments,
            index=default_experiment,
            key="prediction_experiment",
        ),
    )
    selected = selected.filter(pl.col("experiment_id") == experiment)
    actual_figure = observed_vs_predicted_figure(
        selected,
        title=f"{family} · {_display_label(choice)} · experiment {experiment}",
    )
    st.plotly_chart(actual_figure, width="stretch")
    st.caption(
        "Observed and predicted weights use the same padded numerical range and equal physical "
        "scale, so distance from the ideal line is not distorted."
    )
    signed_errors = (
        selected["predicted_weight_g"].to_numpy() - selected["observed_weight_g"].to_numpy()
    )
    mean_bias = float(np.mean(signed_errors))
    direction = ""
    if np.all(signed_errors < 0):
        direction = " Every prediction underestimates the measured weight."
    elif np.all(signed_errors > 0):
        direction = " Every prediction overestimates the measured weight."
    st.caption(
        f"Mean signed error (predicted - measured): {mean_bias:+.3f} g.{direction} "
        "Negative means underprediction on average; positive means overprediction."
    )
    experiment_table = per_experiment_metrics(predictions, group_column).filter(
        (pl.col("protocol") == protocol) & (pl.col(group_column) == choice)
    )
    st.dataframe(
        experiment_table.select(
            pl.col("protocol").replace_strict(PROTOCOL_LABELS).alias("Evaluation setting"),
            pl.col(group_column)
            .map_elements(_display_label, return_dtype=pl.String)
            .alias("Model / representation"),
            pl.col("experiment_id").alias("Experiment"),
            pl.col("n").alias("Cycles"),
            pl.col("mae_g").alias("MAE (g)"),
            pl.col("rmse_g").alias("RMSE (g)"),
            pl.col("r2").alias("R²"),
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "RMSE emphasizes larger errors more than MAE. R² compares squared prediction error with "
        "a constant predictor equal to the observed mean of the displayed evaluation population; "
        "R² = 1 is perfect, 0 matches that reference, and negative values are worse. That "
        "reference is not necessarily the fitted model's training-mean prediction."
    )

    st.subheader("Population-specific predictive importance")
    st.write(
        "Permutation importance shuffles one input across evaluated parts and measures the "
        "change in prediction error. Positive values mean shuffling hurt predictions; negative "
        "values mean it improved this model's predictions, not that changing the physical "
        "process would help. "
        f"Across the loaded evidence, {(data.importance['importance_mean_g'] < 0).sum()} of "
        f"{data.importance.height} saved mean importances were negative. The chart explains one "
        "fitted model and population at a "
        "time—not a universal sensor hierarchy."
    )
    importance_protocol = str(
        st.selectbox(
            "Importance evaluation setting",
            ("primary", "secondary_id"),
            key="importance_protocol",
            format_func=PROTOCOL_LABELS.__getitem__,
        )
    )
    importance_experiments = sorted(
        data.importance.filter(pl.col("protocol") == importance_protocol)[
            "evaluation_experiment_id"
        ]
        .unique()
        .to_list()
    )
    default_importance_experiment = (
        importance_experiments.index(20) if 20 in importance_experiments else 0
    )
    importance_experiment = cast(
        int,
        st.selectbox(
            "Importance experiment",
            importance_experiments,
            index=default_importance_experiment,
            key="importance_experiment",
        ),
    )
    importance = data.importance.filter(
        (pl.col("protocol") == importance_protocol)
        & (pl.col("evaluation_experiment_id") == importance_experiment)
    ).sort("importance_mean_g")
    model_family = str(importance.item(0, "model_family"))
    model_settings = str(importance.item(0, "model_settings"))
    repeat_count = len(cast(list[float], importance.item(0, "repeat_importance_g")))
    importance_figure = go.Figure(
        go.Bar(
            x=importance["importance_mean_g"].to_list(),
            y=[_feature_label(feature) for feature in importance["feature"].to_list()],
            error_x={"type": "data", "array": importance["importance_std_g"].to_list()},
            orientation="h",
        )
    )
    importance_figure.update_layout(
        title=(
            f"Permutation importance · {_display_label(model_family)} · "
            f"{PROTOCOL_LABELS[importance_protocol]} · "
            f"experiment {importance_experiment}"
        ),
        xaxis_title="Change in MAE after permutation (g; negative values retained)",
        yaxis_title="",
    )
    st.plotly_chart(importance_figure, width="stretch")
    st.caption(
        f"Selected model: {_display_label(model_family)}. Error bars are the "
        f"standard deviation over {repeat_count} saved permutations, not confidence intervals."
    )
    with st.expander("Saved model settings"):
        st.code(model_settings, language="json")
    st.warning(
        "Permutation importance describes this fitted model and population. Correlated inputs and "
        "the observed transfer performance complicate interpretation; it is not a physical or "
        "causal ranking."
    )


def _render_reliability_tab(data: DashboardData) -> None:
    st.header("Reliability under shift")
    uncertainty = uncertainty_headline(data)
    nominal = cast(float, data.uncertainty_run.get("nominal_coverage", 0.9))
    represented_coverage = uncertainty["secondary_id_empirical_coverage"]
    unseen_coverage = uncertainty["primary_empirical_coverage"]
    m8_eligible = bool(data.uncertainty_run.get("m8_eligible"))
    coverage_comparison = (
        "Coverage was lower for unseen experiments."
        if unseen_coverage < represented_coverage
        else "Coverage was not lower for unseen experiments."
    )
    gate_comparison = (
        "The saved development gate passed."
        if m8_eligible
        else (
            "The saved development gate failed, so the selective-measurement study was not pursued."
        )
    )
    lead = (
        f"Nominal {nominal:.0%} intervals covered {represented_coverage:.1%} of represented-"
        f"condition outcomes and {unseen_coverage:.1%} under held-out-experiment evaluation. "
        f"{coverage_comparison} {gate_comparison} No automatic measurement policy is claimed."
    )
    if unseen_coverage < represented_coverage or not m8_eligible:
        st.error(lead)
    else:
        st.info(lead)
    selections = cast(list[dict[str, object]], data.uncertainty_run.get("selections", []))
    st.write(
        "This uncertainty study selects between scalar PLS and LightGBM using development "
        "data separately for each fold, then calibrates on reserved cycles. Empirical coverage "
        f"is how often the nominal {nominal:.0%} intervals actually contained measured weights. "
        "Calibration sets one fixed error margin per fitted model, so intervals do not "
        "automatically widen for an unfamiliar cycle."
    )
    st.dataframe(
        pl.DataFrame(
            {
                "Evaluation setting": [
                    PROTOCOL_LABELS.get(str(row["protocol"]), str(row["protocol"]))
                    for row in selections
                ],
                "Fold": [_fold_label(row["fold"]) for row in selections],
                "Development-selected model": [
                    _display_label(cast(dict[str, object], row["selected_candidate"])["family"])
                    for row in selections
                ],
            }
        ),
        hide_index=True,
        width="stretch",
    )
    coverage = coverage_summary(data.interval_metrics)
    coverage_labels = [
        str(label)
        .replace("Unseen experiment · experiment ", "Held-out experiment ")
        .replace("Represented conditions · experiment ", "Represented experiment ")
        .replace("Represented conditions · pooled", "Represented experiments · combined")
        for label in coverage["population"].to_list()
    ]
    coverage_figure = go.Figure()
    coverage_figure.add_bar(
        name="Observed coverage",
        orientation="h",
        x=coverage["empirical_coverage"].to_list(),
        y=coverage_labels,
        text=coverage["empirical_coverage"].to_list(),
        texttemplate="%{text:.1%}",
        textposition="outside",
        cliponaxis=False,
        customdata=coverage["mean_width_g"].to_list(),
        hovertemplate=(
            "%{y}<br>Measured weights inside interval: %{x:.1%}"
            "<br>Average interval width: %{customdata:.3f} g<extra></extra>"
        ),
    )
    coverage_figure.add_vline(
        x=nominal,
        line_dash="dash",
        line_color="#f2b94b",
        annotation_text=f"{nominal:.0%} target",
        annotation_position="top",
    )
    coverage_figure.update_layout(
        title="How often did prediction intervals contain the measured weight?",
        yaxis_title="",
        xaxis_title="Measured weights inside the prediction interval",
        xaxis={"range": [0.0, 1.05], "tickformat": ".0%", "dtick": 0.2},
        yaxis={"autorange": "reversed", "automargin": True},
        showlegend=False,
        height=460,
    )
    st.plotly_chart(coverage_figure, width="stretch")
    st.caption(
        f"The dashed line marks the {nominal:.0%} coverage target. Held-out experiments were "
        "absent from training; represented experiments contributed other cycles to training. "
        "Combined coverage pools the evaluated cycles from all represented experiments."
    )
    st.dataframe(
        coverage.select(
            pl.col("population").alias("Evaluation population"),
            pl.col("evaluation_count").alias("Cycles"),
            pl.col("nominal_coverage").alias("Nominal coverage"),
            pl.col("empirical_coverage").alias("Empirical coverage"),
            pl.col("mean_width_g").alias("Mean interval width (g)"),
        ),
        hide_index=True,
        width="stretch",
    )
    primary_coverage = coverage.filter(pl.col("protocol") == "primary")
    if primary_coverage.height:
        weakest = primary_coverage.sort("empirical_coverage").row(0, named=True)
        st.caption(
            f"The lowest loaded held-out coverage was {weakest['empirical_coverage']:.1%} for "
            f"{weakest['population']}; its interval averaged {weakest['mean_width_g']:.3f} g "
            "wide. No separate interval-widening experiment was run."
        )

    st.subheader("Selective-measurement development gate")
    screen = cast(dict[str, object], data.uncertainty_run.get("development_screen", {}))
    retained = cast(float, screen.get("retained_fraction", 0.75))
    threshold = cast(float, screen.get("primary_fold_minimum_mean_relative_reduction", 0.1))
    st.write(
        "The uncertainty study tested whether distance from familiar training cycles could "
        f"identify predictions that were safer to accept. Retaining the closest {retained:.0%} "
        f"had to reduce development MAE by at least {threshold:.0%} in every whole-experiment "
        "fold before a selective-measurement study could proceed."
    )
    st.dataframe(
        distance_gate_summary(data.uncertainty_run),
        hide_index=True,
        width="stretch",
        column_config={
            "Development MAE reduction": st.column_config.NumberColumn(format="percent")
        },
    )
    if m8_eligible:
        st.warning(
            "The loaded all-fold gate passed, making the saved evidence eligible for the next "
            "pre-specified study. Passing this development gate alone does not establish an "
            "automatic measurement policy."
        )
    else:
        st.warning(
            "The loaded all-fold gate failed. Input distance identified unfamiliar cycles but "
            "did not meet the saved error-reduction requirement in every setup. The "
            "selective-measurement study was therefore not pursued, and no automatic "
            "measurement policy is claimed."
        )

    st.subheader("Saved interval example")
    protocol = str(
        st.selectbox(
            "Interval evaluation setting",
            ("primary", "secondary_id"),
            format_func=PROTOCOL_LABELS.__getitem__,
        )
    )
    interval_rows = data.interval_predictions.filter(pl.col("protocol") == protocol)
    experiments = sorted(interval_rows["experiment_id"].unique().to_list())
    experiment = cast(int, st.selectbox("Interval experiment", experiments))
    interval_rows = interval_rows.filter(pl.col("experiment_id") == experiment).sort(
        "cycle_counter"
    )
    interval_model = data.importance.filter(
        (pl.col("protocol") == protocol) & (pl.col("evaluation_experiment_id") == experiment)
    ).item(0, "model_family")
    st.caption(
        f"Selected model: {_display_label(interval_model)}. "
        "The band is the saved prediction plus/minus its calibration error margin."
    )
    start_options = list(range(0, interval_rows.height, 30))
    start = st.selectbox(
        "Cycle window",
        start_options,
        format_func=lambda value: f"Rows {value + 1}-{min(value + 30, interval_rows.height)}",
    )
    interval_rows = interval_rows.slice(start, 30)
    interval_figure = go.Figure()
    interval_figure.add_scatter(
        x=interval_rows["cycle_counter"].to_list(),
        y=interval_rows["upper_g"].to_list(),
        mode="lines",
        line={"width": 0},
        showlegend=False,
    )
    interval_figure.add_scatter(
        x=interval_rows["cycle_counter"].to_list(),
        y=interval_rows["lower_g"].to_list(),
        mode="lines",
        fill="tonexty",
        name="90% interval",
    )
    interval_figure.add_scatter(
        x=interval_rows["cycle_counter"].to_list(),
        y=interval_rows["observed_weight_g"].to_list(),
        mode="markers",
        name="Observed weight",
    )
    interval_figure.add_scatter(
        x=interval_rows["cycle_counter"].to_list(),
        y=interval_rows["predicted_weight_g"].to_list(),
        mode="lines+markers",
        name="Predicted weight",
    )
    interval_figure.update_layout(
        title=f"Saved intervals · {PROTOCOL_LABELS[protocol]} · experiment {experiment}",
        xaxis_title="Cycle counter",
        yaxis_title="Weight (g)",
    )
    st.plotly_chart(interval_figure, width="stretch")

    st.subheader("How often were process measurements outside the training range?")
    support_protocol = str(
        st.selectbox(
            "Support evaluation setting",
            ("primary", "secondary_id"),
            key="support_protocol",
            format_func=PROTOCOL_LABELS.__getitem__,
        )
    )
    support = support_heatmap_table(data.support, support_protocol)
    maximum = support.sort("fraction_outside_training_range", descending=True).row(0, named=True)
    zoom_scale = st.checkbox(
        "Zoom color scale to small differences",
        value=False,
        key="support_zoom_scale",
        help="Colors end at the largest displayed percentage. The percentages stay unchanged.",
    )
    scale_max = float(maximum["fraction_outside_training_range"]) if zoom_scale else 1.0
    if scale_max == 0:
        scale_max = 1.0
    if zoom_scale:
        st.caption(
            f"Zoomed colors: 0 to {scale_max:.1%} for this view only. Compare the printed "
            "percentages, not color intensity, across evaluation settings."
        )
    else:
        st.caption("Fixed 0 to 100% color scale for comparison across evaluation settings.")
    populations = support["population"].unique(maintain_order=True).to_list()
    features = support["feature"].unique(maintain_order=True).to_list()
    z = [
        [
            support.filter(
                (pl.col("feature") == feature) & (pl.col("population") == population)
            ).item(0, "fraction_outside_training_range")
            for population in populations
        ]
        for feature in features
    ]
    heatmap = go.Figure(
        go.Heatmap(
            z=z,
            x=populations,
            y=[_feature_label(feature) for feature in features],
            zmin=0,
            zmax=scale_max,
            colorscale=[[0, "#252c36"], [0.5, "#1765a8"], [1, "#3285bc"]],
            xgap=2,
            ygap=2,
            colorbar={"title": "Outside range", "tickformat": ".0%"},
            hovertemplate=(
                "%{y}<br>%{x}<br>Measurements outside training range: %{z:.2%}<extra></extra>"
            ),
        )
    )
    for feature, values in zip(features, z, strict=True):
        for population, value in zip(populations, values, strict=True):
            heatmap.add_annotation(
                x=population,
                y=_feature_label(feature),
                text="0%" if value == 0 else f"{value:.1%}",
                showarrow=False,
                font={"color": "#929ba8" if value == 0 else "#ffffff", "size": 12},
            )
    heatmap.update_layout(
        title="Share of evaluated cycles outside each feature's training range",
        xaxis_title="Evaluation experiment",
        yaxis_title="",
        height=max(420, 30 * len(features) + 140),
    )
    st.plotly_chart(heatmap, width="stretch")
    st.caption(
        f"Maximum shown: {maximum['fraction_outside_training_range']:.1%} for "
        f"{_feature_label(maximum['feature'])} in {maximum['population']}, across the displayed "
        f"{PROTOCOL_LABELS[support_protocol]} features and populations. This is a marginal "
        "range check, not full "
        "distributional support, a cause, or a product limit."
    )

    st.subheader("What to do next")
    st.markdown(
        """
        1. **Expand the labeled operating envelope**—the combinations and ranges of process
           conditions for which the model has labeled examples and validation evidence—across
           its boundaries, interior and important combinations, not just more cycles from one
           familiar condition.
        2. **Keep holding out complete conditions, lots or machines** so familiar-condition
           accuracy cannot hide transfer failure.
        3. **Validate guardrails prospectively:** warn on unsupported inputs, physically measure
           those cases, and use the outcomes to test error, coverage and recalibration before
           automating any measurement decision.
        """
    )
    with st.expander("Future monitoring and intended-use details"):
        st.markdown(
            """
            An input-drift warning means the model may be outside its validated use; it does not
            mean the part is defective. Data-quality, operating-context and process-distribution
            changes can be checked immediately. Actual performance and interval-calibration drift
            require later measured weights. This dataset lacks authoritative wall-clock chronology,
            so it cannot validate temporal drift detection or warning delay.

            A future system could distinguish **represented**, **boundary/drift warning** and
            **unsupported** operation. Those states are not current product functionality; their
            thresholds need development selection and prospective validation.

            A deployable model should define and enforce:

            - supported machine, mold, material, target and operating envelope;
            - required inputs, units, sampling grid and prediction cutoff;
            - validated performance by relevant process condition;
            - unsupported conditions, warning/refusal rules and physical-measurement policy;
            - data/model identity, calibration date and the evidence required for recalibration.

            The operating loop is: **build the envelope → predict inside it → warn near or
            outside it → physically measure unsupported cases → expand and recalibrate**.
            """
        )


def render_dashboard(paths: DashboardPaths = DEFAULT_PATHS) -> None:
    """Render the bounded three-tab local dashboard."""
    st.set_page_config(page_title="Injection Molding · Quality Prediction", layout="wide")
    st.title("Injection Molding · Quality Prediction Under Process Shift")
    st.caption("scatimdata Dataset 2 · machine-cycle telemetry → molded-part weight")
    st.caption(
        "Existing portfolio evidence only · no model fitting, downloads, artifact writes, or "
        "remote services"
    )
    if st.button("Reload saved evidence", help="Use after regenerating local artifacts."):
        load_dashboard_data.clear()
    try:
        data = load_dashboard_data(paths)
    except (FileNotFoundError, ValueError) as error:
        st.error(str(error))
        return
    experiment_rows, _ = experiment_summary(data)
    prediction = prediction_headline(data)
    uncertainty = uncertainty_headline(data)
    data_kpi, prediction_kpi, reliability_kpi = st.columns(3)
    data_kpi.metric(
        "Loaded evidence",
        f"{cast(int, experiment_rows['labeled_cycles'].sum())} cycles",
    )
    data_kpi.caption(f"{experiment_rows.height} experiment groups")
    prediction_kpi.metric(
        "PLS pooled MAE — represented",
        f"{prediction['Represented conditions — pooled cycles']:.3f} g",
    )
    prediction_kpi.caption(
        f"Unseen experiment: {prediction['Unseen experiment — pooled cycles']:.3f} g"
    )
    reliability_kpi.metric(
        "Interval coverage — represented "
        f"(nominal {cast(float, data.uncertainty_run.get('nominal_coverage', 0.9)):.0%})",
        f"{uncertainty['secondary_id_empirical_coverage']:.1%}",
    )
    reliability_kpi.caption(f"Unseen experiment: {uncertainty['primary_empirical_coverage']:.1%}")
    st.info(
        "This project evaluates completed-cycle virtual measurement: software estimates a "
        "physical part-weight measurement from machine data after molding. It does not select "
        "one global production model or replace physical inspection. Dataset 2 provides no "
        "authoritative weight tolerance for this study, so these errors compare predictive "
        "reliability rather than product acceptance."
    )
    st.caption(
        "Study scope: three specific controlled transfer scenarios—two moisture experiments "
        "and one mold-temperature experiment—not independent estimates of arbitrary future "
        "manufacturing changes."
    )
    data_tab, prediction_tab, reliability_tab = st.tabs(
        ("Data & process", "Prediction & generalization", "Reliability under shift")
    )
    with data_tab:
        _render_data_tab(data)
    with prediction_tab:
        _render_prediction_tab(data)
    with reliability_tab:
        _render_reliability_tab(data)


if __name__ == "__main__":
    render_dashboard()
