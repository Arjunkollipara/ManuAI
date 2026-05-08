"""Script for training machine learning models for quality prediction."""

import os
import json
import pickle
import logging
from datetime import datetime
from typing import Dict, Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)
from sklearn.model_selection import train_test_split

logger = logging.getLogger('ml.train')
if not logger.handlers:
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/ml.log', mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

RAW_FEATURES_PATH = 'data/curated/ai4i2020_features.parquet'
FEATURE_METADATA_PATH = 'data/curated/feature_metadata.json'
MODEL_PATH = 'ml/models/random_forest.pkl'
METADATA_OUTPUT_PATH = 'ml/models/training_metadata.json'
TARGET_COLUMN = 'machine_failure'

HYPERPARAMETERS = {
    'n_estimators': 100,
    'max_depth': 10,
    'min_samples_split': 5,
    'min_samples_leaf': 2,
    'class_weight': 'balanced',
    'random_state': 42,
    'n_jobs': 1
}


def load_training_data(
    features_path: str,
    metadata_path: str
) -> (pd.DataFrame, pd.Series, Dict[str, Any]):
    logger.info('Loading training data from %s', features_path)
    df = pd.read_parquet(features_path)
    with open(metadata_path, 'r', encoding='utf-8') as metadata_file:
        metadata = json.load(metadata_file)
    feature_columns = metadata.get('feature_columns', [])
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f'{TARGET_COLUMN} is missing from training data')
    missing_features = [col for col in feature_columns if col not in df.columns]
    if missing_features:
        raise ValueError(f'Missing feature columns: {missing_features}')
    X = df[feature_columns]
    y = df[TARGET_COLUMN]
    logger.info('Loaded data with %d rows and %d features', len(df), len(feature_columns))
    return X, y, feature_columns


def train_model(X: pd.DataFrame, y: pd.Series) -> Any:
    logger.info('Splitting data into train/test')
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        stratify=y,
        random_state=42
    )
    logger.info('Training rows: %d, Test rows: %d', len(X_train), len(X_test))

    model = RandomForestClassifier(
        n_estimators=HYPERPARAMETERS['n_estimators'],
        max_depth=HYPERPARAMETERS['max_depth'],
        min_samples_split=HYPERPARAMETERS['min_samples_split'],
        min_samples_leaf=HYPERPARAMETERS['min_samples_leaf'],
        class_weight=HYPERPARAMETERS['class_weight'],
        random_state=HYPERPARAMETERS['random_state'],
        n_jobs=HYPERPARAMETERS['n_jobs']
    )
    logger.info('Training RandomForestClassifier')
    model.fit(X_train, y_train)
    logger.info('Model training complete')
    return model, X_train, X_test, y_train, y_test


def evaluate_model(model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
    logger.info('Evaluating model on test data')
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
    recall = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
    f1 = f1_score(y_test, y_pred, pos_label=1, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred).tolist()
    report_str = classification_report(y_test, y_pred, digits=4)

    logger.info('Accuracy: %.4f', accuracy)
    logger.info('Precision (failure): %.4f', precision)
    logger.info('Recall (failure): %.4f', recall)
    logger.info('F1 Score (failure): %.4f', f1)
    logger.info('ROC AUC: %.4f', roc_auc)
    logger.info('Confusion matrix: %s', cm)

    return {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'roc_auc': float(roc_auc),
        'confusion_matrix': cm,
        'classification_report': report_str
    }


def get_feature_importances(model: Any, feature_columns: Any) -> Dict[str, float]:
    importances = model.feature_importances_
    feature_importances = {
        feature: float(importance)
        for feature, importance in zip(feature_columns, importances)
    }
    sorted_importances = dict(
        sorted(feature_importances.items(), key=lambda item: item[1], reverse=True)
    )
    logger.info('Computed feature importances')
    return sorted_importances


def save_model(model: Any, model_path: str) -> None:
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    logger.info('Saved model to %s', model_path)


def save_metadata(
    metadata_path: str,
    feature_columns: Any,
    training_rows: int,
    test_rows: int,
    metrics: Dict[str, Any],
    feature_importances: Dict[str, float]
) -> None:
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    metadata = {
        'model_type': 'RandomForestClassifier',
        'training_date': datetime.utcnow().isoformat() + 'Z',
        'training_rows': training_rows,
        'test_rows': test_rows,
        'feature_columns': feature_columns,
        'target_column': TARGET_COLUMN,
        'hyperparameters': {
            'n_estimators': HYPERPARAMETERS['n_estimators'],
            'max_depth': HYPERPARAMETERS['max_depth'],
            'min_samples_split': HYPERPARAMETERS['min_samples_split'],
            'min_samples_leaf': HYPERPARAMETERS['min_samples_leaf'],
            'class_weight': HYPERPARAMETERS['class_weight'],
            'random_state': HYPERPARAMETERS['random_state']
        },
        'metrics': {
            'accuracy': metrics['accuracy'],
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'f1_score': metrics['f1_score'],
            'roc_auc': metrics['roc_auc'],
            'confusion_matrix': metrics['confusion_matrix']
        },
        'feature_importances': feature_importances
    }
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    logger.info('Saved training metadata to %s', metadata_path)


def train_pipeline() -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        'training_rows': 0,
        'test_rows': 0,
        'accuracy': 0.0,
        'precision': 0.0,
        'recall': 0.0,
        'f1_score': 0.0,
        'roc_auc': 0.0,
        'confusion_matrix': [[0, 0], [0, 0]],
        'feature_importances': {},
        'model_saved': False,
        'metadata_saved': False,
        'log_file_created': os.path.exists('logs/ml.log'),
        'recall_target_met': False,
        'f1_target_met': False,
        'roc_auc_target_met': False,
        'errors': []
    }

    try:
        X, y, feature_columns = load_training_data(RAW_FEATURES_PATH, FEATURE_METADATA_PATH)
        model, X_train, X_test, y_train, y_test = train_model(X, y)
        summary['training_rows'] = len(X_train)
        summary['test_rows'] = len(X_test)

        metrics = evaluate_model(model, X_test, y_test)
        summary.update({
            'accuracy': metrics['accuracy'],
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'f1_score': metrics['f1_score'],
            'roc_auc': metrics['roc_auc'],
            'confusion_matrix': metrics['confusion_matrix']
        })

        feature_importances = get_feature_importances(model, feature_columns)
        summary['feature_importances'] = feature_importances

        save_model(model, MODEL_PATH)
        summary['model_saved'] = True

        save_metadata(
            METADATA_OUTPUT_PATH,
            feature_columns,
            summary['training_rows'],
            summary['test_rows'],
            metrics,
            feature_importances
        )
        summary['metadata_saved'] = True

        summary['recall_target_met'] = metrics['recall'] > 0.70
        summary['f1_target_met'] = metrics['f1_score'] > 0.50
        summary['roc_auc_target_met'] = metrics['roc_auc'] > 0.85

    except Exception as exc:
        error_message = str(exc)
        summary['errors'].append(error_message)
        logger.error('Training pipeline failed: %s', error_message)

    return summary


if __name__ == '__main__':
    result = train_pipeline()
    print('TRAINING_RESULT:', result)
