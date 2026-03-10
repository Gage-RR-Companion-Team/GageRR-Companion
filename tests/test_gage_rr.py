from gage_rr_companion.gage_rr_io import load_gage_rr_data
from gage_rr_companion.compute import ComputeGageRR
from gage_rr_companion.anova import ComputeANOVA
import pytest


"""
This script serves as a test for the Gage R&R analysis code I just wrote. It loads a dataset,
 runs the analysis, and prints the results.
 """
def test_full_analysis():
    """
    Smoke test
    """
    # Load your dataset
    df = load_gage_rr_data("data/measurements.csv")

    # Run analysis
    results = ComputeGageRR(df)
    return


