"""Performs feature engineering to generate features for ML models."""

import os
import json
import logging
from typing import Dict, Any, List

import pandas as pd

logger = logging.getLogger('feature_engineer')
if not logger.handlers:
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/pipeline.log', mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

FEATURE_COLUMNS: List[str] = [
    'air_temp_k',
    'process_temp_k',
    'rotational_speed_rpm',
    'torque_nm',
    'tool_wear_min',
    'temp_difference',
    'power',
    'tool_wear_rate',
    'temp_wear_interaction',
    'high_torque_flag',
    'high_wear_flag',
    'type_encoded',
    'failure_risk_score'
]

TARGET_COLUMN = 'machine_failure'

TYPE_ENCODING = {'L': 0, 'M': 1, 'H': 2}


def calculate_failure_risk_score(df: pd.DataFrame) -> pd.Series:
    score = (
        (df['torque_nm'] / 80) * 0.3 +
        (df['tool_wear_min'] / 250) * 0.3 +
        (df['temp_difference'] / 15) * 0.2 +
        df['high_torque_flag'] * 0.1 +
        df['high_wear_flag'] * 0.1
    )
    return score.clip(lower=0.0, upper=1.0)


def build_feature_metadata(df: pd.DataFrame, feature_columns: List[str], target_column: str) -> Dict[str, Any]:
    feature_stats: Dict[str, Dict[str, float]] = {}
    for feature in feature_columns:
        series = df[feature].astype(float)
        feature_stats[feature] = {
            'mean': float(series.mean()),
            'std': float(series.std(ddof=0)),
            'min': float(series.min()),
            'max': float(series.max())
        }

    failure_rate = 0.0
    if target_column in df.columns and len(df) > 0:
        failure_rate = float((df[target_column] == 1).sum() / len(df) * 100)

    return {
        'feature_columns': feature_columns,
        'target_column': target_column,
        'total_rows': int(len(df)),
        'failure_rate_percent': failure_rate,
        'feature_stats': feature_stats
    }


def engineer_features(
    input_parquet_path: str,
    curated_parquet_path: str,
    features_parquet_path: str,
    metadata_path: str
) -> Dict[str, Any]:
    logger.info('Starting feature engineering from %s', input_parquet_path)

    summary: Dict[str, Any] = {
        'rows_input': 0,
        'new_features_created': FEATURE_COLUMNS.copy(),
        'feature_columns_total': len(FEATURE_COLUMNS),
        'target_column': TARGET_COLUMN,
        'failure_rate': 0.0,
        'curated_parquet_saved': False,
        'features_parquet_saved': False,
        'feature_metadata_saved': False,
        'log_appended': True,
        'errors': []
    }

    try:
        df = pd.read_parquet(input_parquet_path)
        summary['rows_input'] = len(df)
        logger.info('Loaded %d rows from %s', summary['rows_input'], input_parquet_path)

        required_columns = [
            'air_temp_k', 'process_temp_k', 'rotational_speed_rpm',
            'torque_nm', 'tool_wear_min', 'type', TARGET_COLUMN
        ]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f'Missing required columns in staged data: {missing}')

        df['temp_difference'] = df['process_temp_k'] - df['air_temp_k']
        df['power'] = df['torque_nm'] * df['rotational_speed_rpm']
        df['tool_wear_rate'] = df['tool_wear_min'] / (df['rotational_speed_rpm'] + 1)
        df['temp_wear_interaction'] = df['air_temp_k'] * df['tool_wear_min']
        df['high_torque_flag'] = (df['torque_nm'] > 60).astype(int)
        df['high_wear_flag'] = (df['tool_wear_min'] > 200).astype(int)
        df['type_encoded'] = df['type'].map(TYPE_ENCODING).fillna(-1).astype(int)
        df['failure_risk_score'] = calculate_failure_risk_score(df)

        logger.info('Created new feature columns: %s', FEATURE_COLUMNS)

        os.makedirs(os.path.dirname(curated_parquet_path), exist_ok=True)
        df.to_parquet(curated_parquet_path, index=False)
        summary['curated_parquet_saved'] = True
        logger.info('Saved curated parquet to %s', curated_parquet_path)

        features_df = df[FEATURE_COLUMNS + [TARGET_COLUMN]]
        os.makedirs(os.path.dirname(features_parquet_path), exist_ok=True)
        features_df.to_parquet(features_parquet_path, index=False)
        summary['features_parquet_saved'] = True
        logger.info('Saved features parquet to %s', features_parquet_path)

        metadata = build_feature_metadata(features_df, FEATURE_COLUMNS, TARGET_COLUMN)
        summary['failure_rate'] = metadata['failure_rate_percent']
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        summary['feature_metadata_saved'] = True
        logger.info('Saved feature metadata to %s', metadata_path)

    except Exception as exc:
        error_message = str(exc)
        summary['errors'].append(error_message)
        summary['log_appended'] = True
        logger.error('Feature engineering failed with error: %s', error_message)

    return summary


if __name__ == '__main__':
    result = engineer_features(
        input_parquet_path='data/staged/ai4i2020_staged.parquet',
        curated_parquet_path='data/curated/ai4i2020_curated.parquet',
        features_parquet_path='data/curated/ai4i2020_features.parquet',
        metadata_path='data/curated/feature_metadata.json'
    )
    print('FEATURE_ENGINEERING_RESULT:', result)
