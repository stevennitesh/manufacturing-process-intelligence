# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Offline presentation of the saved Dataset 2 portfolio evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np
import plotly.graph_objects as go
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
                        "M3 memberships, then reload saved evidence."
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
                    "population": "Primary equal-fold mean",
                    "mae_g": cast(float, primary["mae_g"].mean()),
                },
                {
                    group: value,
                    "population": "Primary pooled (sample-weighted)",
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
                    "population": "Separate ID pooled",
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


def coverage_summary(metrics: pl.DataFrame) -> pl.DataFrame:
    """Keep primary and both pooled/per-experiment ID interval results visibly distinct."""
    return metrics.with_columns(
        pl.when(pl.col("protocol") == "primary")
        .then(pl.concat_str(pl.lit("Primary · "), pl.col("fold").str.replace("holdout_", "")))
        .when(pl.col("fold") == "within_experiment")
        .then(pl.lit("ID · pooled"))
        .otherwise(pl.concat_str(pl.lit("ID · "), pl.col("fold")))
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


def _render_data_tab(data: DashboardData) -> None:
    st.header("Data & process")
    st.write(
        "Machine telemetry is linked to the weight of one molded part. Weight is measured in "
        "grams; injection pressure and flow amplitudes remain in source-native units because "
        "their physical units are unresolved. Experiments are controlled groups, not calendar days."
    )
    weights = weight_rows(data)
    counts = weights.group_by("experiment_id").agg(pl.len().alias("cycles")).sort("experiment_id")
    count_columns = st.columns(counts.height)
    for column, row in zip(count_columns, counts.iter_rows(named=True), strict=True):
        column.metric(f"Experiment {row['experiment_id']}", f"{row['cycles']} cycles")

    figure = go.Figure()
    for experiment, rows in weights.partition_by("experiment_id", as_dict=True).items():
        value = experiment[0]
        figure.add_box(name=f"Experiment {value}", y=rows["weight_g"].to_list(), boxpoints=False)
    figure.update_layout(title="Observed part-weight distributions", yaxis_title="Weight (g)")
    st.plotly_chart(figure, width="stretch")

    st.subheader("Native cycle example")
    experiments = sorted(data.context["experiment_id"].unique().to_list())
    experiment = cast(int, st.selectbox("Experiment", experiments, key="cycle_experiment"))
    candidates = data.context.filter(pl.col("experiment_id") == experiment)["unit_id"].to_list()
    unit_id = str(st.selectbox("Cycle", candidates, key="cycle_unit"))
    cycle = data.signals.filter(pl.col("unit_id") == unit_id).sort("sample_index")
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
    st.write(
        "The headline is equal-fold MAE across held-out experiments. Pooled primary MAE is shown "
        "separately and is sample-weighted. The ID comparison uses separately fitted pipelines, so "
        "it is not a paired estimate of the effect of process shift."
    )
    st.info(
        "Retrospective grouped cross-validation: M2 inspected all three experiments before M3 "
        "fixed the evaluation contract. These are not prospective untouched holdouts."
    )
    scalar = headline_mae(data.scalar_metrics, data.scalar_predictions, "model")
    st.plotly_chart(
        _bar_chart(
            scalar,
            "model",
            "mae_g",
            "population",
            title="Scalar baseline MAE",
            y_title="MAE (g)",
        ),
        width="stretch",
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
            "Representation-comparison population",
            comparisons["population"].unique(maintain_order=True).to_list(),
        )
    )
    selected_comparison = comparisons.filter(pl.col("population") == population).with_columns(
        pl.concat_str("model_family", pl.lit(" · "), "representation").alias("series")
    )
    st.plotly_chart(
        _bar_chart(
            selected_comparison,
            "representation",
            "mae_g",
            "model_family",
            title=f"Matched representation comparison · {population}",
            y_title="MAE (g)",
        ),
        width="stretch",
    )
    st.caption(
        "A = scalar only; B = engineered pressure/flow summaries; C-PCA and C-PLS = compressed "
        "native trajectories. Results vary by experiment; no universal representation won."
    )

    st.subheader("Per-experiment predictions")
    family = str(
        st.selectbox(
            "Model family",
            ("Scalar baselines", "Ridge representations", "LightGBM representations"),
        )
    )
    predictions, group_column = _prediction_source(data, family)
    protocol = str(st.selectbox("Protocol", ("primary", "secondary_id"), key="prediction_protocol"))
    choices = sorted(
        predictions.filter(pl.col("protocol") == protocol)[group_column].unique().to_list()
    )
    choice = str(st.selectbox("Model / representation", choices))
    selected = predictions.filter(
        (pl.col("protocol") == protocol) & (pl.col(group_column) == choice)
    )
    experiments = sorted(selected["experiment_id"].unique().to_list())
    experiment = cast(
        int, st.selectbox("Evaluation experiment", experiments, key="prediction_experiment")
    )
    selected = selected.filter(pl.col("experiment_id") == experiment)
    actual_figure = go.Figure()
    actual_figure.add_scatter(
        x=selected["observed_weight_g"].to_list(),
        y=selected["predicted_weight_g"].to_list(),
        mode="markers",
        name="Cycles",
    )
    low = min(
        cast(float, selected["observed_weight_g"].min()),
        cast(float, selected["predicted_weight_g"].min()),
    )
    high = max(
        cast(float, selected["observed_weight_g"].max()),
        cast(float, selected["predicted_weight_g"].max()),
    )
    actual_figure.add_scatter(x=[low, high], y=[low, high], mode="lines", name="Ideal")
    actual_figure.update_layout(
        title=f"{family} · {choice} · experiment {experiment}",
        xaxis_title="Observed weight (g)",
        yaxis_title="Predicted weight (g)",
    )
    st.plotly_chart(actual_figure, width="stretch")
    experiment_table = per_experiment_metrics(predictions, group_column).filter(
        (pl.col("protocol") == protocol) & (pl.col(group_column) == choice)
    )
    st.dataframe(experiment_table, hide_index=True, width="stretch")

    st.subheader("Population-specific predictive importance")
    importance_protocol = str(
        st.selectbox("Importance protocol", ("primary", "secondary_id"), key="importance_protocol")
    )
    importance_experiments = sorted(
        data.importance.filter(pl.col("protocol") == importance_protocol)[
            "evaluation_experiment_id"
        ]
        .unique()
        .to_list()
    )
    importance_experiment = cast(
        int,
        st.selectbox("Importance experiment", importance_experiments, key="importance_experiment"),
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
            y=importance["feature"].to_list(),
            error_x={"type": "data", "array": importance["importance_std_g"].to_list()},
            orientation="h",
        )
    )
    importance_figure.update_layout(
        title=(
            f"Permutation importance · {model_family} · {importance_protocol} · "
            f"experiment {importance_experiment}"
        ),
        xaxis_title="Change in MAE after permutation (g; negative values retained)",
        yaxis_title="",
    )
    st.plotly_chart(importance_figure, width="stretch")
    st.caption(
        f"Selected model: {model_family}; saved settings: {model_settings}. Error bars are the "
        f"standard deviation over {repeat_count} saved permutations, not confidence intervals."
    )
    st.warning(
        "Permutation importance describes this fitted model and population. Correlated inputs and "
        "poor unseen-regime transfer complicate interpretation; it is not a physical or causal "
        "ranking."
    )


