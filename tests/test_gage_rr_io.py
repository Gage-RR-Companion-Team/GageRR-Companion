# tests/test_gage_rr_io.py
import pytest
import pandas as pd
import io
from gage_rr_companion.cornelius import generate_template
from gage_rr_companion.gage_rr_io import load_gage_rr_data, validate_gage_rr_study_design, GageRRDataError

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


def test_generated_expanded_template_matches_notebook_example_shape():
    filename, excel_bytes = generate_template("expanded")
    df = pd.read_excel(io.BytesIO(excel_bytes))
    assert filename == "expanded-template.xlsx"
    assert list(df.columns) == ["Test #", "Part", "Operator", "Parameter 1", "Trial", "Value"]
    assert df.iloc[0].to_dict() == {
        "Test #": "example:",
        "Part": "Part 1",
        "Operator": "Operator A",
        "Parameter 1": "Parameter 1",
        "Trial": 1,
        "Value": 10,
    }
    assert len(df.iloc[1:]) == 180
    assert df["Test #"].iloc[-1] == 180


def test_generated_expanded_template_uses_custom_parameter_headers():
    filename, excel_bytes = generate_template(
        "expanded",
        parameter_names=["Station", "Fixture", "Probe"],
        num_operators=2,
        num_parts=3,
        num_trials=2,
    )
    df = pd.read_excel(io.BytesIO(excel_bytes))
    assert filename == "expanded-template.xlsx"
    assert list(df.columns) == [
        "Test #",
        "Part",
        "Operator",
        "Station",
        "Fixture",
        "Probe",
        "Trial",
        "Value",
    ]
    assert df.iloc[0]["Station"] == "Station"
    assert df.iloc[0]["Fixture"] == "Fixture"
    assert df.iloc[0]["Probe"] == "Probe"
    assert len(df.iloc[1:]) == 36


def test_generated_expanded_template_row_count_uses_parameter_count():
    _, excel_bytes = generate_template(
        "expanded",
        parameter_names=["Parameter 1", "Parameter 2"],
        num_operators=2,
        num_parts=3,
        num_trials=2,
    )
    df = pd.read_excel(io.BytesIO(excel_bytes))
    assert len(df.iloc[1:]) == 24



def test_nested_style_raw_upload_loads_successfully():
    csv = """Operator,Part,Trial,Value
Operator A,A-1,1,10.01
Operator A,A-1,2,10.02
Operator A,A-2,1,10.34
Operator B,B-1,1,10.11
Operator B,B-1,2,10.10
Operator C,C-1,1,9.98
"""
    df = load_gage_rr_data(make_csv(csv), is_path=False)
    assert list(df.columns) == ["Operator", "Part", "Trial", "Value"]
    assert len(df) == 6
    assert set(df["Operator"].astype(str)) == {"Operator A", "Operator B", "Operator C"}


def test_summary_results_upload_message_points_to_raw_measurements():
    csv = """Source,% Contribution,% Study Var,% Gage R&R
Gage R&R,15.2,39.0,39.0
Repeatability,8.1,28.5,28.5
Reproducibility,7.1,26.6,26.6
"""
    with pytest.raises(ValueError, match="raw measurement upload"):
        load_gage_rr_data(make_csv(csv), is_path=False)


def test_missing_columns_message_describes_crossed_nested_format():
    csv = """Operator,Part,Value
Alice,1,5.1
"""
    with pytest.raises(ValueError, match="Operator, Part, Trial, Value"):
        load_gage_rr_data(make_csv(csv), is_path=False)




def test_nested_file_rejected_when_crossed_study_selected():
    csv = """Operator,Part,Trial,Value
Ryan,A-1,1,5.068
Ryan,A-1,2,5.070
Sabrina,B-1,1,5.144
Sabrina,B-1,2,5.142
Taylor,C-1,1,4.992
Taylor,C-1,2,4.994
"""
    df = load_gage_rr_data(make_csv(csv), is_path=False)
    with pytest.raises(ValueError, match="looks like a Nested Gage R&R design"):
        validate_gage_rr_study_design(df, "Crossed Gage R&R")


def test_crossed_file_rejected_when_nested_study_selected():
    csv = """Operator,Part,Trial,Value
Ryan,1,1,5.068
Ryan,1,2,5.070
Sabrina,1,1,5.144
Sabrina,1,2,5.142
Ryan,2,1,4.992
Sabrina,2,1,4.994
"""
    df = load_gage_rr_data(make_csv(csv), is_path=False)
    with pytest.raises(ValueError, match="looks like a Crossed Gage R&R design"):
        validate_gage_rr_study_design(df, "Nested Gage R&R")


def test_valid_crossed_file_passes_study_design_validation():
    df = load_gage_rr_data(make_csv(VALID_CSV), is_path=False)
    validate_gage_rr_study_design(df, "Crossed Gage R&R")




def test_nested_compute_handles_categorical_part_labels_from_upload():
    from gage_rr_companion.compute_nested import ComputeGageRR_Nested
    from gage_rr_companion.interpret_gage_rr import interpret_gage_rr

    csv = """Operator,Part,Trial,Value
Ryan,A-1,1,5.068
Ryan,A-1,2,5.070
Ryan,A-1,3,5.086
Ryan,A-1,4,5.088
Ryan,A-2,1,5.192
Ryan,A-2,2,5.200
Ryan,A-2,3,5.206
Ryan,A-2,4,5.218
Ryan,A-3,1,5.020
Ryan,A-3,2,5.029
Ryan,A-3,3,5.032
Ryan,A-3,4,5.043
Sabrina,B-1,1,5.094
Sabrina,B-1,2,5.103
Sabrina,B-1,3,5.096
Sabrina,B-1,4,5.108
Sabrina,B-2,1,5.196
Sabrina,B-2,2,5.189
Sabrina,B-2,3,5.196
Sabrina,B-2,4,5.191
Sabrina,B-3,1,5.068
Sabrina,B-3,2,5.068
Sabrina,B-3,3,5.065
Sabrina,B-3,4,5.068
Cornelius,C-1,1,5.090
Cornelius,C-1,2,5.084
Cornelius,C-1,3,5.091
Cornelius,C-1,4,5.084
Cornelius,C-2,1,5.212
Cornelius,C-2,2,5.224
Cornelius,C-2,3,5.217
Cornelius,C-2,4,5.226
Cornelius,C-3,1,5.046
Cornelius,C-3,2,5.047
Cornelius,C-3,3,5.057
Cornelius,C-3,4,5.052
"""
    df = load_gage_rr_data(make_csv(csv), is_path=False)
    validate_gage_rr_study_design(df, "Nested Gage R&R")
    results = ComputeGageRR_Nested(df)
    metrics = results["summary_metrics"]

    assert metrics["PercentGageRR"] == pytest.approx(0.7512230645)
    assert metrics["PercentPartToPart"] == pytest.approx(99.2487769355)
    assert interpret_gage_rr(results)["overall_status"] == "Measurement system acceptable"


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
