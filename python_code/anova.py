import pandas as pd
import numpy as np


def ComputeANOVA(
    df,
    operator_col="Operator",
    part_col="Part",
    trial_col="Trial",
    value_col="Value"
):
    """
    Compute the crossed Gage R&R ANOVA table from measurement data.

    This function performs a two-factor crossed Analysis of Variance (ANOVA)
    with replication, using Part and Operator as fixed factors and Trial as
    the replication index. It calculates the sums of squares (SS), degrees of
    freedom (DF), and mean squares (MS) for each variance source required for
    Gage R&R variance component estimation.

    The ANOVA table produced by this function serves as the foundation for
    subsequent variance component calculations and Gage R&R metrics.

    Parameters
    ----------
    df : pandas.DataFrame
        Measurement dataset in long format. Must contain columns specifying
        operator, part, trial, and measured value. The input DataFrame is
        treated as read-only and is not modified.

    operator_col : str, default="Operator"
        Column name identifying the operator performing the measurement.

    part_col : str, default="Part"
        Column name identifying the part being measured.

    trial_col : str, default="Trial"
        Column name identifying the replicate measurement number.

    value_col : str, default="Value"
        Column name containing the numeric measurement values.

    Returns
    -------
    pandas.DataFrame
        ANOVA table containing the following columns:

        Source : str
            Variance source ("Part", "Operator", "Part*Operator",
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
        • Part
        • Operator
        • Part × Operator interaction
        • Repeatability (within-cell error)
        • Total

    This function assumes a crossed design. If the design is unbalanced,
    calculations will still be performed using observed replication counts,
    but variance component estimation may be less reliable.

    The resulting mean squares are used directly in variance component
    estimation according to standard crossed Gage R&R methodology as
    implemented in statistical software such as Minitab and JMP.

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
    parts = data[part_col].unique()

    a = len(operators)
    p = len(parts)

    r = (
        data.groupby([operator_col, part_col])[trial_col]
        .nunique()
        .mean()
    )

    N = len(data)

    # Means
    grand_mean = data[value_col].mean()

    part_means = data.groupby(part_col)[value_col].mean()
    operator_means = data.groupby(operator_col)[value_col].mean()

    cell_means = data.groupby(
        [part_col, operator_col]
    )[value_col].mean()

    # Total SS
    SS_total = ((data[value_col] - grand_mean) ** 2).sum()

    # Part SS
    SS_part = r * a * ((part_means - grand_mean) ** 2).sum()

    # Operator SS
    SS_operator = r * p * ((operator_means - grand_mean) ** 2).sum()

    # Interaction SS
    SS_interaction = 0

    for part in parts:
        for op in operators:

            cell_mean = cell_means.loc[(part, op)]
            part_mean = part_means.loc[part]
            op_mean = operator_means.loc[op]

            SS_interaction += (
                cell_mean
                - part_mean
                - op_mean
                + grand_mean
            ) ** 2

    SS_interaction *= r

    # Repeatability SS
    SS_repeatability = (
        SS_total
        - SS_part
        - SS_operator
        - SS_interaction
    )

    # Degrees of freedom
    DF_part = p - 1
    DF_operator = a - 1
    DF_interaction = (p - 1) * (a - 1)
    DF_repeatability = a * p * (r - 1)
    DF_total = N - 1

    # Mean squares
    MS_part = SS_part / DF_part
    MS_operator = SS_operator / DF_operator
    MS_interaction = SS_interaction / DF_interaction
    MS_repeatability = SS_repeatability / DF_repeatability

    # Build table
    anova_table = pd.DataFrame({

        "Source": [
            "Part",
            "Operator",
            "Part*Operator",
            "Repeatability",
            "Total"
        ],

        "DF": [
            DF_part,
            DF_operator,
            DF_interaction,
            DF_repeatability,
            DF_total
        ],

        "SS": [
            SS_part,
            SS_operator,
            SS_interaction,
            SS_repeatability,
            SS_total
        ],

        "MS": [
            MS_part,
            MS_operator,
            MS_interaction,
            MS_repeatability,
            np.nan
        ]
    })

    return anova_table