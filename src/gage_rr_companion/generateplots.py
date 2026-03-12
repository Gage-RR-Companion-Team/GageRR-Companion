"""
Component: GenerateGageRRPlots

Generates the standard visualization suite for a crossed Gage R&R study
using results produced by ComputeGageRR.

The component produces Altair charts and returns them in a dictionary.
It does NOT recompute any statistical results and treats the input
DataFrame as read-only.
"""

import pandas as pd
import altair as alt


def GenerateGageRRPlots(
    df,
    gage_rr_results,
    operator_col="Operator",
    part_col="Part",
    trial_col="Trial",
    value_col="Value"
):
    """
    Generate standard Gage R&R visualization charts.

    Parameters
    ----------
    df : pandas.DataFrame
        Measurement dataset used in the Gage R&R study.

    gage_rr_results : dict
        Results dictionary returned from ComputeGageRR.

    operator_col : str
        Operator column name.

    part_col : str
        Part column name.

    trial_col : str
        Trial column name.

    value_col : str
        Measurement value column name.

    Returns
    -------
    dict
        Dictionary containing Altair charts:
        {
            "xbar_control_chart": alt.Chart,
            "r_control_chart": alt.Chart,
            "operator_boxplot": alt.Chart,
            "variance_histogram": alt.Chart
        }
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

    # -----------------------------
    # X-Bar Chart (mean per Operator-Part)
    # -----------------------------

    xbar_df = (
        df.groupby([operator_col, part_col])[value_col]
        .mean()
        .reset_index(name="Xbar")
    )

    xbar_chart = (
        alt.Chart(xbar_df)
        .mark_line(point=True)
        .encode(
            x=alt.X(f"{part_col}:O", title="Part"),
            y=alt.Y("Xbar:Q", title="Mean Measurement"),
            color=alt.Color(f"{operator_col}:N", title="Operator"),
        )
        .properties(title="X-Bar Control Chart")
    )

    # -----------------------------
    # R Chart (range per Operator-Part)
    # -----------------------------

    r_df = (
        df.groupby([operator_col, part_col])[value_col]
        .agg(lambda x: x.max() - x.min())
        .reset_index(name="Range")
    )

    # Create subgroup index for plotting
    r_df["Subgroup"] = range(1, len(r_df) + 1)

    r_chart = (
        alt.Chart(r_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("Subgroup:O", title="Subgroup"),
            y=alt.Y("Range:Q", title="Range"),
        )
        .properties(title="R Control Chart")
    )

    # -----------------------------
    # Operator Box Plot
    # -----------------------------

    operator_boxplot = (
        alt.Chart(df)
        .mark_boxplot()
        .encode(
            x=alt.X(f"{operator_col}:N", title="Operator"),
            y=alt.Y(f"{value_col}:Q", title="Measurement Value"),
        )
        .properties(title="Operator Measurement Distribution")
    )

    # -----------------------------
    # Variance Contribution Histogram
    # -----------------------------

    # Use only rows with PercentContribution
    if "PercentContribution" not in variance_components.columns:
        raise ValueError("variance_components must contain 'PercentContribution' column.")

    var_df = variance_components.copy()

    variance_chart = (
        alt.Chart(var_df)
        .mark_bar()
        .encode(
            x=alt.X("Source:N", title="Variance Source"),
            y=alt.Y("PercentContribution:Q", title="Percent Contribution"),
        )
        .properties(title="Variance Contribution")
    )

    # -----------------------------
    # Return charts
    # -----------------------------

    return {
        "xbar_control_chart": xbar_chart,
        "r_control_chart": r_chart,
        "operator_boxplot": operator_boxplot,
        "variance_histogram": variance_chart,
    }