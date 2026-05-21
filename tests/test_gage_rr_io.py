# tests/test_gage_rr_io.py
import pytest
import pandas as pd
import io
from gage_rr_companion.cornelius import generate_template
from gage_rr_companion.gage_rr_io import load_gage_rr_data, GageRRDataError

# --- Helpers ---

def make_csv(content):
    """Wrap a CSV string in a StringIO object so we can pass it without a real file."""
    return io.StringIO(content)

VALID_CSV = """Operator,Part,Trial,Value
Alice,1,1,5.1
Alice,1,2,5.2
Bob,1,1,4.9
Bob,1,2,5.0
"""

# --- Happy path ---

def test_load_valid_data_returns_dataframe():
    df = load_gage_rr_data(make_csv(VALID_CSV), is_path=False)
    assert isinstance(df, pd.DataFrame)

def test_load_valid_data_row_count():
    df = load_gage_rr_data(make_csv(VALID_CSV), is_path=False)
    assert len(df) == 4

def test_operator_is_category():
    df = load_gage_rr_data(make_csv(VALID_CSV), is_path=False)
    assert df["Operator"].dtype.name == "category"

def test_part_is_category():
    df = load_gage_rr_data(make_csv(VALID_CSV), is_path=False)
    assert df["Part"].dtype.name == "category"

def test_trial_is_int():
    df = load_gage_rr_data(make_csv(VALID_CSV), is_path=False)
    assert pd.api.types.is_integer_dtype(df["Trial"])

def test_value_is_float():
    df = load_gage_rr_data(make_csv(VALID_CSV), is_path=False)
    assert df["Value"].dtype == float

def test_dataframe_is_editable():
    df = load_gage_rr_data(make_csv(VALID_CSV), is_path=False)
    df.loc[0, "Value"] = 99.9
    assert df.loc[0, "Value"] == 99.9



def test_enhanced_crossed_template_rows_are_cleaned():
    csv = """Test #,Operator,Part,Trial,Value
example:,Logan,Screw A,1,10
1,Alice,1,1,5.1
2,Alice,1,2,5.2
3,,,,
4,,,,
"""
    df = load_gage_rr_data(make_csv(csv), is_path=False)
    assert len(df) == 2
    assert list(df[["Operator", "Part", "Trial", "Value"]].columns) == [
        "Operator", "Part", "Trial", "Value"
    ]
    assert [str(value) for value in df["Test #"]] == ["1", "2"]


def test_enhanced_template_header_aliases_are_canonicalized():
    csv = """Test #,Operator,Part (The item you are measuring),Trial/Replicate,Value
1,Alice,Screw A,1,5.1
2,Bob,Screw B,1,5.2
"""
    df = load_gage_rr_data(make_csv(csv), is_path=False)
    assert "Part" in df.columns
    assert "Trial" in df.columns
    assert pd.api.types.is_integer_dtype(df["Trial"])
    assert df["Value"].dtype == float



def test_generated_crossed_template_uses_recommended_row_count():
    filename, excel_bytes = generate_template(
        "crossed",
        num_operators=2,
        num_parts=3,
        num_trials=2,
    )
    df = pd.read_excel(io.BytesIO(excel_bytes))
    assert filename == "crossed-template.xlsx"
    assert list(df.columns) == ["Test #", "Operator", "Part", "Trial", "Value"]
    assert df.iloc[0]["Test #"] == "example:"
    assert list(df["Test #"].iloc[1:]) == list(range(1, 13))


def test_generated_type1_template_defaults_to_50_rows_plus_example():
    _, excel_bytes = generate_template("type1", "Conductivity")
    df = pd.read_excel(io.BytesIO(excel_bytes))
    assert list(df.columns) == ["Test #", "Conductivity"]
    assert df.iloc[0]["Test #"] == "example:"
    assert len(df.iloc[1:]) == 50
    assert df["Test #"].iloc[-1] == 50

# --- File not found ---

