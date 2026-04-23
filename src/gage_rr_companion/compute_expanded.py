# compute_expanded.py

import pandas as pd

from .expanded_spec import (
    ExpandedStudySpec,
    validate_expanded_spec,
    infer_model_type,
    build_selected_terms,
)
from .expanded_model import fit_expanded_model
from .expanded_variance import build_expanded_variance_table

from .tables import GenerateGageRRTable
from .stats import ComputeOperatorStats


def ComputeExpandedGageRR(
    df: pd.DataFrame,
    spec: ExpandedStudySpec,
):
    warnings = []

    warnings.extend(validate_expanded_spec(df, spec))

    model_type = infer_model_type(spec)
    selected_terms = build_selected_terms(spec)

    result, model_args, model_data = fit_expanded_model(df, spec)

    variance_components = build_expanded_variance_table(
        result=result,
        model_args=model_args,
        df=model_data,
        spec=spec,
    )

    gage_rr_table = GenerateGageRRTable(variance_components)

    operator_stats = ComputeOperatorStats(
        model_data,
        operator_col=spec.operator_col,
        value_col=spec.value_col,
    )

    def get_var(source):
        values = variance_components.loc[
            variance_components["Source"] == source,
            "VarianceComponent"
        ].values
        return float(values[0]) if len(values) else 0.0

    total_var = get_var("Total Variation")
    gage_rr_var = get_var("Total Gage R&R")
    repeat_var = get_var("Repeatability")
    repro_var = get_var("Reproducibility")
    part_var = get_var("Part-To-Part")

    summary_metrics = {
        "PercentGageRR": gage_rr_var / total_var * 100 if total_var else None,
        "PercentRepeatability": repeat_var / total_var * 100 if total_var else None,
        "PercentReproducibility": repro_var / total_var * 100 if total_var else None,
        "PercentPartToPart": part_var / total_var * 100 if total_var else None,
    }

    metadata = {
        "model_type": model_type,
        "model_formula": model_args["formula"],
        "groups": model_args["groups"],
        "re_formula": model_args["re_formula"],
        "vc_formula": model_args["vc_formula"],
        "selected_terms": selected_terms,
        "n_measurements": len(model_data),
        "n_parts": model_data[spec.part_col].nunique(),
        "n_operators": model_data[spec.operator_col].nunique(),
    }

    return {
        "model_result": result,
        "model_summary": result.summary().as_text(),
        "variance_components": variance_components,
        "gage_rr_table": gage_rr_table,
        "operator_stats": operator_stats,
        "summary_metrics": summary_metrics,
        "metadata": metadata,
        "warnings": warnings,
    }