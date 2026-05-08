"""SQLAlchemy schemas representing database tables."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from .connection import Base


class SensorReading(Base):
    __tablename__ = 'sensor_readings'

    id = Column(Integer, primary_key=True, index=True)
    udi = Column(Integer, index=True)
    product_id = Column(String(20), nullable=True)
    type = Column(String(1), nullable=False)
    air_temp_k = Column(Float, nullable=False)
    process_temp_k = Column(Float, nullable=False)
    rotational_speed_rpm = Column(Integer, nullable=False)
    torque_nm = Column(Float, nullable=False)
    tool_wear_min = Column(Integer, nullable=False)
    machine_failure = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PredictionRecord(Base):
    __tablename__ = 'prediction_records'

    id = Column(Integer, primary_key=True, index=True)
    sensor_reading_id = Column(Integer, ForeignKey('sensor_readings.id'), nullable=True)
    failure_predicted = Column(Boolean, nullable=False)
    failure_probability = Column(Float, nullable=False)
    risk_level = Column(String(10), nullable=False)
    explanation = Column(Text, nullable=False)
    top_features = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AlertRecord(Base):
    __tablename__ = 'alert_records'

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey('prediction_records.id'), nullable=False)
    machine_id = Column(String(20), nullable=False)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MaintenanceLog(Base):
    __tablename__ = 'maintenance_logs'

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String(20), nullable=False)
    action_taken = Column(Text, nullable=False)
    technician_notes = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
