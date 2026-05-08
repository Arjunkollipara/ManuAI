"""ML insight agent and tools for prediction explainability."""

import logging
import json

from ml.evaluate import get_feature_importance
from ml.predict import get_predictor

logger = logging.getLogger("agents.ml_insight_agent")


def create_ml_insight_agent(llm):
    from crewai import Agent
    from crewai_tools import tool

    @tool("get_feature_importance")
    def get_feature_importance_tool(input: str = "") -> str:
        """Get the importance of each sensor feature in predicting machine failure."""
        try:
            predictor = get_predictor()
            importance = get_feature_importance(predictor.model, predictor.feature_columns)
            top_features = dict(list(importance.items())[:5])
            return json.dumps(top_features)
        except Exception as exc:
            logger.error("Feature importance tool failed: %s", exc)
            return json.dumps({"error": str(exc)})

    @tool("predict_failure_risk")
    def predict_failure_risk_tool(sensor_json: str) -> str:
        """Predict failure risk for given sensor readings.
        Input must be JSON with keys: type, air_temp_k, process_temp_k, rotational_speed_rpm, torque_nm, tool_wear_min
        """
        try:
            sensor_data = json.loads(sensor_json)
            predictor = get_predictor()
            result = predictor.predict(sensor_data)
            return json.dumps(
                {
                    "failure_predicted": result["failure_predicted"],
                    "probability": result["failure_probability"],
                    "risk_level": result["risk_level"],
                    "explanation": result["explanation"],
                }
            )
        except Exception as e:
            logger.error("Predict failure risk tool failed: %s", e)
            return json.dumps({"error": str(e)})

    return Agent(
        role="ML Systems Analyst",
        goal="""Explain machine learning predictions in
                plain language, identify which sensor
                readings are driving failure risk, and
                provide technical explanations""",
        backstory="""You are an ML engineer specializing
                in industrial predictive maintenance
                models. You bridge the gap between
                complex model outputs and actionable
                technician guidance.""",
        tools=[get_feature_importance_tool, predict_failure_risk_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
