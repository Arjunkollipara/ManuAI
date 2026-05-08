"""API routes for data ingestion endpoints."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from api.database.connection import get_db
from api.database import schemas
from api.models.sensor import SensorInput, SensorResponse
from api.models.prediction import PredictionResponse
from ml.predict import get_predictor

router = APIRouter()
logger = logging.getLogger("api.routes.ingest")


@router.post("/sensor-data", status_code=201)
def ingest_sensor_data(sensor: SensorInput, db: Session = Depends(get_db)):
    """
    Ingest sensor data and automatically check for risks.
    Creates a prediction record and alert if risk level is HIGH or CRITICAL.
    """
    try:
        logger.info(f"Ingesting sensor data for product {sensor.product_id}")
        
        # Run prediction first to determine machine_failure value
        predictor = get_predictor()
        sensor_dict = sensor.dict()
        prediction = predictor.predict(sensor_dict)
        
        # Convert failure_predicted to integer (0 or 1)
        machine_failure = 1 if prediction["failure_predicted"] else 0
        
        # Save sensor reading to database with predicted failure status
        sensor_record = schemas.SensorReading(
            udi=sensor.udi,
            product_id=sensor.product_id,
            type=sensor.type,
            air_temp_k=sensor.air_temp_k,
            process_temp_k=sensor.process_temp_k,
            rotational_speed_rpm=sensor.rotational_speed_rpm,
            torque_nm=sensor.torque_nm,
            tool_wear_min=sensor.tool_wear_min,
            machine_failure=machine_failure
        )
        db.add(sensor_record)
        db.commit()
        db.refresh(sensor_record)
        logger.info(f"Sensor reading saved: sensor_id={sensor_record.id}, machine_failure={machine_failure}")
        
        # Save prediction record linked to sensor reading
        pred_record = schemas.PredictionRecord(
            sensor_reading_id=sensor_record.id,
            failure_predicted=prediction["failure_predicted"],
            failure_probability=prediction["failure_probability"],
            risk_level=prediction["risk_level"],
            explanation=prediction["explanation"],
            top_features=str(prediction.get("top_contributing_features", []))
        )
        db.add(pred_record)
        db.commit()
        db.refresh(pred_record)
        logger.info(f"Prediction record saved: prediction_id={pred_record.id}")
        
        alert_created = False
        alert_severity = None
        
        # Create alert if high risk
        if prediction["risk_level"] in ["HIGH", "CRITICAL"]:
            alert = schemas.AlertRecord(
                prediction_id=pred_record.id,
                machine_id=sensor.product_id or "UNKNOWN",
                alert_type="PREDICTIVE_FAILURE",
                severity=prediction["risk_level"],
                message=prediction["explanation"],
                resolved=False
            )
            db.add(alert)
            db.commit()
            alert_created = True
            alert_severity = prediction["risk_level"]
            logger.info(f"Alert created for product {sensor.product_id} with severity {alert_severity}")
        
        logger.info(f"Sensor data ingested successfully, sensor_id={sensor_record.id}")
        
        return {
            "message": "Sensor data ingested successfully",
            "sensor_id": sensor_record.id,
            "alert_created": alert_created,
            "alert_severity": alert_severity,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting sensor data: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/sensor-data")
def get_sensor_data(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get list of sensor readings with pagination."""
    try:
        logger.info(f"Fetching sensor data: limit={limit}, offset={offset}")
        
        readings = db.query(schemas.SensorReading)\
            .order_by(schemas.SensorReading.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        logger.info(f"Retrieved {len(readings)} sensor readings")
        
        return readings
    
    except Exception as e:
        logger.error(f"Error fetching sensor data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sensor data: {str(e)}")


@router.get("/sensor-data/{sensor_id}")
def get_sensor_by_id(sensor_id: int, db: Session = Depends(get_db)):
    """Get a single sensor reading by ID."""
    try:
        logger.info(f"Fetching sensor data for sensor_id={sensor_id}")
        
        reading = db.query(schemas.SensorReading)\
            .filter(schemas.SensorReading.id == sensor_id)\
            .first()
        
        if not reading:
            logger.warning(f"Sensor reading not found: sensor_id={sensor_id}")
            raise HTTPException(status_code=404, detail="Sensor reading not found")
        
        return reading
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching sensor by id: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sensor: {str(e)}")


@router.get("/stats")
def get_ingestion_stats(db: Session = Depends(get_db)):
    """Get ingestion statistics."""
    try:
        logger.info("Fetching ingestion statistics")
        
        total_readings = db.query(schemas.SensorReading).count()
        total_alerts = db.query(schemas.AlertRecord).count()
        high_risk = db.query(schemas.AlertRecord)\
            .filter(schemas.AlertRecord.severity == "HIGH").count()
        critical_risk = db.query(schemas.AlertRecord)\
            .filter(schemas.AlertRecord.severity == "CRITICAL").count()
        
        # Calculate failure rate from alerts
        failure_rate = (total_alerts / total_readings * 100) if total_readings > 0 else 0.0
        
        # Get last ingested timestamp
        last_reading = db.query(schemas.SensorReading)\
            .order_by(schemas.SensorReading.created_at.desc())\
            .first()
        last_ingested = last_reading.created_at.isoformat() + "Z" if last_reading else None
        
        stats = {
            "total_readings": total_readings,
            "total_alerts": total_alerts,
            "failure_rate_percent": round(failure_rate, 2),
            "high_risk_count": high_risk,
            "critical_risk_count": critical_risk,
            "last_ingested": last_ingested
        }
        
        logger.info(f"Ingestion stats: {stats}")
        return stats
    
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")
