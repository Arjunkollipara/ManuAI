"""Main entry point for the FastAPI application."""

import os
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.database.connection import engine, Base
from api.security import validate_environment
from ml.predict import get_predictor
from api.routes import ingest, predict, search, agent, reports

LOG_FILE = 'logs/api.log'

logger = logging.getLogger('api.main')
logger.setLevel(logging.INFO)
if not logger.handlers:
    os.makedirs('logs', exist_ok=True)
    handler = logging.FileHandler(LOG_FILE, mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = FastAPI(
    title='Manufacturing Quality & Productivity Suite',
    version='1.0.0',
    description='AI-powered predictive maintenance and manufacturing intelligence platform'
)
app.state.startup_complete = False
app.state.environment_status = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)


@app.on_event('startup')
def startup_event():
    try:
        env_status = validate_environment()
        app.state.environment_status = env_status
        logger.info("Environment: %s", env_status["environment"])
        logger.info("Azure OpenAI: %s", env_status["azure_openai_configured"])
        logger.info("Azure Search: %s", env_status["azure_search_configured"])

        # Force import all table models so SQLAlchemy registers them
        from api.database.schemas import (
            SensorReading, 
            PredictionRecord, 
            AlertRecord, 
            MaintenanceLog
        )
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info('Database tables created successfully')
        
        # Initialize ML model singleton (optional for UI demo)
        try:
            predictor = get_predictor()
            app.state.model_predictor = predictor
            logger.info('ModelPredictor initialized successfully')
        except Exception as model_err:
            app.state.model_predictor = None
            logger.warning("ModelPredictor unavailable: %s", model_err)

        app.state.startup_complete = True
        logger.info('Application startup complete')
        
    except Exception as e:
        logger.error(f'Startup failed (continuing in degraded mode): {e}')
        app.state.model_predictor = None
        app.state.startup_complete = False


@app.on_event('shutdown')
def shutdown_event():
    logger.info('Application shutdown')


@app.get('/')
def root():
    return RedirectResponse(url="/ui/")


@app.get('/health')
def health_check():
    database_status = 'connected'
    database_ready = True
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
    except SQLAlchemyError as db_err:
        database_status = 'degraded'
        database_ready = False
        logger.warning('Database health check failed: %s', db_err)
    except Exception as db_err:
        database_status = 'degraded'
        database_ready = False
        logger.warning('Database health check failed: %s', db_err)

    startup_complete = getattr(app.state, 'startup_complete', False)
    payload = {
        'version': '1.0.0',
        'model_loaded': getattr(app.state, 'model_predictor', None) is not None,
        'database': database_status,
        'startup_complete': startup_complete,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    if not startup_complete or not database_ready:
        payload['status'] = 'degraded'
        return JSONResponse(status_code=503, content=payload)

    payload['status'] = 'healthy'
    return payload


@app.get('/system/config')
def system_config():
    """Return environment and service configuration readiness."""
    cached = getattr(app.state, "environment_status", None)
    return cached if cached else validate_environment()


app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')
app.mount('/ui', StaticFiles(directory=FRONTEND_DIR, html=True), name='ui')


@app.get('/ui', include_in_schema=False)
def serve_ui():
    return RedirectResponse(url='/ui/')

app.include_router(ingest.router, prefix='/ingest', tags=['Ingestion'])
app.include_router(predict.router, prefix='/predict', tags=['Prediction'])
app.include_router(search.router, prefix='/search', tags=['Search'])
app.include_router(agent.router, prefix='/agent', tags=['Agent'])
app.include_router(reports.router, prefix='/reports', tags=['Reporting'])
