"""
Environment variable validation utility for Clerk.
Validates required configuration on startup.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class EnvironmentError(Exception):
    """Raised when environment validation fails"""
    pass


def validate_supabase_config() -> None:
    """
    Validate Supabase configuration on startup.
    
    Raises:
        EnvironmentError: If required variables are missing or invalid
    """
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    missing = []
    
    # Check for required variables
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        error_msg = f"Missing required environment variables: {missing}"
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
    
    # Validate URL format
    url = os.getenv('SUPABASE_URL', '')
    if not url.startswith(('http://', 'https://')):
        error_msg = f"Invalid SUPABASE_URL format: {url}. Must start with http:// or https://"
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
    
    # Try to parse the URL
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError("URL has no network location")
    except Exception as e:
        error_msg = f"Invalid SUPABASE_URL format: {url}. Error: {str(e)}"
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
    
    # Validate key format (should be a JWT token)
    anon_key = os.getenv('SUPABASE_ANON_KEY', '')
    if len(anon_key) < 50:  # JWT tokens are typically much longer
        error_msg = f"SUPABASE_ANON_KEY appears to be invalid (too short). Length: {len(anon_key)}"
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
    
    # Check optional but recommended variables
    optional_vars = {
        'SUPABASE_SERVICE_ROLE_KEY': 'Recommended for server-side operations',
        'SUPABASE_JWT_SECRET': 'Recommended for JWT verification'
    }
    
    for var, description in optional_vars.items():
        if not os.getenv(var):
            logger.warning(f"{var} not set. {description}")
    
    logger.info("Supabase configuration validated successfully")


def validate_required_services() -> None:
    """
    Validate all required service configurations.
    
    Raises:
        EnvironmentError: If required configurations are missing
    """
    errors = []
    
    # Validate Box API configuration
    box_vars = ['BOX_CLIENT_ID', 'BOX_CLIENT_SECRET', 'BOX_ENTERPRISE_ID']
    missing_box = [var for var in box_vars if not os.getenv(var)]
    if missing_box:
        errors.append(f"Box API configuration incomplete. Missing: {missing_box}")
    
    # Validate Qdrant configuration
    if not os.getenv('QDRANT_HOST'):
        errors.append("QDRANT_HOST not configured")
    
    # Validate OpenAI configuration
    if not os.getenv('OPENAI_API_KEY'):
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
        "supabase": {
            "url": os.getenv('SUPABASE_URL', 'NOT SET'),
            "anon_key": mask_value(os.getenv('SUPABASE_ANON_KEY')),
            "service_role_key": mask_value(os.getenv('SUPABASE_SERVICE_ROLE_KEY')),
            "jwt_secret": mask_value(os.getenv('SUPABASE_JWT_SECRET'))
        },
        "box": {
            "client_id": mask_value(os.getenv('BOX_CLIENT_ID')),
            "enterprise_id": os.getenv('BOX_ENTERPRISE_ID', 'NOT SET')
        },
        "qdrant": {
            "host": os.getenv('QDRANT_HOST', 'NOT SET'),
            "port": os.getenv('QDRANT_PORT', '6333')
        },
        "openai": {
            "api_key": mask_value(os.getenv('OPENAI_API_KEY')),
            "model": os.getenv('CONTEXT_LLM_MODEL', 'NOT SET')
        }
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
        # Validate Supabase first as it's critical for case management
        validate_supabase_config()
        
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