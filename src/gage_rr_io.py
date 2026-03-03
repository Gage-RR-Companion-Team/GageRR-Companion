import pandas as pd
import os


class GageRRDataError(Exception):
    """Custom exception for Gage R&R data validation errors."""
    pass


def load_gage_rr_data(
    filepath,
    operator_col="Operator",
    part_col="Part",
    trial_col="Trial",
    value_col="Value",
    method_col=None,
    is_path=True
):
    """
    Loads and validates Gage R&R data in long format.

    Parameters
    ----------
    filepath : str
        Path to CSV file

    operator_col : str
    part_col : str
    trial_col : str
    value_col : str
    method_col : str or None

    Returns
    -------
    pandas.DataFrame
        Validated and editable DataFrame

    Raises
    ------
    FileNotFoundError
    pd.errors.EmptyDataError
    ValueError
    TypeError
    GageRRDataError
    """

    # -------------------------
    # File existence check
    # -------------------------
    if is_path:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"The file '{filepath}' does not exist.")

    # -------------------------
    # Load CSV
    # -------------------------
    try:
        df = pd.read_csv(filepath)
    except pd.errors.EmptyDataError:
        raise pd.errors.EmptyDataError(f"The file '{filepath}' is empty.")

    # -------------------------
    # Check dataset not empty
    # -------------------------
    if df.shape[0] == 0:
        raise ValueError("Dataset contains no measurement rows.")

    # -------------------------
    # Check for unnamed columns
    # -------------------------
    if any(col.startswith("Unnamed") or col.strip() == "" for col in df.columns.astype(str)):
        raise ValueError("Dataset contains unnamed columns. All columns must have labels.")

    # -------------------------
    # Check required columns exist
    # -------------------------
    required_cols = [operator_col, part_col, trial_col, value_col]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' is missing from the dataset.")

    # -------------------------
    # Check missing values
    # -------------------------
    for col in required_cols:
        if df[col].isna().any():
            raise ValueError(f"Column '{col}' contains missing values.")

    # -------------------------
    # Validate Trial column integer
    # -------------------------
    if not pd.api.types.is_integer_dtype(df[trial_col]):
        try:
            df[trial_col] = df[trial_col].astype(int)
        except:
            raise TypeError(f"Column '{trial_col}' must contain only integer values.")

    # -------------------------
    # Validate Value column numeric
    # -------------------------
    if not pd.api.types.is_numeric_dtype(df[value_col]):
        try:
            df[value_col] = pd.to_numeric(df[value_col])
        except:
            raise TypeError(f"Column '{value_col}' must contain only numeric values.")

    # -------------------------
    # Convert types
    # -------------------------
    df[operator_col] = df[operator_col].astype("category")
    df[part_col] = df[part_col].astype("category")
    df[trial_col] = df[trial_col].astype(int)
    df[value_col] = df[value_col].astype(float)

    # Optional method column
    if method_col is not None:
        if method_col not in df.columns:
            raise ValueError(f"Method column '{method_col}' was specified but not found.")

        if df[method_col].isna().any():
            raise ValueError(f"Column '{method_col}' contains missing values.")

        df[method_col] = df[method_col].astype("category")

    # -------------------------
    # Return editable DataFrame
    # -------------------------
    return df


# Example usage:
# df = load_gage_rr_data("measurements.csv")
# print(df)
# df.loc[0, "Value"] = 5.22   # editable
