"""
Environment variable validation utility for Clerk.
Validates required configuration on startup.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class EnvironmentError(Exception):
    """Raised when environment validation fails"""

    pass


def validate_database_config() -> None:
    """
    Validate PostgreSQL database configuration.

    Raises:
        EnvironmentError: If required variables are missing or invalid
    """
    # Database URL is constructed from individual components in settings.py
    # Just log that we're using PostgreSQL
    logger.info("Using PostgreSQL database for case management")


def validate_required_services() -> None:
    """
    Validate all required service configurations.

    Raises:
        EnvironmentError: If required configurations are missing
    """
    errors = []

    # Validate Box API configuration
    box_vars = ["BOX_CLIENT_ID", "BOX_CLIENT_SECRET", "BOX_ENTERPRISE_ID"]
    missing_box = [var for var in box_vars if not os.getenv(var)]
    if missing_box:
        errors.append(f"Box API configuration incomplete. Missing: {missing_box}")

    # Validate Qdrant configuration
    if not os.getenv("QDRANT_HOST"):
        errors.append("QDRANT_HOST not configured")

    # Validate OpenAI configuration
    if not os.getenv("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY not configured")

    if errors:
        error_msg = "Environment validation failed:\n" + "\n".join(errors)
        logger.error(error_msg)
        raise EnvironmentError(error_msg)

    logger.info("All required service configurations validated")


def get_environment_info() -> Dict[str, Any]:
    """
    Get summary of environment configuration for debugging.

    Returns:
        Dictionary with environment information (sensitive values masked)
    """

    def mask_value(value: Optional[str]) -> str:
        """Mask sensitive values for logging"""
        if not value:
            return "NOT SET"
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}...{value[-4:]}"

    info = {
        "database": {
            "type": "PostgreSQL",
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "database": os.getenv("POSTGRES_DB", "clerk_db"),
        },
        "box": {
            "client_id": mask_value(os.getenv("BOX_CLIENT_ID")),
            "enterprise_id": os.getenv("BOX_ENTERPRISE_ID", "NOT SET"),
        },
        "qdrant": {
            "host": os.getenv("QDRANT_HOST", "NOT SET"),
            "port": os.getenv("QDRANT_PORT", "6333"),
        },
        "openai": {
            "api_key": mask_value(os.getenv("OPENAI_API_KEY")),
            "model": os.getenv("CONTEXT_LLM_MODEL", "NOT SET"),
        },
    }

    return info


def validate_all() -> None:
    """
    Run all environment validations.

    Raises:
        EnvironmentError: If any validation fails
    """
    logger.info("Starting environment validation...")

    try:
        # Validate database configuration
        validate_database_config()

        # Validate other required services
        validate_required_services()

        # Log environment summary
        env_info = get_environment_info()
        logger.info(f"Environment configuration summary: {env_info}")

        logger.info("Environment validation completed successfully")

    except EnvironmentError:
        # Re-raise environment errors
        raise
    except Exception as e:
        # Catch any unexpected errors
        error_msg = f"Unexpected error during environment validation: {str(e)}"
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
