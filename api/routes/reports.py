"""Reporting endpoints for Power BI and operational exports."""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.database.connection import get_db, get_database_dialect
from api.database import schemas
from api.models.reporting import ReportingExportResponse, ReportingSummary

router = APIRouter()
logger = logging.getLogger("api.routes.reports")

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def _build_reporting_frame(db: Session) -> pd.DataFrame:
    readings = db.query(schemas.SensorReading).all()
    predictions = db.query(schemas.PredictionRecord).all()
    alerts = db.query(schemas.AlertRecord).all()
    machine_by_reading_id = {item.id: item.product_id for item in readings}

    reading_rows = [
        {
            "record_type": "sensor_reading",
            "record_id": item.id,
            "machine_id": item.product_id,
            "type": item.type,
            "air_temp_k": item.air_temp_k,
            "process_temp_k": item.process_temp_k,
            "rotational_speed_rpm": item.rotational_speed_rpm,
            "torque_nm": item.torque_nm,
            "tool_wear_min": item.tool_wear_min,
            "failure_flag": item.machine_failure,
            "created_at": item.created_at,
        }
        for item in readings
    ]

    prediction_rows = [
        {
            "record_type": "prediction",
            "record_id": item.id,
            "sensor_reading_id": item.sensor_reading_id,
            "machine_id": machine_by_reading_id.get(item.sensor_reading_id),
            "failure_predicted": item.failure_predicted,
            "failure_probability": item.failure_probability,
            "risk_level": item.risk_level,
            "explanation": item.explanation,
            "created_at": item.created_at,
        }
        for item in predictions
    ]

    alert_rows = [
        {
            "record_type": "alert",
            "record_id": item.id,
            "prediction_id": item.prediction_id,
            "machine_id": item.machine_id,
            "severity": item.severity,
            "message": item.message,
            "resolved": item.resolved,
            "created_at": item.created_at,
        }
        for item in alerts
    ]

    return pd.DataFrame(reading_rows + prediction_rows + alert_rows)


@router.get("/summary", response_model=ReportingSummary)
def reporting_summary(db: Session = Depends(get_db)):
    """Return a Power BI friendly summary snapshot."""
    try:
        total_readings = db.query(schemas.SensorReading).count()
        total_predictions = db.query(schemas.PredictionRecord).count()
        total_alerts = db.query(schemas.AlertRecord).count()
        high_risk_count = db.query(schemas.AlertRecord).filter(schemas.AlertRecord.severity == "HIGH").count()
        critical_risk_count = db.query(schemas.AlertRecord).filter(schemas.AlertRecord.severity == "CRITICAL").count()
        last_reading = db.query(schemas.SensorReading).order_by(schemas.SensorReading.created_at.desc()).first()
        failure_rate = (total_alerts / total_readings * 100) if total_readings else 0.0
        return ReportingSummary(
            generated_at=datetime.utcnow(),
            database_dialect=get_database_dialect(),
            total_readings=total_readings,
            total_predictions=total_predictions,
            total_alerts=total_alerts,
            failure_rate_percent=round(failure_rate, 2),
            high_risk_count=high_risk_count,
            critical_risk_count=critical_risk_count,
            last_ingested=last_reading.created_at.isoformat() + "Z" if last_reading else None,
        )
    except Exception as exc:
        logger.error("Reporting summary failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to build reporting summary: {exc}")


@router.get("/power-bi")
def power_bi_dataset(
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    """Return an exportable reporting dataset for Power BI."""
    try:
        frame = _build_reporting_frame(db)
        export_path = REPORT_DIR / f"powerbi_dataset.{format}"

        if format == "csv":
            frame.to_csv(export_path, index=False)
            return FileResponse(export_path, media_type="text/csv", filename=export_path.name)

        export_path.write_text(frame.to_json(orient="records", date_format="iso"), encoding="utf-8")
        return ReportingExportResponse(
            status="SUCCESS",
            format="json",
            generated_at=datetime.utcnow(),
            rows=int(len(frame)),
            path=str(export_path),
            preview=frame.head(10).fillna("").to_dict(orient="records"),
        )
    except Exception as exc:
        logger.error("Power BI export failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to build Power BI export: {exc}")


@router.get("/power-bi/export")
def power_bi_export_csv(db: Session = Depends(get_db)):
    """Shortcut for CSV export."""
    return power_bi_dataset(format="csv", db=db)
