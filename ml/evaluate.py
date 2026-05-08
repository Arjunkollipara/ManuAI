"""Script for evaluating trained machine learning models."""

import os
import json
import pickle
import logging
from typing import Any, Dict, List

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

logger = logging.getLogger('ml.evaluate')
if not logger.handlers:
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/ml.log', mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

TARGET_COLUMN = 'machine_failure'


def load_model(model_path: str) -> Any:
    logger.info('Loading model from %s', model_path)
    if not os.path.exists(model_path):
        logger.warning('Model file not found: %s (using heuristic fallback)', model_path)
        return None
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    logger.info('Model loaded successfully from %s', model_path)
    return model


def evaluate_model(model: Any, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
    logger.info('Evaluating model on provided dataset')
    y_pred = model.predict(X)
    if hasattr(model, 'predict_proba'):
        y_prob = model.predict_proba(X)[:, 1]
    else:
        logger.warning('Model has no predict_proba; using decision_function if available')
        if hasattr(model, 'decision_function'):
            scores = model.decision_function(X)
            y_prob = pd.Series(scores).rank(pct=True).to_numpy()
        else:
            y_prob = pd.Series(y_pred).astype(float).to_numpy()

    accuracy = float(accuracy_score(y, y_pred))
    precision = float(precision_score(y, y_pred, pos_label=1, zero_division=0))
    recall = float(recall_score(y, y_pred, pos_label=1, zero_division=0))
    f1 = float(f1_score(y, y_pred, pos_label=1, zero_division=0))
    roc_auc = float(roc_auc_score(y, y_prob))
    cm = confusion_matrix(y, y_pred).tolist()
    report_str = classification_report(y, y_pred, digits=4)

    logger.info('Evaluation metrics computed: accuracy=%.4f, precision=%.4f, recall=%.4f, f1=%.4f, roc_auc=%.4f',
                accuracy, precision, recall, f1, roc_auc)
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'roc_auc': roc_auc,
        'confusion_matrix': cm,
        'classification_report': report_str
    }


def get_feature_importance(model: Any, feature_columns: List[str]) -> Dict[str, float]:
    logger.info('Extracting feature importances')
    if not hasattr(model, 'feature_importances_'):
        message = 'Model does not expose feature_importances_'
        logger.error(message)
        raise AttributeError(message)
    importances = model.feature_importances_
    features = {
        feature: float(importance)
        for feature, importance in zip(feature_columns, importances)
    }
    sorted_features = dict(sorted(features.items(), key=lambda item: item[1], reverse=True))
    logger.info('Feature importances extracted')
    return sorted_features


def explain_prediction(model: Any, feature_columns: List[str], single_row_df: pd.DataFrame) -> Dict[str, Any]:
    logger.info('Explaining single prediction')
    if single_row_df.shape[0] != 1:
        raise ValueError('single_row_df must contain exactly one row')
    X = single_row_df[feature_columns]
    if model is None:
        failure_probability = float(X.get("failure_risk_score", pd.Series([0.0])).iloc[0])
        failure_predicted = failure_probability >= 0.5
    else:
        failure_predicted = bool(model.predict(X)[0])
        if hasattr(model, 'predict_proba'):
            failure_probability = float(model.predict_proba(X)[:, 1][0])
        else:
            failure_probability = float(model.predict(X)[0])

    if failure_probability < 0.30:
        risk_level = 'LOW'
    elif failure_probability < 0.60:
        risk_level = 'MEDIUM'
    elif failure_probability < 0.80:
        risk_level = 'HIGH'
    else:
        risk_level = 'CRITICAL'

    if model is None:
        top_contributing = []
        explanation = (
            f"Machine failure probability is {failure_probability * 100:.2f}% ({risk_level}). "
            "Heuristic fallback used because the trained model file is missing."
        )
    else:
        importances = get_feature_importance(model, feature_columns)
        feature_values = X.iloc[0].to_dict()
        sorted_importances = sorted(importances.items(), key=lambda item: item[1], reverse=True)
        top_contributing = []
        for feature, importance in sorted_importances[:3]:
            top_contributing.append({
                'feature': feature,
                'value': float(feature_values.get(feature, 0.0)),
                'importance': float(importance)
            })

        top_features_str = ', '.join([item['feature'] for item in top_contributing])
        explanation = (
            f"Machine failure probability is {failure_probability * 100:.2f}% ({risk_level}). "
            f"Primary contributing factors: {top_features_str}"
        )
    logger.info('Explanation generated with risk_level=%s probability=%.4f', risk_level, failure_probability)
    return {
        'failure_predicted': failure_predicted,
        'failure_probability': failure_probability,
        'risk_level': risk_level,
        'top_contributing_features': top_contributing,
        'explanation': explanation
    }


def run_full_evaluation(
    model_path: str,
    features_path: str,
    feature_metadata_path: str
) -> Dict[str, Any]:
    logger.info('Running full evaluation for model=%s', model_path)
    model = load_model(model_path)
    df = pd.read_parquet(features_path)
    with open(feature_metadata_path, 'r', encoding='utf-8') as metadata_file:
        metadata = json.load(metadata_file)
    feature_columns = metadata.get('feature_columns', [])
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f'{TARGET_COLUMN} missing from features data')
    X = df[feature_columns]
    y = df[TARGET_COLUMN]

    metrics = evaluate_model(model, X, y)
    feature_importances = get_feature_importance(model, feature_columns)
    report = {
        'model_path': model_path,
        'features_path': features_path,
        'feature_metadata_path': feature_metadata_path,
        'metrics': metrics,
        'feature_importances': feature_importances,
        'rows_evaluated': len(df)
    }
    os.makedirs(os.path.dirname('ml/models/evaluation_report.json'), exist_ok=True)
    with open('ml/models/evaluation_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    logger.info('Saved evaluation report to ml/models/evaluation_report.json')
    return report


if __name__ == '__main__':
    results = run_full_evaluation(
        model_path='ml/models/random_forest.pkl',
        features_path='data/curated/ai4i2020_features.parquet',
        feature_metadata_path='data/curated/feature_metadata.json'
    )
    print(json.dumps(results['metrics'], indent=2))
    print('\nTop 5 Features:')
    for feat, imp in list(results['feature_importances'].items())[:5]:
        print(f'  {feat}: {imp:.4f}')
