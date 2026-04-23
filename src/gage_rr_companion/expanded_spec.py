from dataclasses import dataclass, field
from itertools import combinations
import pandas as pd

@dataclass
class FactorSpec:
    name: str
    kind: str # "fixed" or "random"
    role: str # "part_to_part", "reproducibility", or "ignore"

@dataclass
class ExpandedStudySpec:
    value_col: str
    part_col: str
    operator_col: str
    factors: dict[str, FactorSpec]
    nesting: list[tuple[str, str]] = field(default_factory=list)
    interaction_order: int = 2
    selected_terms: list[str] | None = None
    part_to_part_factors: list[str] = field(default_factory=lambda: ["Part"])

def validate_expanded_spec(df: pd.DataFrame, spec: ExpandedStudySpec):
    warnings = []

    required = [spec.value_col, spec.part_col, spec.operator_col]
    required += list(spec.factors.keys())

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    if not pd.api.types.is_numeric_dtype(df[spec.value_col]):
        raise ValueError(f"Value column '{spec.value_col}' must be numeric")
    
    for factor in spec.factors.values():
        if factor.kind not in {"fixed", "random"}:
            raise ValueError(f"{factor.name}: kind must be fixed or random")
        if factor.role not in {"part_to_part", "reproducibility", "ignore"}:
            raise ValueError(f"{factor.name}: role must be part_to_part, reproducibility, or ignore")
    
    if spec.interaction_order not in {1, 2}:
        raise ValueError("interaction_order must be 1 or 2")
    
    for child, parent in spec.nesting:
        if child not in spec.factors or parent not in spec.factors:
            raise ValueError(f"Invalid nesting declaration: {child} nested in {parent}")
    
    if df.duplicated().any():
        warnings.append("Duplicate full rows detected")
    
    return warnings

def infer_model_type(spec: ExpandedStudySpec) -> str:
    has_fixed = any(f.kind == "fixed" for f in spec.factors.values())
    has_nested = len(spec.nesting) > 0

    if has_nested:
        return "nested_mixed"
    
    if has_fixed:
        return "mixed"
    
    return "random"

def build_selected_terms(spec: ExpandedStudySpec) -> list[str]:
    factor_names = list(spec.factors.keys())

    if spec.selected_terms is not None:
        return spec.selected_terms
    
    terms = factor_names.copy()

    if spec.interaction_order >= 2:
        for a, b in combinations(factor_names, 2):
            terms.append(f"{a}:{b}")

    return terms

