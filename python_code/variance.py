import pandas as pd
import numpy as np


def ComputeVarianceComponents(
    anova_table,
    n_parts,
    n_operators,
    n_trials
):
    """
    Compute variance components for a crossed Gage R&R study from ANOVA results.

    This function calculates the variance components associated with each
    source of variation in a crossed Gage R&R design using the mean squares
    obtained from the ANOVA table. The calculations follow the standard
    expected mean square relationships used in statistical software such
    as Minitab and JMP.

    Variance components estimated:
        • Repeatability (Equipment Variation)
        • Operator (Appraiser Variation)
        • Part × Operator Interaction
        • Reproducibility (Operator + Interaction)
        • Total Gage R&R (Repeatability + Reproducibility)
        • Part-to-Part Variation
        • Total Variation

    Parameters
    ----------
    anova_table : pandas.DataFrame
        ANOVA table produced by ComputeANOVA. Must contain rows labeled:
        "Part", "Operator", "Part*Operator", and "Repeatability", and a
        column named "MS" containing mean square values.

    n_parts : int
        Number of unique parts in the study.

    n_operators : int
        Number of unique operators in the study.

    n_trials : int
        Number of replicate measurements per operator–part combination.

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
    Variance components are computed using standard crossed Gage R&R formulas:

        σ²_repeatability = MS_repeatability

        σ²_interaction =
            max((MS_interaction − MS_repeatability) / n_trials, 0)

        σ²_operator =
            max((MS_operator − MS_interaction) / (n_parts * n_trials), 0)

        σ²_part =
            max((MS_part − MS_interaction) / (n_operators * n_trials), 0)

    Derived components:

        σ²_reproducibility =
            σ²_operator + σ²_interaction

        σ²_gage_rr =
            σ²_repeatability + σ²_reproducibility

        σ²_total =
            σ²_gage_rr + σ²_part

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
        MS_part = anova_table.loc[
            anova_table["Source"] == "Part", "MS"
        ].values[0]

        MS_operator = anova_table.loc[
            anova_table["Source"] == "Operator", "MS"
        ].values[0]

        MS_interaction = anova_table.loc[
            anova_table["Source"] == "Part*Operator", "MS"
        ].values[0]

        MS_repeatability = anova_table.loc[
            anova_table["Source"] == "Repeatability", "MS"
        ].values[0]

    except Exception:
        raise ValueError(
            "ANOVA table missing required sources or MS values."
        )

    # Variance component calculations (Minitab formulas)

    var_repeatability = MS_repeatability

    var_interaction = max(
        (MS_interaction - MS_repeatability) / n_trials,
        0
    )

    var_operator = max(
        (MS_operator - MS_interaction) / (n_parts * n_trials),
        0
    )

    var_part = max(
        (MS_part - MS_interaction) / (n_operators * n_trials),
        0
    )

    var_reproducibility = var_operator + var_interaction

    var_gage_rr = var_repeatability + var_reproducibility

    var_total = var_gage_rr + var_part

    # Assemble results
    results = pd.DataFrame({

        "Source": [
            "Repeatability",
            "Operator",
            "Operator*Part Interaction",
            "Reproducibility",
            "Total Gage R&R",
            "Part-To-Part",
            "Total Variation"
        ],

        "VarianceComponent": [
            var_repeatability,
            var_operator,
            var_interaction,
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