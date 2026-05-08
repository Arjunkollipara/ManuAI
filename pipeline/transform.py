"""Handles data transformation and cleaning from raw to staged layer."""

import os
import json
import logging
from typing import Dict, Any

import pandas as pd

logger = logging.getLogger('transform')
if not logger.handlers:
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/pipeline.log', mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

COLUMN_RENAME_MAP = {
    'UDI': 'udi',
    'Product ID': 'product_id',
    'Type': 'type',
    'Air temperature [K]': 'air_temp_k',
    'Process temperature [K]': 'process_temp_k',
    'Rotational speed [rpm]': 'rotational_speed_rpm',
    'Torque [Nm]': 'torque_nm',
    'Tool wear [min]': 'tool_wear_min',
    'Machine failure': 'machine_failure',
    'TWF': 'twf',
    'HDF': 'hdf',
    'PWF': 'pwf',
    'OSF': 'osf',
    'RNF': 'rnf'
}

EXPECTED_COLUMNS = [
    'udi', 'product_id', 'type', 'air_temp_k', 'process_temp_k',
    'rotational_speed_rpm', 'torque_nm', 'tool_wear_min', 'machine_failure',
    'twf', 'hdf', 'pwf', 'osf', 'rnf'
]

RANGE_CHECKS = {
    'air_temp_k': (290, 320),
    'process_temp_k': (300, 330),
    'rotational_speed_rpm': (500, 3000),
    'torque_nm': (0, 100),
    'tool_wear_min': (0, 300)
}


def standardize_column_name(column_name: str) -> str:
    clean_name = column_name.strip()
    if clean_name in COLUMN_RENAME_MAP:
        return COLUMN_RENAME_MAP[clean_name]
    return clean_name.strip().replace(' ', '_').lower()


def transform_data(
    input_parquet_path: str,
    output_parquet_path: str,
    quality_report_path: str
) -> Dict[str, Any]:
    logger.info('Starting transformation from %s', input_parquet_path)

    summary = {
        'rows_input': 0,
        'duplicate_rows_removed': 0,
        'nulls_filled': {},
        'range_violations': {},
        'flagged_rows': 0,
        'clean_rows': 0,
        'staged_parquet_saved': False,
        'quality_report_saved': False,
        'validation_status': 'FAILED',
        'errors': []
    }

    try:
        df = pd.read_parquet(input_parquet_path)
        summary['rows_input'] = len(df)
        logger.info('Loaded %d rows from %s', len(df), input_parquet_path)

        # Drop fully duplicate rows
        duplicate_count = len(df) - len(df.drop_duplicates())
        df = df.drop_duplicates().reset_index(drop=True)
        summary['duplicate_rows_removed'] = duplicate_count
        logger.info('Removed %d fully duplicate rows', duplicate_count)

        # Standardize and rename columns
        rename_map = {col: standardize_column_name(col) for col in df.columns}
        df = df.rename(columns=rename_map)
        logger.info('Standardized column names: %s', list(df.columns))

        # Validate expected columns exist after rename
        missing_columns = [col for col in EXPECTED_COLUMNS if col not in df.columns]
        if missing_columns:
            summary['errors'].append(f'Missing expected columns after rename: {missing_columns}')
            logger.error('Missing expected columns after rename: %s', missing_columns)

        # Handle missing values
        null_counts = df.isnull().sum()
        nulls_filled: Dict[str, int] = {}
        for column, null_count in null_counts.items():
            if null_count == 0:
                continue
            if pd.api.types.is_numeric_dtype(df[column]):
                fill_value = df[column].median()
            else:
                mode_values = df[column].mode(dropna=True)
                fill_value = mode_values.iloc[0] if len(mode_values) > 0 else ''
            df[column] = df[column].fillna(fill_value)
            nulls_filled[column] = int(null_count)
            logger.info('Filled %d nulls in column %s', null_count, column)

        summary['nulls_filled'] = nulls_filled
        if not nulls_filled:
            logger.info('No null values required filling')

        # Confirm no nulls remain
        remaining_nulls = df.isnull().sum()
        if remaining_nulls.any():
            nulls_left = remaining_nulls[remaining_nulls > 0].to_dict()
            summary['errors'].append(f'Nulls remain after fill: {nulls_left}')
            logger.error('Nulls remain after fill: %s', nulls_left)

        # Confirm machine_failure only contains 0 and 1
        if 'machine_failure' in df.columns:
            invalid_machine_failure = ~df['machine_failure'].isin([0, 1])
            invalid_count = int(invalid_machine_failure.sum())
            if invalid_count > 0:
                summary['errors'].append('machine_failure contains values outside 0 and 1')
                logger.error('machine_failure contains %d invalid values', invalid_count)
        else:
            invalid_count = 0

        # Range validation and data quality flagging
        violation_counts: Dict[str, int] = {}
        flags = pd.Series(0, index=df.index)
        for column, (low, high) in RANGE_CHECKS.items():
            if column not in df.columns:
                violation_counts[column] = 0
                continue
            out_of_range = ~df[column].between(low, high)
            count = int(out_of_range.sum())
            violation_counts[column] = count
            if count > 0:
                logger.warning('Found %d range violations in column %s', count, column)
            flags = flags | out_of_range.astype(int)

        df['data_quality_flag'] = flags.astype(int)
        summary['range_violations'] = violation_counts
        summary['flagged_rows'] = int(flags.sum())
        summary['clean_rows'] = int(len(df) - summary['flagged_rows'])
        logger.info('Flagged %d rows with data quality issues', summary['flagged_rows'])

        # Final validation status
        summary['validation_status'] = 'PASSED' if not summary['errors'] else 'FAILED'

        # Save staged parquet and quality report
        os.makedirs(os.path.dirname(output_parquet_path), exist_ok=True)
        df.to_parquet(output_parquet_path, index=False)
        summary['staged_parquet_saved'] = True
        logger.info('Saved staged parquet to %s', output_parquet_path)

        os.makedirs(os.path.dirname(quality_report_path), exist_ok=True)
        quality_report = {
            'total_rows': summary['rows_input'] - summary['duplicate_rows_removed'],
            'duplicate_rows_removed': summary['duplicate_rows_removed'],
            'nulls_filled': summary['nulls_filled'],
            'range_violations': summary['range_violations'],
            'flagged_rows': summary['flagged_rows'],
            'clean_rows': summary['clean_rows'],
            'validation_status': summary['validation_status']
        }
        with open(quality_report_path, 'w', encoding='utf-8') as report_file:
            json.dump(quality_report, report_file, indent=2)
        summary['quality_report_saved'] = True
        logger.info('Saved quality report to %s', quality_report_path)

    except Exception as exc:
        error_message = str(exc)
        summary['errors'].append(error_message)
        logger.error('Transformation failed with error: %s', error_message)

    return summary


if __name__ == '__main__':
    result = transform_data(
        input_parquet_path='data/raw/ai4i2020.parquet',
        output_parquet_path='data/staged/ai4i2020_staged.parquet',
        quality_report_path='data/staged/quality_report.json'
    )
    print('TRANSFORM_RESULT:', result)
