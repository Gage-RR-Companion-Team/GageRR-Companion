import pandas as pd
import numpy as np


def GenerateGageRRTable(variance_components):
    """
    Generate the standard Gage R&R results table from variance components.

    This function transforms variance component estimates into the full
    Gage R&R summary table used in measurement system analysis. It computes
    standard deviations (study variation), percent study variation, and
    percent contribution for each source of variation.

    The resulting table matches the structure and calculations used by
    statistical software such as Minitab and JMP.

    Parameters
    ----------
    variance_components : pandas.DataFrame
        DataFrame produced by ComputeVarianceComponents containing columns:

        Source : str
            Source of variation.

        VarianceComponent : float
            Estimated variance component.

        PercentContribution : float
            Percent contribution to total variance.

    Returns
    -------
    pandas.DataFrame
        Gage R&R results table containing:

        Source : str
            Source of variation.

        VarianceComponent : float
            Variance component estimate.

        StdDev : float
            Standard deviation (square root of variance component).

        StudyVar : float
            Study variation, defined as 6 × standard deviation.

        PercentStudyVar : float
            Percent study variation relative to total study variation.

        PercentContribution : float
            Percent contribution to total variance.

    Notes
    -----
    Definitions:

        StdDev = sqrt(VarianceComponent)

        StudyVar = 6 × StdDev

        PercentStudyVar =
            (StudyVar / StudyVar_total) × 100

    The factor of 6 represents the full process spread (±3 standard deviations),
    which is the standard convention in Gage R&R analysis.

    Sources typically included:

        • Total Gage R&R
        • Repeatability
        • Reproducibility
        • Operator
        • Operator × Part Interaction
        • Part-To-Part
        • Total Variation

    Raises
    ------
    ValueError
        If required columns are missing.

    RuntimeError
        If numerical computation fails.
    """

    required_cols = [
        "Source",
        "VarianceComponent",
        "PercentContribution"
    ]

    for col in required_cols:
        if col not in variance_components.columns:
            raise ValueError(
                f"Missing required column '{col}' in variance components."
            )

    table = variance_components.copy()

    # Standard deviation
    table["StdDev"] = np.sqrt(table["VarianceComponent"])

    # Study variation (6 sigma)
    table["StudyVar"] = 6 * table["StdDev"]

    # Total study variation (last row assumed Total Variation)
    total_study_var = table.loc[
        table["Source"] == "Total Variation",
        "StudyVar"
    ].values[0]

    # Percent study variation
    table["PercentStudyVar"] = (
        table["StudyVar"] / total_study_var * 100
    )

    # Reorder columns to match Minitab style
    table = table[[
        "Source",
        "VarianceComponent",
        "PercentContribution",
        "StdDev",
        "StudyVar",
        "PercentStudyVar"
    ]]

    return table