import statsmodels.api as sm
from .expanded_spec import ExpandedStudySpec

def c(name: str) -> str:
    return f"C({name})"

def build_mixedlm_args(spec: ExpandedStudySpec):
    fixed_terms = []

    for factor in spec.factors.values():
        if factor.kind == "fixed":
            fixed_terms.append(c(factor.name))
    
    fixed_rhs = " + ".join(fixed_terms) if fixed_terms else "1"
    formula = f"{spec.value_col} ~ {fixed_rhs}"

    # V1: use part as primary grouping variable

    groups = spec.part_col

    vc_formula = {}

    for factor in spec.factors.values():
        if factor.kind == "random" and factor.name != groups:
            vc_formula[factor.name] = f"0 + {c(factor.name)}"
    
    # V1: nested is handles as if child is nested in parent, create a combined categorical nesting ID upstream later

    for child, parent in spec.nesting:
        nested_name = f"{child}_nest_in_{parent}"
        vc_formula[nested_name] = f"0 + C({nested_name})"

    return {
        "formula": formula,
        "groups": groups,
        "re_formula": "1",
        "vc_formula": vc_formula,
    }

def prepare_nested_columns(df, spec: ExpandedStudySpec):
    data = df.copy()

    for child, parent in spec.nesting:
        nested_name = f"{child}_nested_in_{parent}"
        data[nested_name] = (
            data[parent].astype(str) + "::" + data[child].astype(str)
        ).astype("category")
    
    return data

def fit_expanded_model(df, spec: ExpandedStudySpec):
    data = prepare_nested_columns(df, spec)
    args = build_mixedlm_args(spec)

    model = sm.MixedLM.from_formula(
        args["formula"],
        groups=args["groups"],
        re_formula=args["re_formula"],
        vc_formula=args["vc_formula"],
        data=data,
    )

    result = model.fit(reml=True)

    return result, args, data