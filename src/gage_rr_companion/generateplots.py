import pandas as pd
import numpy as np
import altair as alt


def _first_present_value(mapping, keys):
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _resolve_tolerance(gage_rr_results, explicit_tolerance):
    if explicit_tolerance is not None:
        return explicit_tolerance

    candidate = _first_present_value(
        gage_rr_results,
        [
            "tolerance",
            "Tolerance",
            "total_tolerance",
            "TotalTolerance",
            "process_tolerance",
            "ProcessTolerance",
        ],
    )
    if candidate is not None:
        return candidate

    metadata = gage_rr_results.get("metadata", {})
    if isinstance(metadata, dict):
        candidate = _first_present_value(
            metadata,
            [
                "tolerance",
                "Tolerance",
                "total_tolerance",
                "TotalTolerance",
                "process_tolerance",
                "ProcessTolerance",
            ],
        )
        if candidate is not None:
            return candidate

        lower = _first_present_value(metadata, ["lsl", "LSL", "lower_spec_limit"])
        upper = _first_present_value(metadata, ["usl", "USL", "upper_spec_limit"])
        if lower is not None and upper is not None:
            return float(upper) - float(lower)

    return None


def _apply_black_chart_text(chart):
    return (
        chart.configure_axis(labelColor="black", titleColor="black")
        .configure_legend(labelColor="black", titleColor="black")
        .configure_title(color="black")
    )


def _component_variation_chart_data(variance_components, gage_rr_results, tolerance=None):
    source_labels = {
        "Total Gage R&R": "Gage R&R",
        "Repeatability": "Repeat",
        "Reproducibility": "Reprod",
        "Part-To-Part": "Part-to-Part",
        "Part-to-Part": "Part-to-Part",
    }
    source_order = ["Gage R&R", "Repeat", "Reprod", "Part-to-Part"]

    var_df = variance_components.copy()
    var_df["Component"] = var_df["Source"].map(source_labels)
    var_df = var_df[var_df["Component"].notna()].copy()

    if "PercentStudyVar" not in var_df.columns:
        if "StudyVar" not in var_df.columns:
            var_df["StudyVar"] = 6 * np.sqrt(var_df["VarianceComponent"].clip(lower=0))
        total_study_var = var_df.loc[
            var_df["Source"] == "Total Variation",
            "StudyVar",
        ]
        if total_study_var.empty:
            all_study_var = 6 * np.sqrt(
                variance_components["VarianceComponent"].clip(lower=0)
            )
            total_rows = variance_components["Source"] == "Total Variation"
            total_study_var = all_study_var[total_rows]
        denominator = float(total_study_var.iloc[0]) if not total_study_var.empty else 0.0
        var_df["PercentStudyVar"] = (
            var_df["StudyVar"] / denominator * 100 if denominator else np.nan
        )

    resolved_tolerance = _resolve_tolerance(gage_rr_results, tolerance)
    if "PercentTolerance" not in var_df.columns and resolved_tolerance:
        if "StudyVar" not in var_df.columns:
            var_df["StudyVar"] = 6 * np.sqrt(var_df["VarianceComponent"].clip(lower=0))
        var_df["PercentTolerance"] = var_df["StudyVar"] / float(resolved_tolerance) * 100

    series = [
        ("PercentContribution", "% Contribution"),
        ("PercentStudyVar", "% Study Var"),
    ]
    if "PercentTolerance" in var_df.columns:
        series.append(("PercentTolerance", "% Tolerance"))

    rows = []
    for source in [
        "Total Gage R&R",
        "Repeatability",
        "Reproducibility",
        "Part-To-Part",
        "Part-to-Part",
    ]:
        component_rows = var_df[var_df["Source"] == source]
        if component_rows.empty:
            continue
        row = component_rows.iloc[0]
        for column, label in series:
            value = row.get(column)
            if pd.notna(value):
                rows.append({
                    "Component": row["Component"],
                    "Metric": label,
                    "Percent": float(value),
                })

    chart_df = pd.DataFrame(rows)
    if not chart_df.empty:
        chart_df["Component"] = pd.Categorical(
            chart_df["Component"],
            categories=source_order,
            ordered=True,
        )
        chart_df["Metric"] = pd.Categorical(
            chart_df["Metric"],
            categories=[label for _, label in series],
            ordered=True,
        )
        chart_df = chart_df.sort_values(["Component", "Metric"]).reset_index(drop=True)
    return chart_df, [label for _, label in series]