def test_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        load_gage_rr_data("nonexistent_file.csv", is_path=True)

# --- Empty file ---

def test_empty_file_raises():
    with pytest.raises(pd.errors.EmptyDataError):
        load_gage_rr_data(make_csv(""), is_path=False)

# --- No data rows ---

def test_header_only_raises():
    with pytest.raises(ValueError, match="no measurement rows"):
        load_gage_rr_data(make_csv("Operator,Part,Trial,Value\n"), is_path=False)

# --- Unnamed columns ---

def test_unnamed_column_raises():
    csv = "Operator,Part,Trial,Value,\nAlice,1,1,5.1,\n"
    with pytest.raises(ValueError, match="unnamed columns"):
        load_gage_rr_data(make_csv(csv), is_path=False)

# --- Missing required columns ---

def test_missing_operator_col_raises():
    csv = "Part,Trial,Value\n1,1,5.1\n"
    with pytest.raises(ValueError, match="Operator"):
        load_gage_rr_data(make_csv(csv), is_path=False)

def test_missing_value_col_raises():
    csv = "Operator,Part,Trial\nAlice,1,1\n"
    with pytest.raises(ValueError, match="Value"):
        load_gage_rr_data(make_csv(csv), is_path=False)

# --- Missing values ---

def test_missing_value_in_operator_raises():
    csv = "Operator,Part,Trial,Value\n,1,1,5.1\nBob,1,2,5.0\n"
    with pytest.raises(ValueError, match="missing values"):
        load_gage_rr_data(make_csv(csv), is_path=False)

def test_missing_value_in_value_col_raises():
    csv = "Operator,Part,Trial,Value\nAlice,1,1,\nBob,1,2,5.0\n"
    with pytest.raises(ValueError, match="missing values"):
        load_gage_rr_data(make_csv(csv), is_path=False)

# --- Type coercion ---

def test_trial_as_string_int_coerces():
    csv = "Operator,Part,Trial,Value\nAlice,1,1,5.1\nBob,1,2,5.0\n"
    df = load_gage_rr_data(make_csv(csv), is_path=False)
    assert pd.api.types.is_integer_dtype(df["Trial"])

def test_non_numeric_trial_raises():
    csv = "Operator,Part,Trial,Value\nAlice,1,abc,5.1\n"
    with pytest.raises(TypeError, match="Trial"):
        load_gage_rr_data(make_csv(csv), is_path=False)

def test_non_numeric_value_raises():
    csv = "Operator,Part,Trial,Value\nAlice,1,1,bad\n"
    with pytest.raises(TypeError, match="Value"):
        load_gage_rr_data(make_csv(csv), is_path=False)

# --- Custom column names ---

def test_custom_column_names():
    csv = "Op,Prt,Rep,Meas\nAlice,1,1,5.1\nBob,1,2,5.0\n"
    df = load_gage_rr_data(
        make_csv(csv),
        operator_col="Op", part_col="Prt", trial_col="Rep", value_col="Meas",
        is_path=False
    )
    assert list(df.columns) == ["Op", "Prt", "Rep", "Meas"]

# --- Optional method column ---

def test_method_col_loads_as_category():
    csv = "Operator,Part,Trial,Value,Method\nAlice,1,1,5.1,A\nBob,1,2,5.0,B\n"
    df = load_gage_rr_data(make_csv(csv), method_col="Method", is_path=False)
    assert df["Method"].dtype.name == "category"

def test_method_col_missing_from_data_raises():
    with pytest.raises(ValueError, match="Method"):
        load_gage_rr_data(make_csv(VALID_CSV), method_col="Method", is_path=False)

def test_method_col_with_nulls_raises():
    csv = "Operator,Part,Trial,Value,Method\nAlice,1,1,5.1,\nBob,1,2,5.0,B\n"
    with pytest.raises(ValueError, match="missing values"):
        load_gage_rr_data(make_csv(csv), method_col="Method", is_path=False)
