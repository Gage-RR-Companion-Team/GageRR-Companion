# Component Specification: `GenerateGageRRPlots`

## Description  
`GenerateGageRRPlots` generates the standard visualization suite associated with a crossed Gage R&R study using the results produced by `ComputeGageRR`.

The component produces interactive statistical charts using **Altair** and returns them as chart objects. These plots replicate the typical Measurement System Analysis visualizations found in industrial statistical software such as Minitab.

This component **does not perform any statistical calculations**. It consumes the already-computed results from `ComputeGageRR` and visualizes them.

The input DataFrame is treated as **read-only**.

---

# Inputs

| Name | Type | Description | Required | Constraints |
|------|------|-------------|----------|-------------|
| `df` | `pandas.DataFrame` | Measurement dataset used for the Gage R&R study | Yes | Must contain `"Operator"`, `"Part"`, `"Trial"`, `"Value"` columns |
| `gage_rr_results` | `dict` | Output dictionary returned from `ComputeGageRR` | Yes | Must contain `"variance_components"` and `"metadata"` keys |

### Optional Column Parameters

| Name | Type | Default | Description |
|------|------|--------|-------------|
| `operator_col` | `str` | `"Operator"` | Column identifying operator |
| `part_col` | `str` | `"Part"` | Column identifying measured part |
| `trial_col` | `str` | `"Trial"` | Column identifying trial |
| `value_col` | `str` | `"Value"` | Column containing measurement value |

---

# Input Validation Rules

- `df` must be a non-empty `pandas.DataFrame`.
- `gage_rr_results` must be a dictionary.
- Required columns must exist in `df`:
  - `"Operator"`
  - `"Part"`
  - `"Trial"`
  - `"Value"`
- `gage_rr_results` must contain:
  - `"variance_components"`
  - `"metadata"`
- Input DataFrame must **not be modified** during execution.

---

# Outputs

| Name | Type | Description |
|------|------|-------------|
| `xbar_control_chart` | `altair.Chart` | X-bar chart showing average measurement per operator and part |
| `r_control_chart` | `altair.Chart` | Range chart showing repeatability across operator–part subgroups |
| `operator_boxplot` | `altair.Chart` | Box-and-whisker plot comparing measurement distributions per operator |
| `variance_histogram` | `altair.Chart` | Bar chart showing percent contribution of variance sources |

All charts are returned in a dictionary:

```python
{
    "xbar_control_chart": alt.Chart,
    "r_control_chart": alt.Chart,
    "operator_boxplot": alt.Chart,
    "variance_histogram": alt.Chart
}