def generateplots(
    df,
    gage_rr_results,
    operator_col="Operator",
    part_col="Part",
    trial_col="Trial",
    value_col="Value",
    tolerance=None
):
    """
    Generate standard Gage R&R visualization charts with control limits,
    average lines, autoscaling, and operator grouping.
    """

    # -----------------------------
    # Input Validation
    # -----------------------------
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    if df.empty:
        raise ValueError("Input DataFrame cannot be empty.")

    if not isinstance(gage_rr_results, dict):
        raise TypeError("gage_rr_results must be a dictionary.")

    required_cols = [operator_col, part_col, trial_col, value_col]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' missing from DataFrame.")

    required_keys = ["variance_components", "metadata"]
    for key in required_keys:
        if key not in gage_rr_results:
            raise ValueError(f"Missing required key in results: {key}")

    variance_components = gage_rr_results["variance_components"]
    if "PercentContribution" not in variance_components.columns:
        raise ValueError("variance_components must contain 'PercentContribution' column.")

    # -----------------------------
    # Compute summary values for control lines
    # -----------------------------
    xbar_df = df.groupby([operator_col, part_col], observed=True)[value_col].mean().reset_index(name="Xbar")
    xbar_df = xbar_df.sort_values([operator_col, part_col]).reset_index(drop=True)
    xbar_df["Subgroup"] = range(1, len(xbar_df) + 1)
    avg_xbar = xbar_df["Xbar"].mean()

    r_df = df.groupby([operator_col, part_col], observed=True)[value_col].agg(lambda x: x.max() - x.min()).reset_index(name="Range")
    r_df = r_df.sort_values([operator_col, part_col]).reset_index(drop=True)
    r_df["Subgroup"] = range(1, len(r_df) + 1)
    avg_r = r_df["Range"].mean()

    n_replicates = df.groupby([operator_col, part_col], observed=True)[value_col].count().min()
    if n_replicates < 2 or n_replicates > 10:
        raise ValueError("Number of replicates per part/operator must be between 2 and 10.")

    d2_table = {2:1.128, 3:1.693, 4:2.059, 5:2.326, 6:2.534, 7:2.704, 8:2.847, 9:2.970, 10:3.078}
    d2 = d2_table[n_replicates]
    sigma_est = avg_r / d2
    xbar_control_width = 3 * sigma_est / np.sqrt(n_replicates)
    ucl_xbar = avg_xbar + xbar_control_width
    lcl_xbar = avg_xbar - xbar_control_width

    # -----------------------------
    # X-bar Control Chart
    # -----------------------------
    xbar_chart_points = (
        alt.Chart(xbar_df)
        .mark_point(filled=True, size=60)
        .encode(
            x=alt.X("Subgroup:O", title="Subgroup", axis=alt.Axis(labelAngle=0, labelColor="black")),
            y=alt.Y("Xbar:Q", title="Mean Measurement", scale=alt.Scale(zero=False), axis=alt.Axis(ticks=False, labelColor="black")),
            shape=alt.Shape(f"{operator_col}:N", title="Operator"),
            color=alt.Color(f"{operator_col}:N", title="Operator"),
            tooltip=[operator_col, part_col, "Xbar"]
        )
    )

    xbar_lines = alt.layer(
        alt.Chart(pd.DataFrame({"y":[avg_xbar]})).mark_rule(color="grey", strokeDash=[4,4], size=2).encode(y="y:Q"),
        alt.Chart(pd.DataFrame({"y":[ucl_xbar]})).mark_rule(color="red", size=2).encode(y="y:Q"),
        alt.Chart(pd.DataFrame({"y":[lcl_xbar]})).mark_rule(color="red", size=2).encode(y="y:Q")
    )

    xbar_chart = _apply_black_chart_text(
        alt.layer(xbar_chart_points, xbar_lines).properties(
            title="X-Bar Control Chart"
        ).configure_view(
            stroke="black"
        )
    )

    # -----------------------------
    # R Control Chart
    # -----------------------------
    d3_d4_table = {2:(0,3.267),3:(0,2.574),4:(0,2.282),5:(0,2.114),
                   6:(0,2.004),7:(0.076,1.924),8:(0.136,1.864),
                   9:(0.184,1.816),10:(0.223,1.777)}
    d3,d4 = d3_d4_table[n_replicates]
    ucl_r = avg_r*d4
    lcl_r = avg_r*d3

    r_chart_points = (
        alt.Chart(r_df)
        .mark_point(filled=True, size=60)
        .encode(
            x=alt.X("Subgroup:O", title="Subgroup", axis=alt.Axis(labelAngle=0, labelColor="black")),
            y=alt.Y("Range:Q", title="Range", scale=alt.Scale(zero=False), axis=alt.Axis(labelColor="black")),
            shape=alt.Shape(f"{operator_col}:N", title="Operator"),
            color=alt.Color(f"{operator_col}:N", title="Operator"),
            tooltip=[operator_col, part_col, "Range"]
        )
    )

    r_lines = alt.layer(
        alt.Chart(pd.DataFrame({"y":[avg_r]})).mark_rule(color="grey", strokeDash=[4,4], size=2).encode(y="y:Q"),
        alt.Chart(pd.DataFrame({"y":[ucl_r]})).mark_rule(color="red", size=2).encode(y="y:Q"),
        alt.Chart(pd.DataFrame({"y":[lcl_r]})).mark_rule(color="red", size=2).encode(y="y:Q")
    )

    r_chart = _apply_black_chart_text(
        alt.layer(r_chart_points, r_lines).properties(
            title="R Control Chart"
        ).configure_view(
            stroke="black"
        )
    )

    # -----------------------------
    # Operator Box Plot
    # -----------------------------
    operator_boxplot = _apply_black_chart_text(
        alt.Chart(df)
        .mark_boxplot(
            color="#4C78A8",
            extent=1.5,
            median={"color": "#1F2937", "strokeWidth": 2},
            outliers={"filled": True, "fill": "#F58518", "size": 45},
            rule={"color": "#374151"},
            size=42,
            ticks={"color": "#374151", "size": 42},
        )
        .encode(
            x=alt.X(
                f"{operator_col}:N",
                title="Operator",
                axis=alt.Axis(labelAngle=0, labelColor="black", titleColor="black"),
            ),
            y=alt.Y(
                f"{value_col}:Q",
                title="Measurement Value",
                scale=alt.Scale(zero=False),
                axis=alt.Axis(
                    grid=True,
                    gridColor="#E5E7EB",
                    labelColor="black",
                    titleColor="black",
                ),
            ),
            tooltip=[operator_col, alt.Tooltip(f"{value_col}:Q", title="Value")],
        )
        .properties(title="Measurement Distribution by Operator")
        .configure_view(stroke="#9CA3AF")
    )

    # -----------------------------
    # Components of Variation
    # -----------------------------
    variation_df, metric_domain = _component_variation_chart_data(
        variance_components,
        gage_rr_results,
        tolerance=tolerance,
    )
    color_range = ["#7EA6D8", "#C95F54"]
    if "% Tolerance" in metric_domain:
        color_range.append("#FFF176")

    variance_chart = _apply_black_chart_text(
        alt.Chart(variation_df)
        .mark_bar(stroke="#666666", strokeWidth=0.6)
        .encode(
            x=alt.X(
                "Component:N",
                title=None,
                sort=["Gage R&R", "Repeat", "Reprod", "Part-to-Part"],
                axis=alt.Axis(labelAngle=0, labelColor="black", titleColor="black"),
            ),
            xOffset=alt.XOffset("Metric:N", sort=metric_domain),
            y=alt.Y(
                "Percent:Q",
                title="Percent",
                scale=alt.Scale(zero=True),
                axis=alt.Axis(labelColor="black", titleColor="black"),
            ),
            color=alt.Color(
                "Metric:N",
                title=None,
                scale=alt.Scale(domain=metric_domain, range=color_range),
                legend=alt.Legend(orient="right", labelColor="black", titleColor="black"),
            ),
            tooltip=["Component:N", "Metric:N", alt.Tooltip("Percent:Q", format=".2f")],
        )
        .properties(title="Components of Variation")
        .configure_view(stroke="black")
    )

    return {
        "xbar_control_chart": xbar_chart,
        "r_control_chart": r_chart,
        "operator_boxplot": operator_boxplot,
        "variance_histogram": variance_chart
    }