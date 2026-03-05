from gage_rr_companion.gage_rr_io import load_gage_rr_data
from gage_rr_companion.compute import ComputeGageRR

"""
This script serves as a test for the Gage R&R analysis code I just wrote. It loads a dataset,
 runs the analysis, and prints the results.
 """

# Load your dataset
df = load_gage_rr_data("../data/measurements.csv")

# Run analysis
results = ComputeGageRR(df)


# Print outputs
print("\n=== METADATA ===")
print(results["metadata"])

print("\n=== WARNINGS ===")
print(results["warnings"])

print("\n=== ANOVA TABLE ===")
print(results["anova_table"])

print("\n=== VARIANCE COMPONENTS ===")
print(results["variance_components"])

print("\n=== GAGE RR TABLE ===")
print(results["gage_rr_table"])

print("\n=== OPERATOR STATS ===")
print(results["operator_stats"])

print("\n=== SUMMARY METRICS ===")
print(results["summary_metrics"])
