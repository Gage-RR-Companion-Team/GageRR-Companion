import pandas as pd
import re

class CSVValidationError(Exception):
    pass

def read_and_validate_csv(file_path):
    # Read CSV
    df = pd.read_csv(file_path)
    # Normalize column names (lowercase, strip spaces)
    normalized_cols = [col.strip().lower() for col in df.columns]
    df.columns = normalized_cols

    # Find operator column
    operator_col = next((col for col in normalized_cols if re.search(r'operator', col)), None)
    if not operator_col:
        raise CSVValidationError("Missing operator column.")
    # Find part number column
    part_col = next((col for col in normalized_cols if re.search(r'part', col)), None)
    if not part_col:
        raise CSVValidationError("Missing part number column.")
    # Find measurement columns (replicates)
    measurement_cols = [col for col in normalized_cols if re.search(r'measurement|replicate|value', col)]
    if len(measurement_cols) < 1:
        raise CSVValidationError("Missing measurement columns.")

    # Check types
    if not pd.api.types.is_string_dtype(df[operator_col]):
        raise CSVValidationError("Operator column must be string.")
    if not pd.api.types.is_string_dtype(df[part_col]):
        raise CSVValidationError("Part number column must be string.")

    # Group by operator and part number
    grouped = df.groupby([operator_col, part_col])
    # Check for n replicates per group
    replicate_counts = grouped.size()
    if replicate_counts.min() < 1:
        raise CSVValidationError("Each operator-part combo must have at least one measurement.")

    return df, operator_col, part_col, measurement_cols

# Example usage:
# try:
#     df, op_col, part_col, meas_cols = read_and_validate_csv('yourfile.csv')
# except CSVValidationError as e:
#     print(f"Error: {e}")
