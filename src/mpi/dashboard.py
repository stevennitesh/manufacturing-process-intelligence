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
PROTOCOL_LABELS: Final = {
    "primary": "Primary · entire experiment held out",
    "secondary_id": "Secondary ID · all experiment groups represented",
}


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
        "Injection molding injects molten plastic into a mold, holds it under pressure, then "
        "cools and removes the part. Pressure, flow, temperature and timing describe how it was "
        "made. We ask whether these machine records can estimate completed-part weight before "
        "using its physical measurement. Weight is one quality characteristic, not a complete "
        "acceptability verdict. "
        "Dataset 2 contains controlled injection-molding runs for a stacking-box part made from "
        "BASF Ultramid B3EG6 (PA6-GF30). Each labeled machine cycle maps to one molded part."
    )
    st.subheader("What one cycle contains—and how it is used")
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
                "| **Experimental context** | Experiment, moisture, mold-temperature and charge "
                "context describe controlled conditions; they group analysis but are not default "
                "model inputs. |",
                "| **Physical quality** | Part weight in grams is the target measured after "
                "molding. Geometry remains deferred because its released scale/mapping is "
                "unresolved. |",
            )
        )
    )
    st.caption(
        "The source also contains optional cavity-pressure/state data that this bounded MVP does "
        "not use. Another 92 signal-only cycles are excluded because they have no matching "
        "released scalar/quality row and therefore no supported weight target."
    )

    st.subheader("How the data becomes an experiment")
    st.graphviz_chart(
        r"""
        digraph pipeline {
            graph [rankdir=TB, bgcolor="transparent", nodesep=0.3, ranksep=0.45];
            node [shape=box, style="rounded,filled", fillcolor="#e8f0fa",
                  color="#7593b8", fontcolor="#172b45", fontname="Arial", fontsize=12];
            edge [color="#7593b8", fontcolor="#8798ab", fontname="Arial", fontsize=10];
            raw [label="Dataset 2 raw files\nScalars + pressure/flow + measured weight"];
            prepare [label="Validate and join by cycle identity\n"
                + "829 labeled parts; exclude 92 signal-only cycles\n"
                + "Preserve native 2,048-point signals"];
            split [label="Audit data and fix evaluation memberships\n"
                + "Primary: whole experiment held out, repeated three times\n"
                + "Secondary ID: random cycles from every experiment"];
            train [label="Fit/tune rows only\nA: 16 scalars\n"
                + "B: scalars + signal summaries\nC: scalars + compressed signals"];
            models [label="Train and tune predefined models\nMean / Ridge / PLS scalar baselines\n"
                + "Ridge / LightGBM representation comparisons\n"
                + "Fit scaling/compression inside training folds"];
            evaluate [label="Reserved evaluation cycles\n"
                + "Compare predictions with measured weights"];
            result [label="Prediction results\nStrong represented-group accuracy\n"
                + "Weak transfer; mixed trajectory benefit"];
            selected [label="Uncertainty study\nSelect scalar PLS or LightGBM\n"
                + "using development data only"];
            calibration [label="Reserved calibration cycles\n"
                + "Measured errors set 90% interval margin"];
            coverage [label="Evaluate intervals on reserved evaluation cycles\n"
                + "86.2% ID coverage; 5.2% under experiment shift"];
            gate [label="Development-only distance screen\n"
                + "One setup misses required error reduction\nNo automatic measurement policy"];
            explain [label="Explain saved predictions\n"
                + "Feature importance + input-range departures\n"
                + "Associations, not physical causes"];
            raw -> prepare -> split -> train -> models -> evaluate -> result;
            models -> selected -> calibration -> coverage;
            split -> calibration [style=dashed, label="reserve separately"];
            split -> evaluate [style=dashed, label="keep out of fitting/tuning"];
            selected -> gate;
            selected -> explain;
        }
        """,
        width="stretch",
    )
    st.markdown(
        "**Completed-cycle scalars + pressure/flow trajectories → predict part weight.** The "
        "model trains on two experiment groups and evaluates on the third, then repeats for all "
        "three groups. Scalars establish the baseline; trajectory representations test added "
        "value; context defines the holdout; weight never enters as a predictor. Separate "
        "calibration rows are reserved for prediction intervals. The uncertainty branch uses "
        "scalar models; it does not select a trajectory model from evaluation results. "
        "The dashboard reads saved results from these experiments."
    )

    st.subheader("How the controlled experiments differ")
    st.markdown(
        "\n".join(
            (
                "| Experiment | Labeled cycles | Observed controlled context | Mean part weight "
                "| Distinguishing evidence |",
                "| ---: | ---: | --- | ---: | --- |",
                "| 15 | 303 | Moisture: raw 0.050 → 0.100 → 0.150 | 115.956 g | Highest mean "
                "weight; first two moisture values differ from the paper. |",
                "| 20 | 223 | Moisture: raw 0.086 → 0.180 → 0.046 | 115.237 g | Broader "
                "pressure/flow-summary spread than experiment 23. |",
                "| 23 | 303 | Mold temperature: 80 → 90 → 70 (raw) | 114.308 g | Lowest/narrowest "
                "weight distribution; higher mean pressure and lower mean flow. |",
            )
        )
    )
    st.warning(
        "Each experiment contains several settings; validation withholds the whole group. "
        "The temperature values match the paper's °C settings, but the unit mapping is inferred. "
        "These are source experiment groups, not verified calendar days. The context identifies "
        "controlled interventions, but other process measurements move with them; it does not "
        "prove that moisture or mold temperature alone caused the weight differences."
    )
    weights = weight_rows(data)
    counts = weights.group_by("experiment_id").agg(pl.len().alias("cycles")).sort("experiment_id")
    count_columns = st.columns(counts.height)
    for column, row in zip(count_columns, counts.iter_rows(named=True), strict=True):
        column.metric(f"Experiment {row['experiment_id']}", f"{row['cycles']} cycles")

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
        "About 70.45% of observed weight variation lies between these three experiment groups. "
        "Pooled "
        "metrics can therefore reward condition separation while hiding weaker within-condition "
        "explanation or transfer to a new condition."
    )

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
    st.success(
        "Scalar PLS reached 0.114 g pooled MAE when every experiment group was "
        "represented during training, but 0.503 g equal-fold MAE when a complete experiment was "
        "withheld. Familiar-condition accuracy did not establish new-condition transfer."
    )
    st.subheader("How the experiment works")
    st.markdown(
        "**Train on two experiment groups → evaluate on the third → repeat for all three.** "
        "Each group contains multiple settings. The separate in-distribution (ID) benchmark "
        "randomly splits cycles within every group; neighboring-cycle similarity can make it "
        "optimistic for later production. The original paper's "
        "random cross-validation asked whether detailed signals improve prediction within the "
        "available condition mixture; this project asks the harder transfer question. Our "
        "features and models also differ, so this is an extension, not an exact replication."
    )
    st.markdown(
        "**Reading the comparisons:** MAE is average absolute weight error in grams (lower is "
        "better). Primary means an entire experiment is held out; secondary ID means all groups "
        "are represented. Equal-fold means weight each experiment equally; pooled means weight "
        "each cycle equally. **Mean** predicts a constant training average; **Ridge** is a "
        "regularized linear model; **PLS** learns components linking correlated inputs to weight; "
        "**LightGBM** learns nonlinear relationships with decision trees."
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
            title="Familiar-condition accuracy does not transfer automatically",
            y_title="MAE (g)",
        ),
        width="stretch",
    )
    st.caption(
        "Scalar PLS reached 0.114 g pooled MAE with represented conditions and 0.503 g "
        "equal-fold MAE with whole-experiment holdouts. The protocols use separately fitted "
        "pipelines, so this gap is descriptive rather than a paired causal effect."
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
        "A = scalar only; B = scalars plus engineered pressure/flow summaries; C-PCA and C-PLS "
        "= scalars plus compressed trajectories. PCA summarizes signal variation; PLS compression "
        "learns components associated with training weights, before Ridge/LightGBM predicts. "
        "Benefits varied by experiment; none of these Ridge/LightGBM "
        "representations beat scalar PLS's 0.503 g grouped aggregate. This is a descriptive "
        "comparison of predefined experiments, not an outer-selected deployment winner."
    )

    st.subheader("Where trajectories helped—and where they hurt")
    delta_rows = []
    for family_name, metrics in (
        ("Ridge", data.ridge_metrics),
        ("LightGBM", data.lightgbm_metrics),
    ):
        primary = metrics.filter(pl.col("protocol") == "primary")
        baseline = primary.filter(pl.col("representation") == "A").select(
            "fold", pl.col("mae_g").alias("scalar_mae_g")
        )
        delta_rows.append(
            primary.filter(pl.col("representation") != "A")
            .join(baseline, on="fold", validate="m:1")
            .with_columns(
                (pl.col("scalar_mae_g") - pl.col("mae_g")).alias("improvement_g"),
                pl.concat_str(pl.lit(family_name + " · "), "representation").alias("comparison"),
                pl.col("fold")
                .str.replace("holdout_experiment_", "Experiment ")
                .alias("experiment"),
            )
            .select("experiment", "comparison", "improvement_g")
        )
    delta_figure = _bar_chart(
        pl.concat(delta_rows).sort("experiment", "comparison"),
        "experiment",
        "improvement_g",
        "comparison",
        title="Trajectory benefit relative to the same model's scalar baseline",
        y_title="Scalar MAE - augmented MAE (g)",
    )
    delta_figure.add_hline(y=0, line_color="gray")
    st.plotly_chart(delta_figure, width="stretch")
    st.caption(
        "Above zero means trajectories reduced error; below zero means they increased it. "
        "Each comparison uses the same held-out experiment and model family."
    )

    st.subheader("What was learned and what comes next")
    learned, next_step = st.columns(2)
    with learned:
        st.markdown(
            """
            **Learned from this experiment**

            - About 70.45% of observed weight variation was between experiment groups, so
              pooled performance can hide weak within-condition explanation.
            - Scalar PLS transferred better on aggregate than the tested nonlinear and
              trajectory alternatives; complexity did not replace condition coverage.
            - Held-out conditions often extended beyond fitted marginal ranges, but that does
              not prove range departure caused every error.
            - Predictive importance changed by population; no universal or causal sensor ranking
              was established.
            - This is a completed-cycle weight estimate, not control, conformance or physical
              root-cause analysis.
            """
        )
    with next_step:
        st.markdown(
            """
            **The next question: does the model know when it is unreliable?**

            The Reliability tab tests whether calibrated intervals still contain measured
            weights under experiment shift, and whether input distance identifies predictions
            that need physical measurement. Those results determine the next data-collection
            and validation steps.
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
            "Protocol",
            ("primary", "secondary_id"),
            key="prediction_protocol",
            format_func=PROTOCOL_LABELS.__getitem__,
        )
    )
    choices = sorted(
        predictions.filter(pl.col("protocol") == protocol)[group_column].unique().to_list()
    )
    default_choice = choices.index("pls") if "pls" in choices else 0
    choice = str(st.selectbox("Model / representation", choices, index=default_choice))
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
    st.dataframe(experiment_table, hide_index=True, width="stretch")

    st.subheader("Population-specific predictive importance")
    st.write(
        "Permutation importance shuffles one input across evaluated parts and measures the "
        "change in prediction error. Positive values mean shuffling hurt predictions; negative "
        "values mean it improved this model's predictions, not that changing the physical "
        "process would help. "
        "Importance changed with the evaluated population. Switchover pressure led several "
        "populations, while injection time led represented experiment 23; 40 of 96 saved mean "
        "importances were negative. The chart explains one fitted model and population at a "
        "time—not a universal sensor hierarchy."
    )
    importance_protocol = str(
        st.selectbox(
            "Importance protocol",
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
    st.error(
        "Nominal 90% intervals covered 86.2% of represented-group outcomes "
        "but only 5.2% under held-out-experiment shift. The input-distance score missed the "
        "required error-reduction threshold in one development setup, so no automatic "
        "measurement policy is claimed."
    )
    st.write(
        "This uncertainty study selects between scalar PLS and LightGBM using development "
        "data separately for each fold, then calibrates on reserved cycles. LightGBM was "
        "selected for held-out experiments 15/20 and the ID benchmark; PLS for experiment 23. "
        "A nominal 90% interval aims to contain nine in ten measured weights under its "
        "assumptions; empirical coverage is how often it actually did. Calibration sets one "
        "fixed error margin per fitted model, so intervals do not automatically widen for "
        "an unfamiliar cycle."
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
    st.caption(
        "Experiment 23 illustrates the failure mode: its interval averaged 0.550 g wide, yet "
        "coverage was about 0.3%. That calibrated interval was insufficient to cover the "
        "systematic underprediction; no separate interval-widening experiment was run."
    )

    m8_eligible = data.uncertainty_run.get("m8_eligible")
    st.subheader("Why the selective-measurement gate stopped")
    st.write(
        "M7 tested whether distance from familiar training cycles could identify predictions "
        "that were safer to accept. Retaining the closest 75% had to reduce development MAE by "
        "at least 10% in every primary fold before M8 could proceed."
    )
    st.markdown(
        """
        | Future held-out experiment | Development MAE reduction | Decision |
        | --- | ---: | --- |
        | Experiment 15 | 19.66% | Pass |
        | Experiment 20 | 4.31% | **Fail** |
        | Experiment 23 | 16.31% | Pass |
        """
    )
    st.warning(
        "The all-fold gate failed. Input distance can identify an unfamiliar cycle without "
        "reliably identifying whether its weight prediction will be wrong. The project therefore "
        f"stopped before risk-coverage curves or an automatic measurement rule (M8 eligible: "
        f"{m8_eligible}) instead of searching for a favorable score after seeing the result."
    )

    st.subheader("Saved interval example")
    protocol = str(
        st.selectbox(
            "Interval protocol",
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
        f"Selected model: {interval_model}. "
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
        title=f"Saved intervals · {protocol} · experiment {experiment}",
        xaxis_title="Cycle counter",
        yaxis_title="Weight (g)",
    )
    st.plotly_chart(interval_figure, width="stretch")

    st.subheader("Observed marginal feature-range departures")
    support_protocol = str(
        st.selectbox(
            "Support protocol",
            ("primary", "secondary_id"),
            key="support_protocol",
            format_func=PROTOCOL_LABELS.__getitem__,
        )
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

    st.subheader("What to do next")
    st.markdown(
        """
        1. **Expand the labeled operating envelope** across its boundaries, interior and important
           combinations—not just more cycles from one familiar condition.
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
