import pandas as pd
import numpy as np


def ComputeVarianceComponents_Nested(
    anova_table,
    n_parts,
    n_operators,
    n_trials
):
    """
    Compute variance components for a nested Gage R&R study from ANOVA results.

    In a nested design, parts are nested within operators so there is no
    interaction term. Variance components are estimated from the mean squares
    of the nested ANOVA table following standard expected mean square
    relationships used in Minitab and JMP.

    Variance components estimated:
        • Repeatability (Equipment Variation)
        • Operator (Appraiser Variation)
        • Part(Operator) (Part-to-Part within Operator)
        • Reproducibility (Operator only — no interaction term)
        • Total Gage R&R (Repeatability + Reproducibility)
        • Part-To-Part
        • Total Variation

    Parameters
    ----------
    anova_table : pandas.DataFrame
        ANOVA table produced by ComputeANOVA_Nested. Must contain rows
        labeled "Operator", "Part(Operator)", and "Repeatability", and a
        column named "MS" containing mean square values.

    n_parts : int
        Number of parts per operator.

    n_operators : int
        Number of unique operators in the study.

    n_trials : int
        Number of replicate measurements per part.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing variance components with columns:

        Source : str
            Source of variation.

        VarianceComponent : float
            Estimated variance component for each source.

        PercentContribution : float
            Percentage contribution of each source relative to total variance.

    Notes
    -----
    Variance components are computed using standard nested Gage R&R formulas:

        σ²_repeatability = MS_repeatability

        σ²_part =
            max((MS_part(operator) - MS_repeatability) / n_trials, 0)

        σ²_operator =
            max((MS_operator - MS_part(operator)) / (n_parts * n_trials), 0)

    Derived components:

        σ²_reproducibility = σ²_operator

        σ²_gage_rr = σ²_repeatability + σ²_reproducibility

        σ²_total = σ²_gage_rr + σ²_part

    Negative variance estimates are set to zero, consistent with standard
    statistical practice and Minitab implementation.

    Raises
    ------
    ValueError
        If required sources or mean square values are missing.

    RuntimeError
        If computation fails due to invalid inputs.
    """

    # Extract mean squares
    try:
        MS_operator = anova_table.loc[
            anova_table["Source"] == "Operator", "MS"
        ].values[0]

        MS_part = anova_table.loc[
            anova_table["Source"] == "Part(Operator)", "MS"
        ].values[0]

        MS_repeatability = anova_table.loc[
            anova_table["Source"] == "Repeatability", "MS"
        ].values[0]

    except Exception:
        raise ValueError(
            "ANOVA table missing required sources or MS values."
        )

    # Variance component calculations (nested Minitab formulas)

    var_repeatability = MS_repeatability

    var_part = max(
        (MS_part - MS_repeatability) / n_trials,
        0
    )

    var_operator = max(
        (MS_operator - MS_part) / (n_parts * n_trials),
        0
    )

    # No interaction term in nested design
    var_reproducibility = var_operator

    var_gage_rr = var_repeatability + var_reproducibility

    var_total = var_gage_rr + var_part

    # Assemble results
    results = pd.DataFrame({

        "Source": [
            "Repeatability",
            "Operator",
            "Part(Operator)",
            "Reproducibility",
            "Total Gage R&R",
            "Part-To-Part",
            "Total Variation"
        ],

        "VarianceComponent": [
            var_repeatability,
            var_operator,
            var_part,
            var_reproducibility,
            var_gage_rr,
            var_part,
            var_total
        ]
    })

    # Percent contribution
    results["PercentContribution"] = (
        results["VarianceComponent"] / var_total * 100
    )

    return results
