"""Analytics agent and tools for production insight queries."""

import logging
import json

from api.database.connection import SessionLocal
from api.database.schemas import AlertRecord, PredictionRecord, SensorReading

logger = logging.getLogger("agents.analytics_agent")


def create_analytics_agent(llm):
    from crewai import Agent
    from crewai_tools import tool

    @tool("get_production_stats")
    def get_production_stats_tool(input: str = "") -> str:
        """Get current production statistics including total readings, failure rates, and alert counts."""
        db = SessionLocal()
        try:
            total = db.query(SensorReading).count()
            alerts = db.query(AlertRecord).count()
            predictions = db.query(PredictionRecord).count()
            failures = db.query(PredictionRecord).filter(
                PredictionRecord.failure_predicted.is_(True)
            ).count()
            rate = (failures / predictions * 100) if predictions > 0 else 0
            return json.dumps(
                {
                    "total_sensor_readings": total,
                    "total_predictions": predictions,
                    "total_alerts": alerts,
                    "failure_predictions": failures,
                    "failure_rate_percent": round(rate, 2),
                }
            )
        except Exception as exc:
            logger.error("Production stats tool failed: %s", exc)
            return json.dumps({"error": str(exc)})
        finally:
            db.close()

    @tool("get_recent_alerts")
    def get_recent_alerts_tool(limit: str = "5") -> str:
        """Get recent machine alerts and their details."""
        db = SessionLocal()
        try:
            safe_limit = max(1, min(25, int(limit)))
            alerts = db.query(AlertRecord).order_by(AlertRecord.created_at.desc()).limit(
                safe_limit
            ).all()
            result = [
                {
                    "machine_id": a.machine_id,
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "message": a.message,
                    "resolved": a.resolved,
                    "created_at": str(a.created_at),
                }
                for a in alerts
            ]
            return json.dumps(result)
        except Exception as exc:
            logger.error("Recent alerts tool failed: %s", exc)
            return json.dumps({"error": str(exc)})
        finally:
            db.close()

    return Agent(
        role="Manufacturing Analytics Specialist",
        goal="""Analyse production data, identify trends,
                explain anomalies, and provide actionable
                operational insights""",
        backstory="""You are a data-driven manufacturing
                analyst with deep expertise in production
                optimization and OEE (Overall Equipment
                Effectiveness). You translate raw metrics
                into clear business insights.""",
        tools=[get_production_stats_tool, get_recent_alerts_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
