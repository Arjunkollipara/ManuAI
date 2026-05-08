"""
- Load raw CSV from data/raw/
- Validate that all required columns exist
- Validate row count is greater than 0
- Validate no fully empty rows
- Log every step with timestamps using Python logging module
- Save validated raw data as parquet to data/raw/ai4i2020.parquet
- Return a summary dict with: 
  rows_loaded, columns_found, missing_columns, validation_status
"""

import pandas as pd
import logging
import os
from typing import Dict, Any

logger = logging.getLogger('ingest')
if not logger.handlers:
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/pipeline.log', mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

REQUIRED_COLUMNS = [
    'UDI', 'Product ID', 'Type', 'Air temperature [K]', 
    'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 
    'Tool wear [min]', 'Machine failure', 'TWF', 'HDF', 'PWF', 'OSF', 'RNF'
]

def ingest_data(raw_csv_path: str, output_parquet_path: str) -> Dict[str, Any]:
    """
    Ingest data from CSV, validate, and save as Parquet.
    """
    logger.info(f"Starting ingestion from {raw_csv_path}")
    
    summary = {
        "rows_loaded": 0,
        "columns_found": 0,
        "missing_columns": [],
        "validation_status": "FAILED"
    }
    
    try:
        # Load raw CSV
        df = pd.read_csv(raw_csv_path)
        summary["rows_loaded"] = len(df)
        summary["columns_found"] = len(df.columns)
        logger.info(f"Loaded {len(df)} rows and {len(df.columns)} columns.")
        
        # Validate row count
        if len(df) == 0:
            logger.error("Validation failed: Row count is 0")
            return summary
            
        # Validate no fully empty rows
        if df.isnull().all(axis=1).any():
            logger.error("Validation failed: Found fully empty rows")
            return summary
            
        # Validate required columns
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            summary["missing_columns"] = missing_cols
            logger.error(f"Validation failed: Missing columns: {missing_cols}")
            return summary
            
        summary["missing_columns"] = "none"
        summary["validation_status"] = "PASSED"
        logger.info("Validation passed successfully.")
        
        # Save to parquet
        os.makedirs(os.path.dirname(output_parquet_path), exist_ok=True)
        df.to_parquet(output_parquet_path, index=False)
        logger.info(f"Saved validated raw data to {output_parquet_path}")
        
    except Exception as e:
        logger.error(f"Ingestion failed with error: {str(e)}")
        
    return summary

if __name__ == "__main__":
    result = ingest_data(
        raw_csv_path="data/raw/ai4i2020.csv",
        output_parquet_path="data/raw/ai4i2020.parquet"
    )
    print("INGESTION_RESULT:", result)
