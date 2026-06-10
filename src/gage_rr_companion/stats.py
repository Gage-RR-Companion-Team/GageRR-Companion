import pandas as pd
import numpy as np


def ComputeOperatorStats(
    df,
    operator_col="Operator",
    value_col="Value"
):
    """
    Compute per-operator statistical diagnostics for a Gage R&R study.

    This function calculates descriptive statistics for each operator based
    on their measurement values. These statistics help evaluate operator
    consistency, bias, and variability, and are commonly included in Gage R&R
    diagnostic output.

    Statistics computed per operator:

        • Count (number of measurements)
        • Mean measurement value
        • Standard deviation
        • Minimum value
        • Maximum value
        • Range (max − min)
        • Coefficient of variation (CV %)

    Parameters
    ----------
    df : pandas.DataFrame
        Measurement dataset in long format. Must contain columns identifying
        operator and measurement value. The input DataFrame is treated as
        read-only and is not modified.

    operator_col : str, default="Operator"
        Column name identifying the operator performing the measurement.

    value_col : str, default="Value"
        Column name containing numeric measurement values.

    Returns
    -------
    pandas.DataFrame
        DataFrame indexed by operator containing the following columns:

        Count : int
            Number of measurements performed by the operator.

        Mean : float
            Mean measurement value.

        StdDev : float
            Standard deviation of measurements.

        Min : float
            Minimum measurement value.

        Max : float
            Maximum measurement value.

        Range : float
            Difference between maximum and minimum values.

        CV_Percent : float
            Coefficient of variation expressed as a percentage:
                CV = (StdDev / Mean) × 100

    Notes
    -----
    The coefficient of variation provides a normalized measure of operator
    variability relative to the magnitude of the measurements.

    Higher CV values indicate greater relative variability and potential
    operator inconsistency.

    This function does not modify the input DataFrame.

    Raises
    ------
    ValueError
        If required columns are missing or DataFrame is empty.

    RuntimeError
        If numerical computation fails.
    """

    # Validate inputs
    if operator_col not in df.columns:
        raise ValueError(f"Column '{operator_col}' not found.")

    if value_col not in df.columns:
        raise ValueError(f"Column '{value_col}' not found.")

    if len(df) == 0:
        raise ValueError("DataFrame is empty.")

    # Group by operator
    grouped = df.groupby(operator_col, observed=True)[value_col]

    stats = pd.DataFrame({

        "Count": grouped.count(),

        "Mean": grouped.mean(),

        "StdDev": grouped.std(ddof=1),

        "Min": grouped.min(),

        "Max": grouped.max()

    })

    # Range
    stats["Range"] = stats["Max"] - stats["Min"]

    # Coefficient of variation (%)
    stats["CV_Percent"] = (
        stats["StdDev"] / stats["Mean"] * 100
    )

    # Reset index to make Operator a column
    stats = stats.reset_index()

    return stats