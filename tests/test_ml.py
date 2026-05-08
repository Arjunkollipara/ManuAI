import json
import os
import pickle

import pandas as pd
import pytest

from ml.evaluate import get_feature_importance
from ml.predict import get_predictor


@pytest.fixture
def predictor():
    model_predictor = get_predictor()
    if hasattr(model_predictor.model, "n_jobs"):
        model_predictor.model.n_jobs = 1
    return model_predictor


@pytest.fixture
def sample_sensor_input():
    return {
        "air_temp_k": 298.1,
        "process_temp_k": 308.6,
        "rotational_speed_rpm": 1551,
        "torque_nm": 42.8,
        "tool_wear_min": 0,
        "type": "M",
    }


@pytest.fixture
def high_risk_input():
    return {
        "air_temp_k": 305.0,
        "process_temp_k": 315.0,
        "rotational_speed_rpm": 1200,
        "torque_nm": 75.0,
        "tool_wear_min": 220,
        "type": "H",
    }


def test_model_file_exists():
    assert os.path.exists("ml/models/random_forest.pkl")
    assert os.path.exists("ml/models/training_metadata.json")


def test_model_loads_correctly():
    with open("ml/models/random_forest.pkl", "rb") as f:
        model = pickle.load(f)
    assert model is not None
    assert hasattr(model, "predict")
    assert hasattr(model, "predict_proba")


def test_training_metrics():
    metadata = json.load(open("ml/models/training_metadata.json", "r", encoding="utf-8"))
    metrics = metadata["metrics"]
    assert metrics["recall"] >= 0.70
    assert metrics["f1_score"] >= 0.50
    assert metrics["roc_auc"] >= 0.85
    assert metrics["accuracy"] >= 0.90


def test_predictor_singleton():
    p1 = get_predictor()
    p2 = get_predictor()
    assert p1 is p2


def test_preprocess_input(predictor, sample_sensor_input):
    df = predictor.preprocess_input(sample_sensor_input)
    assert isinstance(df, pd.DataFrame)
    assert df.shape[1] == 13
    assert set(predictor.feature_columns).issubset(set(df.columns))
    assert df.isnull().sum().sum() == 0


def test_prediction_output_structure(predictor, sample_sensor_input):
    result = predictor.predict(sample_sensor_input)
    keys = {
        "failure_predicted",
        "failure_probability",
        "risk_level",
        "explanation",
        "top_contributing_features",
        "timestamp",
    }
    assert keys.issubset(set(result.keys()))
    assert 0 <= result["failure_probability"] <= 1
    assert result["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_risk_levels_make_sense(predictor, sample_sensor_input, high_risk_input):
    normal = predictor.predict(sample_sensor_input)
    high_risk = predictor.predict(high_risk_input)
    assert high_risk["failure_probability"] > normal["failure_probability"]
    assert high_risk["failure_probability"] > 0.5


def test_feature_importance(predictor):
    importance = get_feature_importance(predictor.model, predictor.feature_columns)
    assert isinstance(importance, dict)
    assert len(importance) == 13
    assert all(0 <= value <= 1 for value in importance.values())
    assert sum(importance.values()) == pytest.approx(1.0, abs=0.01)
