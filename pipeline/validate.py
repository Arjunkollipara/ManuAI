"""Validates data quality and integrity at different pipeline stages."""

import os
import json
import logging
from datetime import datetime
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger('validate')
if not logger.handlers:
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/pipeline.log', mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

RAW_PARQUET = 'data/raw/ai4i2020.parquet'
STAGED_PARQUET = 'data/staged/ai4i2020_staged.parquet'
CURATED_PARQUET = 'data/curated/ai4i2020_curated.parquet'
FEATURES_PARQUET = 'data/curated/ai4i2020_features.parquet'
FEATURE_METADATA = 'data/curated/feature_metadata.json'
QUALITY_REPORT = 'data/staged/quality_report.json'
VALIDATION_REPORT = 'data/curated/validation_report.json'
LOG_FILE = 'logs/pipeline.log'
TARGET_COLUMN = 'machine_failure'


def file_existence_check() -> Dict[str, Any]:
    logger.info('Running file existence check')
    files = [
        RAW_PARQUET,
        STAGED_PARQUET,
        CURATED_PARQUET,
        FEATURES_PARQUET,
        FEATURE_METADATA,
        QUALITY_REPORT,
        LOG_FILE
    ]
    missing = [path for path in files if not os.path.exists(path)]
    status = 'PASSED' if not missing else 'FAILED'
    details = 'all files exist' if not missing else f'missing files: {missing}'
    logger.info('File existence check status=%s details=%s', status, details)
    return {'status': status, 'details': details}


