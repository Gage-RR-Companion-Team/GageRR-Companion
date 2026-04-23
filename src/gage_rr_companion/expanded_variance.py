import numpy as np
import pandas as pd
from .expanded_spec import ExpandedStudySpec

def extract_random_variance_components(result, model_args):
    components = {}

    #residual variance
    components["Repeatability"] = float(result.scale)

    # main group variance, part
    if result.cov_re is not None and result.cov_re.size > 0:
        group_var = float(result.cov_re.iloc[0, 0])
        group_name = model_args["groups"]
        components[group_name] = max(group_var, 0)

    # variance components from vc_formula
    vc_names = list(model_args["vc_formula"].keys())
    for name, value in zip(vc_names, result.vcomp):
        components[name] = max(float(value), 0)

    return components

def compute_fixed_factor_variability(df, spec: ExpandedStudySpec):
    """
    V1 simplified fixed term variability
    variance of factor-level means.
    This is not full minitab parity, but is a useful first implementation
    """

    fixed_components = {}

    for factor in spec.factors.values():
        if factor.kind == "fixed" and factor.role != "ignore":
            means = df.groupby(factor.name)[spec.value_col].mean()
            if len(means) > 1:
                fixed_components[factor.name] = float(means.var(ddof=1))
            else:
                fixed_components[factor.name] = 0.0
    
    return fixed_components

def build_expanded_variance_table(result, model_args, df, spec: ExpandedStudySpec):
    raw = extract_random_variance_components(result, model_args)
    raw.update(compute_fixed_factor_variability(df, spec))

    repeatability = raw.get("Repeatability", 0.0)

    part_to_part = 0.0
    reproducibility = 0.0

    rows = []

    for name, var in raw.items():
        if name == "Repeatability":
            role = "repeatability"
        elif name in spec.part_to_part_terms or name == spec.part_col:
            role = "part_to_part"
            part_to_part += var
        else:
            #default anything not repeatability or part to part is reproducibility
            role = "reproducibility"
            reproducibility += var

        rows.append({
            "Source": name,
            "VarianceComponent": var,
            "Role": role,
        })

    total_gage_rr = repeatability + reproducibility
    total_variation = total_gage_rr + part_to_part

    summary_rows = [
        {"Source": "Reproducibility", "VarianceComponent": reproducibility, "Role": "summary"},
        {"Source": "Part-to-Part", "VarianceComponent": part_to_part, "Role": "summary"},
        {"Source": "Total Gage R&R", "VarianceComponent": total_gage_rr, "Role": "summary"},
        {"Source": "Total Variation", "VarianceComponent": total_variation, "Role": "summary"},
    ]

    out = pd.DataFrame(rows + summary_rows)

    if total_variation > 0:
        out["PercentContribution"] = out["VarianceComponent"] / total_variation * 100
    else:
        out["PercentContribution"] = np.nan
    
    return out