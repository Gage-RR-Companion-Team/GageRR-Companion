import pandas as pd
import numpy as np


def ComputeANOVA_Nested(
    df,
    operator_col="Operator",
    part_col="Part",
    trial_col="Trial",
    value_col="Value"
):
    """
    Compute the nested Gage R&R ANOVA table from measurement data.

    In a nested design, each part is measured by only one operator — parts
    are nested within operators. This is common in destructive testing where
    the same physical part cannot be measured twice. There is no
    Part x Operator interaction term because each operator measures a
    different set of parts.

    Parameters
    ----------
    df : pandas.DataFrame
        Measurement dataset in long format. Must contain columns specifying
        operator, part, trial, and measured value. The input DataFrame is
        treated as read-only and is not modified.

    operator_col : str, default="Operator"
        Column name identifying the operator performing the measurement.

    part_col : str, default="Part"
        Column name identifying the part being measured. Parts are assumed
        to be nested within operators.

    trial_col : str, default="Trial"
        Column name identifying the replicate measurement number.

    value_col : str, default="Value"
        Column name containing the numeric measurement values.

    Returns
    -------
    pandas.DataFrame
        ANOVA table containing the following columns:

        Source : str
            Variance source ("Operator", "Part(Operator)",
            "Repeatability", "Total")

        DF : int
            Degrees of freedom associated with each source.

        SS : float
            Sum of squares for each source.

        MS : float
            Mean square for each source. The Total row contains NaN.

    Notes
    -----
    Variance sources included:
        • Operator
        • Part(Operator) — parts nested within operators
        • Repeatability (within-cell error)
        • Total

    There is no interaction term in a nested design.

    Degrees of freedom:
        DF_operator     = a - 1
        DF_part         = a * (p - 1)
        DF_repeatability = a * p * (r - 1)
        DF_total        = N - 1

    Where:
        a = number of operators
        p = number of parts per operator
        r = number of trials per part

    Raises
    ------
    ValueError
        If required columns are missing or the DataFrame is empty.

    RuntimeError
        If numerical computation fails unexpectedly.
    """

    # Copy to ensure read-only behavior
    data = df[[operator_col, part_col, trial_col, value_col]].copy()

    # Counts
    operators = data[operator_col].unique()
    a = len(operators)

    # Parts per operator (assume balanced)
    p = int(
        data.groupby(operator_col)[part_col]
        .nunique()
        .mean()
    )

    # Trials per part
    r = int(
        data.groupby([operator_col, part_col])[trial_col]
        .nunique()
        .mean()
    )

    N = len(data)

    # Grand mean
    grand_mean = data[value_col].mean()

    # Operator means
    operator_means = data.groupby(operator_col)[value_col].mean()

    # Part means (nested within operator)
    part_means = data.groupby([operator_col, part_col])[value_col].mean()

    # Total SS
    SS_total = ((data[value_col] - grand_mean) ** 2).sum()

    # Operator SS
    SS_operator = r * p * ((operator_means - grand_mean) ** 2).sum()

    # Part(Operator) SS
    SS_part = 0
    for op in operators:
        op_mean = operator_means.loc[op]
        op_part_means = part_means.loc[op]
        SS_part += r * ((op_part_means - op_mean) ** 2).sum()

    # Repeatability SS
    SS_repeatability = SS_total - SS_operator - SS_part

    # Degrees of freedom
    DF_operator = a - 1
    DF_part = a * (p - 1)
    DF_repeatability = a * p * (r - 1)
    DF_total = N - 1

    # Mean squares
    MS_operator = SS_operator / DF_operator
    MS_part = SS_part / DF_part
    MS_repeatability = SS_repeatability / DF_repeatability

    # Build table
    anova_table = pd.DataFrame({

        "Source": [
            "Operator",
            "Part(Operator)",
            "Repeatability",
            "Total"
        ],

        "DF": [
            DF_operator,
            DF_part,
            DF_repeatability,
            DF_total
        ],

        "SS": [
            SS_operator,
            SS_part,
            SS_repeatability,
            SS_total
        ],

        "MS": [
            MS_operator,
            MS_part,
            MS_repeatability,
            np.nan
        ]
    })

    return anova_table