def load_parquet_safe(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return pd.read_parquet(path)


def row_consistency_check() -> Dict[str, Any]:
    logger.info('Running row consistency check')
    details = []
    status = 'PASSED'
    counts = {'raw': None, 'staged': None, 'curated': None}
    try:
        raw_df = load_parquet_safe(RAW_PARQUET)
        staged_df = load_parquet_safe(STAGED_PARQUET)
        curated_df = load_parquet_safe(CURATED_PARQUET)
        counts['raw'] = len(raw_df)
        counts['staged'] = len(staged_df)
        counts['curated'] = len(curated_df)
        if counts['raw'] != counts['staged'] or counts['staged'] != counts['curated']:
            status = 'WARNING'
            details.append(f'raw={counts["raw"]} staged={counts["staged"]} curated={counts["curated"]}')
        else:
            details.append(f'raw={counts["raw"]} staged={counts["staged"]} curated={counts["curated"]}')
    except Exception as exc:
        status = 'FAILED'
        details.append(str(exc))
        logger.error('Row consistency check failed: %s', exc)
    logger.info('Row consistency check status=%s details=%s', status, details)
    return {'status': status, 'details': '; '.join(details), 'counts': counts}


def feature_completeness_check() -> Dict[str, Any]:
    logger.info('Running feature completeness check')
    status = 'PASSED'
    details = []
    try:
        with open(FEATURE_METADATA, 'r', encoding='utf-8') as metadata_file:
            metadata = json.load(metadata_file)
        expected_features = metadata.get('feature_columns', [])
        df = load_parquet_safe(FEATURES_PARQUET)
        expected_columns = expected_features + [TARGET_COLUMN]
        found_columns = list(df.columns)
        missing = [col for col in expected_columns if col not in found_columns]
        extra = [col for col in found_columns if col not in expected_columns]
        if missing:
            status = 'FAILED'
            details.append(f'missing columns: {missing}')
        else:
            details.append(f'found {len(expected_columns)} expected feature columns')
        logger.info('Feature completeness check missing=%s extra=%s', missing, extra)
    except Exception as exc:
        status = 'FAILED'
        details.append(str(exc))
        logger.error('Feature completeness check failed: %s', exc)
    return {'status': status, 'details': '; '.join(details)}


def target_integrity_check() -> Dict[str, Any]:
    logger.info('Running target integrity check')
    status = 'PASSED'
    details = []
    try:
        df = load_parquet_safe(FEATURES_PARQUET)
        if TARGET_COLUMN not in df.columns:
            raise ValueError(f'{TARGET_COLUMN} missing from features file')
        series = df[TARGET_COLUMN]
        null_count = int(series.isnull().sum())
        unique_values = sorted(series.dropna().unique().tolist())
        positive_rate = float((series == 1).sum() / len(series) * 100) if len(series) else 0.0
        if null_count > 0:
            status = 'FAILED'
            details.append(f'{TARGET_COLUMN} has {null_count} nulls')
        if any(val not in [0, 1] for val in unique_values):
            status = 'FAILED'
            details.append(f'{TARGET_COLUMN} contains values outside 0 and 1: {unique_values}')
        if positive_rate < 1.0:
            status = 'FAILED'
            details.append(f'{TARGET_COLUMN} positive rate below 1%: {positive_rate:.2f}%')
        details.append(f'failure rate: {positive_rate:.2f}%')
        logger.info('Target integrity values=%s positive_rate=%.2f nulls=%d', unique_values, positive_rate, null_count)
    except Exception as exc:
        status = 'FAILED'
        details.append(str(exc))
        logger.error('Target integrity check failed: %s', exc)
    return {'status': status, 'details': '; '.join(details)}


def feature_sanity_check() -> Dict[str, Any]:
    logger.info('Running feature sanity check')
    status = 'PASSED'
    details = []
    try:
        df = load_parquet_safe(FEATURES_PARQUET)
        total_rows = len(df)
        zero_columns = [col for col in df.columns if col != TARGET_COLUMN and df[col].fillna(0).eq(0).all()]
        if zero_columns:
            status = 'WARNING'
            details.append(f'columns entirely zero: {zero_columns}')
        null_counts = df.isnull().sum()
        null_issues = [col for col, count in null_counts.items() if count / total_rows > 0.05]
        if null_issues:
            status = 'WARNING'
            details.append(f'columns >5% nulls: {null_issues}')
        if 'failure_risk_score' in df.columns:
            out_of_range = df[~df['failure_risk_score'].between(0, 1)]
            count = len(out_of_range)
            if count > 0:
                status = 'WARNING'
                details.append(f'failure_risk_score out of [0,1] for {count} rows')
        logger.info('Feature sanity zero_columns=%s null_issues=%s', zero_columns, null_issues)
    except Exception as exc:
        status = 'WARNING'
        details.append(str(exc))
        logger.error('Feature sanity check failed: %s', exc)
    return {'status': status, 'details': '; '.join(details)}


def log_integrity_check() -> Dict[str, Any]:
    logger.info('Running log integrity check')
    status = 'PASSED'
    details = []
    try:
        if not os.path.exists(LOG_FILE):
            raise FileNotFoundError(LOG_FILE)
        with open(LOG_FILE, 'r', encoding='utf-8') as log_file:
            content = log_file.read().lower()
        needs = {
            'ingest': 'ingest',
            'transform': 'transform',
            'feature': 'feature'
        }
        missing = [name for name, token in needs.items() if token not in content]
        if missing:
            status = 'WARNING'
            details.append(f'missing log mentions: {missing}')
        else:
            details.append('all pipeline stage mentions found')
        logger.info('Log integrity missing=%s', missing)
    except Exception as exc:
        status = 'WARNING'
        details.append(str(exc))
        logger.error('Log integrity check failed: %s', exc)
    return {'status': status, 'details': '; '.join(details)}


def build_validation_report() -> Dict[str, Any]:
    logger.info('Building validation report')
    checks = {
        'file_existence': file_existence_check(),
        'row_consistency': row_consistency_check(),
        'feature_completeness': feature_completeness_check(),
        'target_integrity': target_integrity_check(),
        'feature_sanity': feature_sanity_check(),
        'log_integrity': log_integrity_check()
    }
    overall_status = 'PASSED'
    for check_name, check_data in checks.items():
        if check_data['status'] == 'FAILED':
            overall_status = 'FAILED'
            break
    ready_for_ml = overall_status == 'PASSED'
    report = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': checks,
        'overall_status': overall_status,
        'ready_for_ml': ready_for_ml
    }
    os.makedirs(os.path.dirname(VALIDATION_REPORT), exist_ok=True)
    with open(VALIDATION_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    logger.info('Saved validation report to %s', VALIDATION_REPORT)
    return report


def print_report(report: Dict[str, Any]) -> None:
    print('VALIDATION REPORT')
    print('=================')
    file_status = report['checks']['file_existence']['status']
    row_data = report['checks']['row_consistency']['details']
    feature_status = report['checks']['feature_completeness']['status']
    target_status = report['checks']['target_integrity']['status']
    feature_sanity_status = report['checks']['feature_sanity']['status']
    log_status = report['checks']['log_integrity']['status']
    failure_rate = 'unknown'
    target_details = report['checks']['target_integrity']['details']
    if 'failure rate:' in target_details.lower():
        failure_rate = target_details.lower().split('failure rate:')[-1].strip().split('%')[0] + '%'
    print(f'File existence: {file_status}')
    print(f'Row consistency: {report["checks"]["row_consistency"]["status"]} - {row_data}')
    print(f'Feature completeness: {feature_status} - {report["checks"]["feature_completeness"]["details"]}')
    print(f'Target integrity: {target_status} - {target_details}')
    print(f'Feature sanity: {feature_sanity_status}')
    print(f'Log integrity: {log_status}')
    print(f'Validation report saved: yes')
    print(f'Overall status: {report["overall_status"]}')
    print(f'Ready for ML: {str(report["ready_for_ml"]).lower()}')
    errors = []
    for check_data in report['checks'].values():
        if check_data['status'] == 'FAILED':
            errors.append(check_data['details'])
    print(f'Errors encountered: {errors if errors else "none"}')
    print(f'Status: {"COMPLETE" if report["overall_status"] == "PASSED" else "NEEDS ATTENTION"}')


if __name__ == '__main__':
    report = build_validation_report()
    print_report(report)
