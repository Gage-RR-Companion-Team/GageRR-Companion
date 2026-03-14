# Gage R&R Interpretation Component

## Overview

The **Gage R&R Interpretation Component** evaluates the results dictionary produced by the `ComputeGageRR` analysis pipeline and generates standardized measurement system diagnostics.

This component does **not perform calculations** or generate plots. Those operations are handled upstream by:

- ANOVA computation
- Variance component estimation
- Gage R&R summary table generation
- Operator statistics
- Plotting components

The purpose of this module is to **interpret the computed statistics** and produce:

- Acceptable / Marginal / Not Acceptable ratings
- Root cause analysis of measurement variation
- Measurement discrimination capability
- Automated recommendations

The interpretation rules follow common **Measurement System Analysis (MSA)** guidelines consistent with tools such as Minitab.

---

# Input Source

This component consumes the `results` dictionary produced by:

```
ComputeGageRR()
```

Example structure:

```python
results = {

    "anova_table": pandas.DataFrame,

    "variance_components": pandas.DataFrame,

    "gage_rr_table": pandas.DataFrame,

    "operator_stats": pandas.DataFrame,

    "summary_metrics": {

        "PercentGageRR": float,
        "PercentRepeatability": float,
        "PercentReproducibility": float,
        "PercentPartToPart": float
    },

    "metadata": {

        "n_operators": int,
        "n_parts": int,
        "n_trials": int,
        "n_measurements": int
    },

    "warnings": list[str]
}
```

---

# Metrics Used for Interpretation

The interpretation component primarily relies on values contained in:

```
results["summary_metrics"]
```

Example:

```python
metrics = results["summary_metrics"]

percent_gage_rr = metrics["PercentGageRR"]
percent_repeat = metrics["PercentRepeatability"]
percent_repro = metrics["PercentReproducibility"]
percent_part = metrics["PercentPartToPart"]
```

---

# Interpretation Rules

## 1. Total Gage R&R

Total Gage R&R indicates the proportion of total variation caused by the measurement system.

| Percent Gage R&R | Interpretation | Status |
|------------------|---------------|--------|
| < 10% | Excellent measurement system | Acceptable |
| 10–30% | Conditionally acceptable | Marginal |
| > 30% | Measurement system unacceptable | Not Acceptable |

Example logic:

```python
if percent_gage_rr < 10:
    gage_rr_status = "Acceptable"
elif percent_gage_rr <= 30:
    gage_rr_status = "Marginal"
else:
    gage_rr_status = "Not Acceptable"
```

---

## 2. Repeatability vs Reproducibility

This comparison identifies the dominant source of measurement variation.

| Condition | Interpretation |
|----------|---------------|
| Repeatability >> Reproducibility | Equipment variation dominates |
| Reproducibility >> Repeatability | Operator variation dominates |
| Similar magnitude | Balanced measurement variation |

Example logic:

```python
if percent_repeat > percent_repro * 1.5:
    root_cause = "Equipment variation dominates"
elif percent_repro > percent_repeat * 1.5:
    root_cause = "Operator variation dominates"
else:
    root_cause = "Balanced measurement variation"
```

---

## 3. Part-To-Part Variation

Part-to-part variation reflects how much real process variation exists relative to measurement noise.

| Percent Part-To-Part | Interpretation |
|----------------------|---------------|
| > 80% | Good discrimination between parts |
| 50–80% | Moderate discrimination |
| < 50% | Poor discrimination |

Example logic:

```python
if percent_part > 80:
    discrimination = "Good"
elif percent_part > 50:
    discrimination = "Moderate"
else:
    discrimination = "Poor"
```

---

# Overall Measurement System Rating

The overall system classification is determined using the primary indicators.

Priority order:

1. Percent Gage R&R
2. Part-to-Part variation

Example logic:

```python
if percent_gage_rr > 30:
    overall_status = "Measurement system NOT acceptable"

elif percent_gage_rr <= 10 and percent_part > 80:
    overall_status = "Measurement system acceptable"

else:
    overall_status = "Measurement system conditionally acceptable"
```

---

# Diagnostic Output Table

The interpretation component can produce a summary table like:

| Metric | Value | Interpretation |
|------|------|---------------|
| Percent Gage R&R | 12.5% | Marginal |
| Percent Repeatability | 8.0% | Moderate equipment variation |
| Percent Reproducibility | 4.5% | Low operator variation |
| Percent Part-To-Part | 87.5% | Good discrimination |

---

# Recommendation Engine

Recommendations are generated based on the dominant source of variation.

## Equipment Variation Dominant

Possible causes:

- Instrument resolution limitations
- Calibration issues
- Unstable fixturing
- Measurement environment noise

Recommendation:

```
Investigate instrument precision, calibration procedures, and fixture stability.
```

---

## Operator Variation Dominant

Possible causes:

- Inconsistent measurement technique
- Insufficient operator training
- Ambiguous measurement procedures

Recommendation:

```
Standardize the measurement procedure and retrain operators to ensure consistent technique.
```

---

## Low Part-To-Part Variation

Possible cause:

- Study parts are too similar to reveal meaningful variation

Recommendation:

```
Select parts that span the full expected range of process variation.
```

---

# Example Implementation

Example function consuming the `results` dictionary.

```python
def interpret_gage_rr(results):

    metrics = results["summary_metrics"]

    percent_gage_rr = metrics["PercentGageRR"]
    percent_repeat = metrics["PercentRepeatability"]
    percent_repro = metrics["PercentReproducibility"]
    percent_part = metrics["PercentPartToPart"]

    if percent_gage_rr < 10:
        gage_rr_status = "Acceptable"
    elif percent_gage_rr <= 30:
        gage_rr_status = "Marginal"
    else:
        gage_rr_status = "Not Acceptable"

    if percent_repeat > percent_repro * 1.5:
        root_cause = "Equipment variation dominates"
    elif percent_repro > percent_repeat * 1.5:
        root_cause = "Operator variation dominates"
    else:
        root_cause = "Balanced measurement variation"

    if percent_part > 80:
        discrimination = "Good"
    elif percent_part > 50:
        discrimination = "Moderate"
    else:
        discrimination = "Poor"

    if percent_gage_rr > 30:
        overall = "Measurement system NOT acceptable"
    elif percent_gage_rr <= 10 and percent_part > 80:
        overall = "Measurement system acceptable"
    else:
        overall = "Measurement system conditionally acceptable"

    return {

        "overall_status": overall,
        "gage_rr_status": gage_rr_status,
        "root_cause": root_cause,
        "discrimination": discrimination
    }
```

---

# Integration with Analysis Pipeline

The interpretation component is placed at the end of the analysis workflow.

```
Raw Measurement Data
        ↓
ComputeGageRR()
        ↓
ANOVA Table
Variance Components
Gage R&R Table
Operator Statistics
        ↓
Interpretation Component
        ↓
Final Report / Dashboard
```

This separation allows the statistical computation layer and interpretation layer to remain independent and easier to maintain.
