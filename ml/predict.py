"""Handles inference and prediction using trained models."""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

# Ensure project root is on sys.path when executing script directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd

from ml.evaluate import load_model, explain_prediction

MODEL_PATH = 'ml/models/random_forest.pkl'
FEATURE_METADATA_PATH = 'data/curated/feature_metadata.json'
TYPE_ENCODING = {'L': 0, 'M': 1, 'H': 2}

# Configure logging
os.makedirs('logs', exist_ok=True)
logger = logging.getLogger('ml.predict')
if not logger.handlers:
    file_handler = logging.FileHandler('logs/ml.log', mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)


def _compute_failure_risk_score(row: Dict[str, Any]) -> float:
    score = (
        (row['torque_nm'] / 80) * 0.3 +
        (row['tool_wear_min'] / 250) * 0.3 +
        ((row['process_temp_k'] - row['air_temp_k']) / 15) * 0.2 +
        (1 if row['torque_nm'] > 60 else 0) * 0.1 +
        (1 if row['tool_wear_min'] > 200 else 0) * 0.1
    )
    return max(0.0, min(1.0, score))


class ModelPredictor:
    def __init__(self):
        logger.info('Initializing ModelPredictor')
        self.model = load_model(MODEL_PATH)
        with open(FEATURE_METADATA_PATH, 'r', encoding='utf-8') as metadata_file:
            metadata = json.load(metadata_file)
        self.feature_columns = metadata.get('feature_columns', [])
        logger.info('ModelPredictor initialized successfully')

    def preprocess_input(self, raw_input: Dict[str, Any]) -> pd.DataFrame:
        logger.info('Preprocessing input: %s', raw_input)
        required_keys = [
            'air_temp_k',
            'process_temp_k',
            'rotational_speed_rpm',
            'torque_nm',
            'tool_wear_min',
            'type'
        ]
        missing = [key for key in required_keys if key not in raw_input]
        if missing:
            raise ValueError(f'Missing required input keys: {missing}')

        row = {
            'air_temp_k': float(raw_input['air_temp_k']),
            'process_temp_k': float(raw_input['process_temp_k']),
            'rotational_speed_rpm': int(raw_input['rotational_speed_rpm']),
            'torque_nm': float(raw_input['torque_nm']),
            'tool_wear_min': int(raw_input['tool_wear_min']),
            'type': str(raw_input['type']).upper()
        }
        if row['type'] not in TYPE_ENCODING:
            raise ValueError(f"Invalid type value: {row['type']}. Expected one of {list(TYPE_ENCODING.keys())}")

        row['temp_difference'] = row['process_temp_k'] - row['air_temp_k']
        row['power'] = row['torque_nm'] * row['rotational_speed_rpm']
        row['tool_wear_rate'] = row['tool_wear_min'] / (row['rotational_speed_rpm'] + 1)
        row['temp_wear_interaction'] = row['air_temp_k'] * row['tool_wear_min']
        row['high_torque_flag'] = 1 if row['torque_nm'] > 60 else 0
        row['high_wear_flag'] = 1 if row['tool_wear_min'] > 200 else 0
        row['type_encoded'] = TYPE_ENCODING[row['type']]
        row['failure_risk_score'] = _compute_failure_risk_score(row)

        df = pd.DataFrame([row])
        if 'type' in df.columns:
            df = df.drop(columns=['type'])
        missing_cols = [col for col in self.feature_columns if col not in df.columns]
        extra_cols = [col for col in df.columns if col not in self.feature_columns]
        if missing_cols or extra_cols:
            raise ValueError(f'Preprocessed input columns mismatch. missing={missing_cols}, extra={extra_cols}')

        df = df[self.feature_columns]
        logger.info('Preprocessed input into dataframe with columns: %s', self.feature_columns)
        return df

    def predict(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        df = self.preprocess_input(raw_input)
        explanation = explain_prediction(self.model, self.feature_columns, df)
        result = {
            'failure_predicted': explanation['failure_predicted'],
            'failure_probability': explanation['failure_probability'],
            'risk_level': explanation['risk_level'],
            'top_contributing_features': explanation['top_contributing_features'],
            'explanation': explanation['explanation'],
            'input_received': raw_input,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        logger.info('Prediction completed with risk_level=%s probability=%.4f', result['risk_level'], result['failure_probability'])
        return result

    def predict_batch(self, raw_inputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info('Running batch prediction for %d inputs', len(raw_inputs))
        results = [self.predict(raw_input) for raw_input in raw_inputs]
        logger.info('Batch prediction completed for %d inputs', len(results))
        return results


_predictor_instance: ModelPredictor = None


def get_predictor() -> ModelPredictor:
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = ModelPredictor()
    return _predictor_instance


if __name__ == '__main__':
    predictor = get_predictor()

    test_input = {
        'air_temp_k': 298.1,
        'process_temp_k': 308.6,
        'rotational_speed_rpm': 1551,
        'torque_nm': 42.8,
        'tool_wear_min': 0,
        'type': 'M'
    }

    result = predictor.predict(test_input)
    print(json.dumps(result, indent=2, default=str))

    high_risk_input = {
        'air_temp_k': 305.0,
        'process_temp_k': 315.0,
        'rotational_speed_rpm': 1200,
        'torque_nm': 75.0,
        'tool_wear_min': 220,
        'type': 'H'
    }

    result2 = predictor.predict(high_risk_input)
    print(json.dumps(result2, indent=2, default=str))
