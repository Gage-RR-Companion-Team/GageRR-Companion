import pandas as pd
import numpy as np

from .anova import ComputeANOVA
from .variance import ComputeVarianceComponents
from .tables import GenerateGageRRTable
from .stats import ComputeOperatorStats


def ComputeGageRR(
    df,
    operator_col="Operator",
    part_col="Part",
    trial_col="Trial",
    value_col="Value"
):
    """
    Perform a full crossed Gage R&R analysis on measurement data.

    This function orchestrates the complete Gage R&R analysis workflow by
    calling the ANOVA, variance component, Gage R&R table, and operator
    statistics components. It assembles all results into a structured
    dictionary consistent with standard statistical software such as Minitab.

    The input DataFrame is treated as read-only and is not modified.

    Parameters
    ----------
    df : pandas.DataFrame
        Validated measurement dataset in long format containing columns
        identifying operator, part, trial, and measurement value.

    operator_col : str, default="Operator"
        Column identifying measurement operator.

    part_col : str, default="Part"
        Column identifying measured part.

    trial_col : str, default="Trial"
        Column identifying trial number.

    value_col : str, default="Value"
        Column containing numeric measurement values.

    Returns
    -------
    dict
        Dictionary containing the following keys:

        anova_table : pandas.DataFrame
            ANOVA table used to estimate variance components.

        variance_components : pandas.DataFrame
            Variance component estimates and percent contribution.

        gage_rr_table : pandas.DataFrame
            Full Gage R&R summary table including study variation.

        operator_stats : pandas.DataFrame
            Per-operator diagnostic statistics.

        summary_metrics : dict
            Key Gage R&R performance metrics including:
                • Percent Gage R&R
                • Percent Repeatability
                • Percent Reproducibility
                • Percent Part-to-Part

        metadata : dict
            Study metadata including number of operators, parts, trials,
            and total measurements.

        warnings : list of str
            List of warnings generated during analysis.

    Raises
    ------
    ValueError
        If required columns are missing or DataFrame is empty.

    TypeError
        If Trial or Value columns have invalid types.

    RuntimeError
        If computation fails unexpectedly.

    Notes
    -----
    This function assumes a crossed Gage R&R design.

    Variance components and study variation calculations follow the same
    methodology used by Minitab and AIAG MSA standards.
    """

    warnings = []

    # Validate basic structure
    required_cols = [operator_col, part_col, trial_col, value_col]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' is missing.")

    if len(df) == 0:
        raise ValueError("Input DataFrame is empty.")

    if not pd.api.types.is_integer_dtype(df[trial_col]):
        raise TypeError(f"Column '{trial_col}' must be integer.")

    if not pd.api.types.is_numeric_dtype(df[value_col]):
        raise TypeError(f"Column '{value_col}' must be numeric.")

    # Metadata
    n_operators = df[operator_col].nunique()
    n_parts = df[part_col].nunique()

    trials_per_cell = (
        df.groupby([operator_col, part_col])[trial_col]
        .nunique()
    )

    if trials_per_cell.nunique() != 1:
        warnings.append(
            "Unbalanced design detected. Variance component estimates may be unreliable."
        )

    n_trials = int(trials_per_cell.mean())

    metadata = {

        "n_operators": n_operators,
        "n_parts": n_parts,
        "n_trials": n_trials,
        "n_measurements": len(df),

        "operator_column": operator_col,
        "part_column": part_col,
        "trial_column": trial_col,
        "value_column": value_col
    }

    # Run analysis components
    anova_table = ComputeANOVA(
        df,
        operator_col,
        part_col,
        trial_col,
        value_col
    )

    variance_components = ComputeVarianceComponents(
        anova_table,
        n_parts,
        n_operators,
        n_trials
    )

    gage_rr_table = GenerateGageRRTable(
        variance_components
    )

    operator_stats = ComputeOperatorStats(
        df,
        operator_col,
        value_col
    )

    # Summary metrics
    total_var = variance_components.loc[
        variance_components["Source"] == "Total Variation",
        "VarianceComponent"
    ].values[0]

    gage_rr_var = variance_components.loc[
        variance_components["Source"] == "Total Gage R&R",
        "VarianceComponent"
    ].values[0]

    repeat_var = variance_components.loc[
        variance_components["Source"] == "Repeatability",
        "VarianceComponent"
    ].values[0]

    repro_var = variance_components.loc[
        variance_components["Source"] == "Reproducibility",
        "VarianceComponent"
    ].values[0]

    part_var = variance_components.loc[
        variance_components["Source"] == "Part-To-Part",
        "VarianceComponent"
    ].values[0]

    summary_metrics = {

        "PercentGageRR": gage_rr_var / total_var * 100,

        "PercentRepeatability": repeat_var / total_var * 100,

        "PercentReproducibility": repro_var / total_var * 100,

        "PercentPartToPart": part_var / total_var * 100
    }

    # Assemble results
    results = {

        "anova_table": anova_table,

        "variance_components": variance_components,

        "gage_rr_table": gage_rr_table,

        "operator_stats": operator_stats,

        "summary_metrics": summary_metrics,

        "metadata": metadata,

        "warnings": warnings
    }

    return results
