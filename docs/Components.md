1) make a data input window with three columns (one to distinguish the operator, one to distinguish the part number and one for the values from the measurement.) This should be able to be edited, with unlimited rows but only around 15 shown at a time, while the rest must be scrolled to. Add the ablilty to add columns for additional measurements to allow comparisons betweeen measurement methods. 
1.5) read a csv into a Pandas dataframe, make sure that all columns are labeled, there should be one column to specify the operator (this data can either be a number or a name to specify the operator) and one column to specify the part number (this will be an integer) and at least one column for the measurement values(this will be some number value, may be floating point). There should be mutiple measurement values for each operator-part combo, If there are mutiple methods being compared then therse should be additional measurement value columns (one for each measeurment method). If there is not one column for the operator or part number or value return an error stating that data is not in the correct structure
2) output window (shows total varience, operator varience and tool varience)
3) data visualization output (needs area on screen and code) (way to edit and change)
4) dropdown to pick which type of gage we're doing
5) documentation (user manual)
6) AI helper ???
7) authentification for data entry errors
8) export graphs and numbers, maybe use LLM for comentary
9) way to store data so they can come back to it
10) import/export data as a csv/df 
11) BIGGEST ONE NEED A FUNCTION TO ACTUALLY DO THE WORK OF THE MATH, gonna add a disciption below got chat to help me with it. next need to add in components that this calls ie (Compute ANOVA, ComputeVarience, ComputeGAGEtable, Compute operator stats)
# Component Specification: `ComputeGageRR`

## Description  
`ComputeGageRR` performs a crossed Gage R&R analysis on a validated pandas DataFrame. It calculates ANOVA, variance components, Gage R&R tables, summary metrics, and operator statistics using the same formulas and structure as Minitab.  

It treats the input DataFrame as read-only and includes warnings for unbalanced designs while computing the best possible results.

---

## Inputs  

| Name | Type | Description | Required | Constraints |
|------|------|-------------|----------|-------------|
| `df` | `pandas.DataFrame` | Validated measurement data with columns `"Operator"`, `"Part"`, `"Trial"`, and `"Value"` | Yes | Must contain no missing values, all `"Trial"` values integers, `"Value"` numeric. Must be balanced (warning if not). |

### Input Validation Rules
- Columns `"Operator"`, `"Part"`, `"Trial"`, `"Value"` must exist.  
- `"Trial"` must contain integer values; `"Value"` must be numeric.  
- DataFrame must be non-empty; otherwise raise `ValueError`.  
- If design is unbalanced, issue a warning in the results dictionary.

---

## Outputs  

| Name | Type | Description |
|------|------|-------------|
| `anova_table` | `pandas.DataFrame` | ANOVA table used to calculate variance components. |
| `variance_components` | `pandas.DataFrame` | Part, operator, interaction, repeatability, and total variance components. |
| `gage_rr_table` | `pandas.DataFrame` | Full Gage R&R table (repeatability, reproducibility, %Contribution, etc.) matching Minitab output. |
| `summary_metrics` | `dict` | Key metrics including %Gage R&R, %Part, %Operator, %Repeatability. |
| `operator_stats` | `pandas.DataFrame` | Count, mean, standard deviation, range, and coefficient of variation per operator. |
| `metadata` | `dict` | Number of operators, parts, trials, total measurements, and column names. |
| `warnings` | `list[str]` | List of warnings generated during computation (e.g., unbalanced design). |

---

## Side Effects  

- Does **not** modify the input DataFrame.  
- May populate `"warnings"` list in the returned dictionary.  
- Uses lower-level components for ANOVA, variance components, and table calculations.  

---

## Errors  

| Error Type | Condition |
|-----------|------------|
| `ValueError` | DataFrame missing required columns or empty. |
| `TypeError` | `"Trial"` not integer or `"Value"` not numeric. |
| `RuntimeError` | Unexpected failure during calculations. |

---

## Dependencies on Other Components  

### `ComputeANOVA`
**Purpose:** Calculate ANOVA table from the measurement DataFrame.  
**How it is used:** Called internally to generate variance estimates.  
**Input provided:** Validated DataFrame.  
**Output used:** Used to calculate variance components.

### `ComputeVarianceComponents`
**Purpose:** Calculate variance components from ANOVA results.  
**How it is used:** Called internally after ANOVA.  
**Input provided:** ANOVA table.  
**Output used:** Populates `variance_components` in results dictionary.

### `GenerateGageRRTable`
**Purpose:** Format variance components into standard Gage R&R table structure.  
**How it is used:** Called internally after variance components.  
**Input provided:** Variance components DataFrame.  
**Output used:** Populates `gage_rr_table` in results dictionary.

### `ComputeOperatorStats`
**Purpose:** Calculate per-operator metrics (mean, std, range, CV, count).  
**How it is used:** Called internally on original DataFrame.  
**Input provided:** Original measurement DataFrame.  
**Output used:** Populates `operator_stats` in results dictionary.

---

## Internal State  

- Stateless; no internal state persists between calls.  

---

## Execution Behavior  

1. Validate input DataFrame and column types.  
2. Check for balanced design; if unbalanced, append warning.  
3. Call `ComputeANOVA` to generate ANOVA table.  
4. Call `ComputeVarianceComponents` to calculate variance components.  
5. Call `GenerateGageRRTable` to produce standard Gage R&R table.  
6. Call `ComputeOperatorStats` to calculate operator diagnostic metrics.  
7. Assemble `summary_metrics`, `metadata`, and `warnings` into a single dictionary.  
8. Return results dictionary.
