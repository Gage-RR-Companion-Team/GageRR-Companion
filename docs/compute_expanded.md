Name:

compute_expanded.py

Dependencies:
 * pandas
 * numpy
 * statsmodels
 * scipy

utilization of statsmodels for the support of fixed effects, group-based random effects, and additional variance components. Estimates variance parameters

# What it does
Performs expanded Gage R&R analysis by:
 * Validating a study specification
 * Constructing the appropriate mixed/random/nested model
 * Fitting the model
 * Extracting or constructing variance components
 * Rolling them into Gage R&R categories
 * Return tables and metadata

# Inputs

data: pd.DataFrame
value_col: str
part_col: str
operator_col: str
factor_specs: dict
nesting_specs: list[tuple[str, str]] | None
interaction_order: int = 2
selected_terms: list[str] | None
part_to_part_terms: list[str] | None
study_var_multiplier: float = 6.0
tolerance: float | None = None
lsl: float | None = None
usl: float | None = None
historical_sigma: float | None = None
alpha_remove_interaction: float | None = None
metadata: dict | None = None

# Shape of factor specifications dictionary
## This does not mean that it is exactly these, but it will take on the shape of this type of dictionary

factor_specs = {
    "Part": {
        "kind": "random",
        "role": "part_to_part"
    },
    "Operator": {
        "kind": "random",
        "role": "reproducibility"
    },
    "Station": {
        "kind": "fixed",
        "role": "reproducibility"
    }

}

# Outputs

factor_info: pd.DataFrame
model_type: str
model_formula: str
fit_summary_text: str
anova_table: pd.DataFrame | None
variance_components: pd.DataFrame
gage_rr_table: pd.DataFrame
term_mapping: pd.DataFrame
summary_metrics: dict
plot_data: dict
metadata: dict
warnings: list[str]

# How it uses other components
 * Receives validated GUI selections and raw data upstream
 * Feeds tables to existing Streamlit display layer
 * Feeds plot-ready DataFrames to Altair plotting