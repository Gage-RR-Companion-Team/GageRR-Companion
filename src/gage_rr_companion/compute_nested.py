# compute_nested.py

import pandas as pd

from .anova_nested import ComputeANOVA_Nested
from .variance_nested import ComputeVarianceComponents_Nested
from .tables import GenerateGageRRTable
from .stats import ComputeOperatorStats


def ComputeGageRR_Nested(
    df,
    operator_col="Operator",
    part_col="Part",
    trial_col="Trial",
    value_col="Value",
):
    warnings = []

    required_cols = [operator_col, part_col, trial_col, value_col]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' is missing.")

    if len(df) == 0:
        raise ValueError("Input DataFrame is empty.")

    n_operators = df[operator_col].nunique()

    parts_per_operator = (
        df.groupby(operator_col, observed=True)[part_col]
        .nunique()
    )

    if parts_per_operator.nunique() != 1:
        warnings.append(
            "Unbalanced nested design detected. Results may be less reliable."
        )

    n_parts = int(parts_per_operator.mean())

    trials_per_part = (
        df.groupby([operator_col, part_col], observed=True)[trial_col]
        .nunique()
    )

    if trials_per_part.nunique() != 1:
        warnings.append(
            "Unequal trial counts detected. Results may be less reliable."
        )

    n_trials = int(trials_per_part.mean())

    metadata = {
        "n_operators": n_operators,
        "n_parts_per_operator": n_parts,
        "n_trials": n_trials,
        "n_measurements": len(df),
        "operator_column": operator_col,
        "part_column": part_col,
        "trial_column": trial_col,
        "value_column": value_col,
        "study_type": "nested",
    }

    anova_table = ComputeANOVA_Nested(
        df,
        operator_col=operator_col,
        part_col=part_col,
        trial_col=trial_col,
        value_col=value_col,
    )

    variance_components = ComputeVarianceComponents_Nested(
        anova_table,
        n_parts=n_parts,
        n_operators=n_operators,
        n_trials=n_trials,
    )

    gage_rr_table = GenerateGageRRTable(variance_components)

    operator_stats = ComputeOperatorStats(
        df,
        operator_col=operator_col,
        value_col=value_col,
    )

    total_var = variance_components.loc[
        variance_components["Source"] == "Total Variation",
        "VarianceComponent",
    ].values[0]

    def pct(source):
        value = variance_components.loc[
            variance_components["Source"] == source,
            "VarianceComponent",
        ].values[0]
        return value / total_var * 100 if total_var else None

    summary_metrics = {
        "PercentGageRR": pct("Total Gage R&R"),
        "PercentRepeatability": pct("Repeatability"),
        "PercentReproducibility": pct("Reproducibility"),
        "PercentPartToPart": pct("Part-To-Part"),
    }

    return {
        "anova_table": anova_table,
        "variance_components": variance_components,
        "gage_rr_table": gage_rr_table,
        "operator_stats": operator_stats,
        "summary_metrics": summary_metrics,
        "metadata": metadata,
        "warnings": warnings,
    }