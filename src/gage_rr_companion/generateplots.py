import pandas as pd
import altair as alt

def generateplots(
    df,
    gage_rr_results,
    operator_col="Operator",
    part_col="Part",
    trial_col="Trial",
    value_col="Value"
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
    xbar_df = df.groupby([operator_col, part_col])[value_col].mean().reset_index(name="Xbar")
    xbar_df = xbar_df.sort_values([operator_col, part_col]).reset_index(drop=True)
    xbar_df["Subgroup"] = range(1, len(xbar_df) + 1)
    avg_xbar = xbar_df["Xbar"].mean()

    r_df = df.groupby([operator_col, part_col])[value_col].agg(lambda x: x.max() - x.min()).reset_index(name="Range")
    r_df = r_df.sort_values([operator_col, part_col]).reset_index(drop=True)
    r_df["Subgroup"] = range(1, len(r_df) + 1)
    avg_r = r_df["Range"].mean()

    n_replicates = df.groupby([operator_col, part_col])[value_col].count().min()
    if n_replicates < 2 or n_replicates > 10:
        raise ValueError("Number of replicates per part/operator must be between 2 and 10.")

    d2_table = {2:1.128, 3:1.693, 4:2.059, 5:2.326, 6:2.534, 7:2.704, 8:2.847, 9:2.970, 10:3.078}
    d2 = d2_table[n_replicates]
    sigma_est = avg_r / d2
    ucl_xbar = avg_xbar + 3*sigma_est
    lcl_xbar = avg_xbar - 3*sigma_est

    # -----------------------------
    # X-bar Control Chart
    # -----------------------------
    xbar_chart = (
        alt.Chart(xbar_df)
        .mark_point(filled=True, size=60)
        .encode(
            x=alt.X("Subgroup:O", title="Subgroup", axis=alt.Axis(labelAngle=0, labelColor="black")),
            y=alt.Y("Xbar:Q", title="Mean Measurement", scale=alt.Scale(zero=False), axis=alt.Axis(ticks=True)),
            shape=alt.Shape(f"{operator_col}:N", title="Operator"),
            color=alt.Color(f"{operator_col}:N", title="Operator"),
            tooltip=[operator_col, part_col, "Xbar"]
        )
    )

    # Control lines
    xbar_lines = alt.layer(
        # Average
        alt.Chart(pd.DataFrame({"y":[avg_xbar]})).mark_rule(color="grey", strokeDash=[4,4], size=2).encode(y="y:Q"),
        # UCL
        alt.Chart(pd.DataFrame({"y":[ucl_xbar]})).mark_rule(color="red", size=2).encode(y="y:Q"),
        # LCL
        alt.Chart(pd.DataFrame({"y":[lcl_xbar]})).mark_rule(color="red", size=2).encode(y="y:Q")
    )

    xbar_chart = alt.layer(xbar_chart, xbar_lines).properties(
        title="X-Bar Control Chart"
    ).configure_view(
        stroke="black"
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
            y=alt.Y("Range:Q", title="Range", scale=alt.Scale(zero=False)),
            shape=alt.Shape(f"{operator_col}:N", title="Operator"),
            color=alt.Color(f"{operator_col}:N", title="Operator"),
            tooltip=[operator_col, part_col, "Range"]
        )
    )

    r_lines = alt.layer(
        # Average
        alt.Chart(pd.DataFrame({"y":[avg_r]})).mark_rule(color="grey", strokeDash=[4,4], size=2).encode(y="y:Q"),
        # UCL
        alt.Chart(pd.DataFrame({"y":[ucl_r]})).mark_rule(color="red", size=2).encode(y="y:Q"),
        # LCL
        alt.Chart(pd.DataFrame({"y":[lcl_r]})).mark_rule(color="red", size=2).encode(y="y:Q")
    )

    r_chart = alt.layer(r_chart_points, r_lines).properties(
        title="R Control Chart"
    ).configure_view(
        stroke="black"
    )

    # -----------------------------
    # Operator Box Plot
    # -----------------------------
    operator_boxplot = (
        alt.Chart(df)
        .mark_boxplot()
        .encode(
            x=alt.X(f"{operator_col}:N", title="Operator"),
            y=alt.Y(f"{value_col}:Q", title="Measurement Value", scale=alt.Scale(zero=False))
        )
        .properties(title="Operator Measurement Distribution")
        .configure_view(stroke="black")
    )

    # -----------------------------
    # Variance Contribution Histogram
    # -----------------------------
    var_df = variance_components.copy()
    variance_chart = (
        alt.Chart(var_df)
        .mark_bar()
        .encode(
            x=alt.X("Source:N", title="Variance Source"),
            y=alt.Y("PercentContribution:Q", title="Percent Contribution", scale=alt.Scale(zero=False)),
        )
        .properties(title="Variance Contribution")
        .configure_view(stroke="black")
    )

    return {
        "xbar_control_chart": xbar_chart,
        "r_control_chart": r_chart,
        "operator_boxplot": operator_boxplot,
        "variance_histogram": variance_chart
    }