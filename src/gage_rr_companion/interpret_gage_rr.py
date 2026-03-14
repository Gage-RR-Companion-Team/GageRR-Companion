# interpret_gage_rr.py

"""
Gage R&R Interpretation Component

This module interprets the results dictionary produced by the ComputeGageRR
analysis pipeline and generates standardized measurement system diagnostics.

The component does not perform statistical calculations or generate plots.
It only interprets computed statistics according to Measurement System
Analysis (MSA) guidelines similar to those used by Minitab.

Expected input is the results dictionary returned by ComputeGageRR().
"""

import numpy as np

def interpret_gage_rr(results: dict) -> dict:
    """
    Interpret Gage R&R analysis results.

    Parameters
    ----------
    results : dict
        Dictionary produced by ComputeGageRR containing:
            - anova_table
            - variance_components
            - gage_rr_table
            - operator_stats
            - summary_metrics
            - metadata
            - warnings

    Returns
    -------
    dict
        Dictionary containing interpretation diagnostics including:
            - overall_status
            - gage_rr_status
            - root_cause
            - discrimination
            - recommendation
    """

    # ----------------------------
    # Validate presence of summary_metrics
    # ----------------------------
    if "summary_metrics" not in results:
        raise ValueError("Results dictionary missing 'summary_metrics'.")

    metrics = results["summary_metrics"]

    # Extract metrics
    try:
        percent_gage_rr = metrics["PercentGageRR"]
        percent_repeat = metrics["PercentRepeatability"]
        percent_repro = metrics["PercentReproducibility"]
        percent_part = metrics["PercentPartToPart"]
    except KeyError as e:
        raise KeyError(f"Missing required summary metric: {e}")

    # Check for NaN or None
    for k, v in {
        "PercentGageRR": percent_gage_rr,
        "PercentRepeatability": percent_repeat,
        "PercentReproducibility": percent_repro,
        "PercentPartToPart": percent_part
    }.items():
        if v is None or (isinstance(v, float) and np.isnan(v)):
            raise ValueError(f"Metric '{k}' is missing or NaN.")

    # ----------------------------
    # 1. Gage R&R Status
    # ----------------------------
    if percent_gage_rr < 10:
        gage_rr_status = "Acceptable"
    elif percent_gage_rr <= 30:
        gage_rr_status = "Marginal"
    else:
        gage_rr_status = "Not Acceptable"

    # ----------------------------
    # 2. Root Cause Analysis
    # ----------------------------
    if percent_repeat > percent_repro * 1.5:
        root_cause = "Equipment variation dominates"
    elif percent_repro > percent_repeat * 1.5:
        root_cause = "Operator variation dominates"
    else:
        root_cause = "Balanced measurement variation"

    # ----------------------------
    # 3. Part-To-Part Discrimination
    # ----------------------------
    if percent_part > 80:
        discrimination = "Good"
    elif percent_part > 50:
        discrimination = "Moderate"
    else:
        discrimination = "Poor"

    # ----------------------------
    # 4. Overall Measurement System Status
    # ----------------------------
    if percent_gage_rr > 30:
        overall_status = "Measurement system NOT acceptable"
    elif percent_gage_rr <= 10 and percent_part > 80:
        overall_status = "Measurement system acceptable"
    else:
        overall_status = "Measurement system conditionally acceptable"

    # ----------------------------
    # 5. Recommendation Engine
    # ----------------------------
    if root_cause == "Equipment variation dominates":
        recommendation = (
            "Investigate instrument precision, calibration procedures, "
            "and fixture stability."
        )
    elif root_cause == "Operator variation dominates":
        recommendation = (
            "Standardize the measurement procedure and retrain operators "
            "to ensure consistent technique."
        )
    elif discrimination == "Poor":
        recommendation = (
            "Select parts that span the full expected range of process variation."
        )
    else:
        recommendation = "Measurement system performance is generally acceptable."

    # ----------------------------
    # Assemble interpretation results
    # ----------------------------
    interpretation = {
        "overall_status": overall_status,
        "gage_rr_status": gage_rr_status,
        "root_cause": root_cause,
        "discrimination": discrimination,
        "recommendation": recommendation
    }

    return interpretation
