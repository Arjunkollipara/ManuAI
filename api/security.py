"""Environment settings and security validation helpers."""

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger("api.security")


ALL_SETTINGS_KEYS = [
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_SQL_CONNECTION_STRING",
    "AZURE_AI_SEARCH_KEY",
    "AZURE_AI_SEARCH_ENDPOINT",
    "AZURE_AI_SEARCH_INDEX",
    "AZURE_KEY_VAULT_URL",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_TENANT_ID",
    "ENVIRONMENT",
    "DATABASE_URL",
    "LOG_LEVEL",
    "API_VERSION",
]

SENSITIVE_KEYS = {
    "AZURE_OPENAI_KEY",
    "AZURE_SQL_CONNECTION_STRING",
    "AZURE_AI_SEARCH_KEY",
    "AZURE_CLIENT_SECRET",
}


def _mask_value(key: str, value: str | None) -> str | None:
    if value is None:
        return None
    if key in SENSITIVE_KEYS:
        return "***"
    return value


def _is_present(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    normalized = value.strip().lower()
    placeholder_tokens = ("your_", "your-", "your.", "<", ">")
    return not any(token in normalized for token in placeholder_tokens)


def get_settings() -> dict:
    """Read environment variables, mask secrets in logs, and validate required keys."""
    load_dotenv(override=False)

    settings = {key: os.getenv(key) for key in ALL_SETTINGS_KEYS}
    environment = settings.get("ENVIRONMENT") or "development"

    required = ["ENVIRONMENT", "DATABASE_URL", "AZURE_OPENAI_KEY", "AZURE_OPENAI_ENDPOINT"]
    if environment == "production":
        required.extend(["AZURE_SQL_CONNECTION_STRING", "AZURE_AI_SEARCH_KEY"])

    missing_required = [key for key in required if not _is_present(settings.get(key))]

    masked_for_logs = {key: _mask_value(key, value) for key, value in settings.items()}
    logger.info("Loaded environment settings (masked): %s", masked_for_logs)
    logger.info("Environment validation missing_required=%s", missing_required)

    return {
        "settings": settings,
        "validation": {
            "required": required,
            "missing_required": missing_required,
            "is_valid": len(missing_required) == 0,
        },
    }


def validate_environment() -> dict:
    """Return high-level environment readiness status."""
    payload = get_settings()
    settings = payload["settings"]
    missing_required = payload["validation"]["missing_required"]
    environment = settings.get("ENVIRONMENT") or "development"

    database_configured = _is_present(settings.get("DATABASE_URL"))
    azure_openai_configured = _is_present(settings.get("AZURE_OPENAI_KEY")) and _is_present(
        settings.get("AZURE_OPENAI_ENDPOINT")
    )
    azure_search_configured = _is_present(settings.get("AZURE_AI_SEARCH_KEY")) and _is_present(
        settings.get("AZURE_AI_SEARCH_ENDPOINT")
    )
    azure_sql_configured = _is_present(settings.get("AZURE_SQL_CONNECTION_STRING"))
    key_vault_configured = _is_present(settings.get("AZURE_KEY_VAULT_URL")) and _is_present(
        settings.get("AZURE_CLIENT_ID")
    ) and _is_present(settings.get("AZURE_CLIENT_SECRET")) and _is_present(
        settings.get("AZURE_TENANT_ID")
    )

    if environment == "production":
        ready_for_production = (
            len(missing_required) == 0
            and azure_openai_configured
            and azure_search_configured
            and azure_sql_configured
            and key_vault_configured
        )
    else:
        ready_for_production = False

    return {
        "environment": environment,
        "database_configured": database_configured,
        "azure_openai_configured": azure_openai_configured,
        "azure_search_configured": azure_search_configured,
        "azure_sql_configured": azure_sql_configured,
        "key_vault_configured": key_vault_configured,
        "missing_required": missing_required,
        "ready_for_production": ready_for_production,
    }