def _render_reliability_tab(data: DashboardData) -> None:
    st.header("Reliability under shift")
    st.write(
        "Intervals target 90% marginal coverage. Empirical coverage under held-out-experiment "
        "shift "
        "was poor; experiment 23 retained a small nonzero coverage of about 0.3%."
    )
    coverage = coverage_summary(data.interval_metrics)
    coverage_figure = go.Figure()
    coverage_figure.add_bar(
        name="Empirical coverage",
        x=coverage["population"].to_list(),
        y=coverage["empirical_coverage"].to_list(),
        customdata=coverage["mean_width_g"].to_list(),
        hovertemplate="%{x}<br>coverage=%{y:.3f}<br>mean width=%{customdata:.3f} g<extra></extra>",
    )
    coverage_figure.add_scatter(
        name="90% nominal", x=coverage["population"].to_list(), y=[0.9] * coverage.height
    )
    coverage_figure.update_layout(
        title="Nominal versus empirical interval coverage",
        yaxis_title="Coverage fraction",
        xaxis_title="",
        yaxis={"range": [0.0, 1.0]},
    )
    st.plotly_chart(coverage_figure, width="stretch")
    st.dataframe(
        coverage.select(
            "population",
            "evaluation_count",
            "nominal_coverage",
            "empirical_coverage",
            "mean_width_g",
        ),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Saved interval example")
    protocol = str(st.selectbox("Interval protocol", ("primary", "secondary_id")))
    interval_rows = data.interval_predictions.filter(pl.col("protocol") == protocol)
    experiments = sorted(interval_rows["experiment_id"].unique().to_list())
    experiment = cast(int, st.selectbox("Interval experiment", experiments))
    interval_rows = interval_rows.filter(pl.col("experiment_id") == experiment).sort(
        "cycle_counter"
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
        title=f"Saved intervals · {protocol} · experiment {experiment}",
        xaxis_title="Cycle counter",
        yaxis_title="Weight (g)",
    )
    st.plotly_chart(interval_figure, width="stretch")

    st.subheader("Observed marginal feature-range departures")
    support_protocol = str(
        st.selectbox("Support protocol", ("primary", "secondary_id"), key="support_protocol")
    )
    support = support_heatmap_table(data.support, support_protocol)
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
            y=features,
            zmin=0,
            zmax=1,
            colorbar={"title": "Fraction"},
            hovertemplate="%{y}<br>%{x}<br>outside training range=%{z:.3f}<extra></extra>",
        )
    )
    heatmap.update_layout(
        title=f"Fraction outside marginal training range · {support_protocol}",
        xaxis_title="Evaluation population",
        yaxis_title="",
    )
    st.plotly_chart(heatmap, width="stretch")
    maximum = support.sort("fraction_outside_training_range", descending=True).row(0, named=True)
    st.caption(
        f"Maximum shown: {maximum['fraction_outside_training_range']:.1%} for "
        f"{maximum['feature']} in {maximum['population']}, across the displayed "
        f"{support_protocol} features and populations. This is a marginal range check, not full "
        "distributional support, a cause, or a product limit."
    )

    m8_eligible = data.uncertainty_run.get("m8_eligible")
    st.error(
        "The development-only distance gate did not pass every required fold "
        f"(saved M8 eligibility: {m8_eligible}). M8 was skipped: there is no validated "
        "selective-measurement curve or support-based deployment policy. Feature shift co-occurs "
        "with errors, but is not established as their dominant cause."
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
