import json
import os

import pandas as pd
import pytest


@pytest.fixture
def sample_raw_data():
    rows = []
    for i in range(100):
        rows.append(
            {
                "udi": i + 1,
                "product_id": f"TEST{i:05d}",
                "type": "M" if i % 3 else "H",
                "air_temp_k": 298.0 + (i % 5) * 0.1,
                "process_temp_k": 308.0 + (i % 7) * 0.1,
                "rotational_speed_rpm": 1500 + (i % 20),
                "torque_nm": 40.0 + (i % 10) * 0.5,
                "tool_wear_min": i % 250,
                "machine_failure": 1 if i in {2, 35, 77} else 0,
                "twf": 0,
                "hdf": 0,
                "pwf": 0,
                "osf": 0,
                "rnf": 0,
            }
        )
    return pd.DataFrame(rows)


def test_raw_data_schema():
    path = "data/raw/ai4i2020.parquet"
    assert os.path.exists(path)

    df = pd.read_parquet(path)
    required_columns = {
        "udi",
        "product_id",
        "type",
        "air_temp_k",
        "process_temp_k",
        "rotational_speed_rpm",
        "torque_nm",
        "tool_wear_min",
        "machine_failure",
        "twf",
        "hdf",
        "pwf",
        "osf",
        "rnf",
    }
    rename_map = {
        "UDI": "udi",
        "Product ID": "product_id",
        "Type": "type",
        "Air temperature [K]": "air_temp_k",
        "Process temperature [K]": "process_temp_k",
        "Rotational speed [rpm]": "rotational_speed_rpm",
        "Torque [Nm]": "torque_nm",
        "Tool wear [min]": "tool_wear_min",
        "Machine failure": "machine_failure",
        "TWF": "twf",
        "HDF": "hdf",
        "PWF": "pwf",
        "OSF": "osf",
        "RNF": "rnf",
    }
    normalized = {rename_map.get(col, col) for col in df.columns}
    assert required_columns.issubset(normalized)
    assert len(df) > 0
    failure_col = "machine_failure" if "machine_failure" in df.columns else "Machine failure"
    assert set(df[failure_col].dropna().unique()).issubset({0, 1})


def test_staged_data_exists():
    path = "data/staged/ai4i2020_staged.parquet"
    assert os.path.exists(path)

    df = pd.read_parquet(path)
    assert df.isnull().sum().sum() == 0
    assert "data_quality_flag" in df.columns


def test_curated_features_exist():
    features_path = "data/curated/ai4i2020_features.parquet"
    metadata_path = "data/curated/feature_metadata.json"

    assert os.path.exists(features_path)
    assert os.path.exists(metadata_path)

    df = pd.read_parquet(features_path)
    metadata = json.load(open(metadata_path, "r", encoding="utf-8"))
    feature_columns = metadata["feature_columns"]

    for col in feature_columns:
        assert col in df.columns
    assert "machine_failure" in df.columns


def test_feature_engineering_values():
    df = pd.read_parquet("data/curated/ai4i2020_features.parquet")
    staged = pd.read_parquet("data/staged/ai4i2020_staged.parquet")

    for idx in range(10):
        expected_temp_diff = staged.iloc[idx]["process_temp_k"] - staged.iloc[idx]["air_temp_k"]
        expected_power = staged.iloc[idx]["torque_nm"] * staged.iloc[idx]["rotational_speed_rpm"]
        assert df.iloc[idx]["temp_difference"] == pytest.approx(expected_temp_diff, abs=0.01)
        assert df.iloc[idx]["power"] == pytest.approx(expected_power, abs=0.01)

    assert ((df["failure_risk_score"] >= 0) & (df["failure_risk_score"] <= 1)).all()
    assert set(df["high_torque_flag"].unique()).issubset({0, 1})
    assert set(df["high_wear_flag"].unique()).issubset({0, 1})


def test_validation_report():
    report = json.load(open("data/curated/validation_report.json", "r", encoding="utf-8"))
    assert report["overall_status"] == "PASSED"
    assert report["ready_for_ml"] is True

    checks = report.get("checks", {})
    assert len(checks) == 6
    for check in checks.values():
        assert check.get("status") in {"PASSED", "WARNING"}
