import os

import pandas as pd


class GageRRDataError(Exception):
    """Custom exception for Gage R&R data validation errors."""
    pass


EXCEL_EXTENSIONS = (".xlsx", ".xlsm", ".xls")

COLUMN_ALIASES = {
    "Operator": {"operator", "appraiser", "appraiser/operator"},
    "Part": {"part", "sample", "part (the item you are measuring)"},
    "Trial": {"trial", "trial/replicate", "replicate", "replication"},
    "Value": {"value", "measurement", "measured value", "readout"},
    "Test #": {"test #", "test#", "test number", "test no", "test no."},
}


def _source_name(filepath) -> str:
    return str(getattr(filepath, "name", filepath) or "")


def _is_excel_source(filepath) -> bool:
    return _source_name(filepath).lower().endswith(EXCEL_EXTENSIONS)


def load_uploaded_table(filepath, is_path=True):
    """Load a user-uploaded CSV or Excel table into a DataFrame."""
    if is_path and not os.path.exists(filepath):
        raise FileNotFoundError(f"The file '{filepath}' does not exist.")

    try:
        if _is_excel_source(filepath):
            return pd.read_excel(filepath)
        return pd.read_csv(filepath)
    except pd.errors.EmptyDataError:
        raise pd.errors.EmptyDataError(f"The file '{filepath}' is empty.")


def _normalize_column_name(name: object) -> str:
    return " ".join(str(name).strip().lower().split())


def _canonicalize_template_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    used_names = set(df.columns.astype(str))

    for column in df.columns:
        column_text = str(column).strip()
        normalized = _normalize_column_name(column_text)
        for canonical, aliases in COLUMN_ALIASES.items():
            if normalized in aliases and column_text != canonical and canonical not in used_names:
                rename_map[column] = canonical
                used_names.add(canonical)
                break

    if rename_map:
        df = df.rename(columns=rename_map)

    df.columns = [str(column).strip() for column in df.columns]
    return df


def _drop_example_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    cleaned = df.copy()
    first_col = cleaned.iloc[:, 0].map(
        lambda value: str(value).strip().lower() if pd.notna(value) else ""
    )
    return cleaned[~first_col.isin({"example", "example:"})].reset_index(drop=True)


def clean_uploaded_template_table(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize generated-template conveniences before analysis."""
    df = _canonicalize_template_columns(df)
    return _drop_example_rows(df)


def _drop_template_helper_rows(df: pd.DataFrame, required_cols: list[str]) -> pd.DataFrame:
    cleaned = clean_uploaded_template_table(df)

    blank_required = (
        cleaned[required_cols]
        .replace(r"^\s*$", pd.NA, regex=True)
        .isna()
        .all(axis=1)
    )
    cleaned = cleaned[~blank_required]

    return cleaned.reset_index(drop=True)


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
    # Load CSV or Excel
    # -------------------------
    df = load_uploaded_table(filepath, is_path=is_path)
    df = clean_uploaded_template_table(df)

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

    df = _drop_template_helper_rows(df, required_cols)

    if df.shape[0] == 0:
        raise ValueError("Dataset contains no measurement rows.")

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
