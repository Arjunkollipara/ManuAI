"""API routes for model prediction endpoints."""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from api.database.connection import get_db
from api.database import schemas
from api.models.sensor import SensorInput
from api.models.prediction import PredictionRequest, PredictionResponse, AlertResponse
from ml.predict import get_predictor

router = APIRouter()
logger = logging.getLogger("api.routes.predict")


@router.post("/failure", response_model=PredictionResponse, status_code=201)
def predict_failure(request: PredictionRequest, db: Session = Depends(get_db)):
    """
    Run prediction on sensor data.
    Optionally saves prediction record and creates alert if failure predicted.
    """
    try:
        logger.info(f"Running prediction for product {request.sensor_data.product_id}")
        
        # Run prediction
        predictor = get_predictor()
        sensor_dict = request.sensor_data.dict()
        prediction = predictor.predict(sensor_dict)
        
        prediction_id = None
        
        # Save to database if requested
        if request.save_to_db:
            # First save the prediction record
            pred_record = schemas.PredictionRecord(
                sensor_reading_id=None,  # No sensor reading associated in this flow
                failure_predicted=prediction["failure_predicted"],
                failure_probability=prediction["failure_probability"],
                risk_level=prediction["risk_level"],
                explanation=prediction["explanation"],
                top_features=str(prediction.get("top_contributing_features", []))
            )
            db.add(pred_record)
            db.commit()
            db.refresh(pred_record)
            prediction_id = pred_record.id
            logger.info(f"Prediction saved to DB: prediction_id={prediction_id}")
            
            # Create alert if failure predicted (now we have prediction_id)
            if prediction["failure_predicted"]:
                alert = schemas.AlertRecord(
                    prediction_id=pred_record.id,
                    machine_id=request.sensor_data.product_id or "UNKNOWN",
                    alert_type="PREDICTIVE_FAILURE",
                    severity=prediction["risk_level"],
                    message=prediction["explanation"],
                    resolved=False
                )
                db.add(alert)
                db.commit()
                logger.info(f"Alert created for failed prediction: prediction_id={prediction_id}")
        
        response = PredictionResponse(
            prediction_id=prediction_id,
            failure_predicted=prediction["failure_predicted"],
            failure_probability=prediction["failure_probability"],
            risk_level=prediction["risk_level"],
            explanation=prediction["explanation"],
            top_contributing_features=prediction.get("top_contributing_features", []),
            timestamp=datetime.utcnow()
        )
        
        logger.info(f"Prediction completed: failure={prediction['failure_predicted']}, risk={prediction['risk_level']}")
        return response
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error during prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/history")
def get_prediction_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get recent predictions from database."""
    try:
        logger.info(f"Fetching prediction history: limit={limit}, offset={offset}")
        
        predictions = db.query(schemas.PredictionRecord)\
            .order_by(schemas.PredictionRecord.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        logger.info(f"Retrieved {len(predictions)} predictions")
        return predictions
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching prediction history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


@router.get("/history/{prediction_id}")
def get_prediction_by_id(prediction_id: int, db: Session = Depends(get_db)):
    """Get a single prediction by ID."""
    try:
        logger.info(f"Fetching prediction: prediction_id={prediction_id}")
        
        prediction = db.query(schemas.PredictionRecord)\
            .filter(schemas.PredictionRecord.id == prediction_id)\
            .first()
        
        if not prediction:
            logger.warning(f"Prediction not found: prediction_id={prediction_id}")
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        return prediction
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching prediction by id: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch prediction: {str(e)}")


@router.post("/batch")
def batch_predict(
    sensor_readings: List[SensorInput],
    db: Session = Depends(get_db)
):
    """
    Run batch predictions on multiple sensor readings.
    Does NOT save to database (batch is for analysis only).
    Max 50 items per request.
    """
    try:
        if len(sensor_readings) > 50:
            raise HTTPException(status_code=422, detail="Maximum 50 items allowed per batch")
        
        logger.info(f"Running batch prediction: {len(sensor_readings)} items")
        
        predictor = get_predictor()
        # Convert SensorInput objects to dictionaries
        sensor_dicts = [sensor.dict() for sensor in sensor_readings]
        predictions = predictor.predict_batch(sensor_dicts)
        
        # Convert to response format
        responses = []
        for pred in predictions:
            response = PredictionResponse(
                prediction_id=None,
                failure_predicted=pred["failure_predicted"],
                failure_probability=pred["failure_probability"],
                risk_level=pred["risk_level"],
                explanation=pred["explanation"],
                top_contributing_features=pred.get("top_contributing_features", []),
                timestamp=datetime.utcnow()
            )
            responses.append(response)
        
        logger.info(f"Batch prediction completed: {len(responses)} predictions")
        return responses
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error during batch prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")


@router.get("/alerts")
def get_alerts(
    resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get alerts with optional filtering by resolved status and severity."""
    try:
        logger.info(f"Fetching alerts: resolved={resolved}, severity={severity}, limit={limit}")
        
        query = db.query(schemas.AlertRecord)
        
        if resolved is not None:
            query = query.filter(schemas.AlertRecord.resolved == resolved)
        
        if severity is not None:
            query = query.filter(schemas.AlertRecord.severity == severity)
        
        alerts = query.order_by(schemas.AlertRecord.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        logger.info(f"Retrieved {len(alerts)} alerts")
        return alerts
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {str(e)}")
