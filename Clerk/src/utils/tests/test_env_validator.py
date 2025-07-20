"""
Unit tests for environment validator.
"""

import os
import pytest
from unittest.mock import patch

from src.utils.env_validator import (
    validate_required_services,
    validate_all,
    get_environment_info,
    EnvironmentError,
)


class TestRequiredServicesValidation:
    """Test validation of required services"""

    def test_validate_required_services_success(self):
        """Test successful validation of all required services"""
        with patch.dict(
            os.environ,
            {
                "BOX_CLIENT_ID": "test-client-id",
                "BOX_CLIENT_SECRET": "test-client-secret",
                "BOX_ENTERPRISE_ID": "test-enterprise-id",
                "QDRANT_HOST": "qdrant",
                "OPENAI_API_KEY": "test-openai-key",
            },
        ):
            # Should not raise any exception
            validate_required_services()

    def test_validate_required_services_missing_box(self):
        """Test validation fails when Box configuration is incomplete"""
        with patch.dict(
            os.environ,
            {
                "BOX_CLIENT_ID": "test-client-id",
                # Missing BOX_CLIENT_SECRET and BOX_ENTERPRISE_ID
                "QDRANT_HOST": "qdrant",
                "OPENAI_API_KEY": "test-openai-key",
            },
        ):
            with pytest.raises(EnvironmentError) as exc_info:
                validate_required_services()
            assert "Box API configuration incomplete" in str(exc_info.value)

    def test_validate_required_services_missing_qdrant(self):
        """Test validation fails when Qdrant host is missing"""
        with patch.dict(
            os.environ,
            {
                "BOX_CLIENT_ID": "test-client-id",
                "BOX_CLIENT_SECRET": "test-client-secret",
                "BOX_ENTERPRISE_ID": "test-enterprise-id",
                # Missing QDRANT_HOST
                "OPENAI_API_KEY": "test-openai-key",
            },
        ):
            with pytest.raises(EnvironmentError) as exc_info:
                validate_required_services()
            assert "QDRANT_HOST not configured" in str(exc_info.value)

    def test_validate_required_services_missing_openai(self):
        """Test validation fails when OpenAI key is missing"""
        with patch.dict(
            os.environ,
            {
                "BOX_CLIENT_ID": "test-client-id",
                "BOX_CLIENT_SECRET": "test-client-secret",
                "BOX_ENTERPRISE_ID": "test-enterprise-id",
                "QDRANT_HOST": "qdrant",
                # Missing OPENAI_API_KEY
            },
        ):
            with pytest.raises(EnvironmentError) as exc_info:
                validate_required_services()
            assert "OPENAI_API_KEY not configured" in str(exc_info.value)


class TestEnvironmentInfo:
    """Test environment info retrieval"""

    def test_get_environment_info_with_values(self):
        """Test getting environment info with all values set"""
        with patch.dict(
            os.environ,
            {
                "BOX_CLIENT_ID": "box123456",
                "BOX_ENTERPRISE_ID": "enterprise123",
                "QDRANT_HOST": "qdrant",
                "QDRANT_PORT": "6333",
                "OPENAI_API_KEY": "sk-test123456789",
                "CONTEXT_LLM_MODEL": "gpt-4",
            },
        ):
            info = get_environment_info()

            assert info["box"]["client_id"] == "box1...3456"  # Masked
            assert info["box"]["enterprise_id"] == "enterprise123"
            assert info["qdrant"]["host"] == "qdrant"
            assert info["qdrant"]["port"] == "6333"
            assert info["openai"]["api_key"] == "sk-t...6789"  # Masked
            assert info["openai"]["model"] == "gpt-4"

    def test_get_environment_info_missing_values(self):
        """Test getting environment info with missing values"""
        with patch.dict(os.environ, {}, clear=True):
            info = get_environment_info()

            assert info["box"]["client_id"] == "NOT SET"
            assert info["qdrant"]["host"] == "NOT SET"
            assert info["openai"]["api_key"] == "NOT SET"

    def test_get_environment_info_short_values(self):
        """Test masking of short values"""
        with patch.dict(os.environ, {"BOX_CLIENT_ID": "tiny"}):
            info = get_environment_info()

            assert info["box"]["client_id"] == "***"  # Short value masked


class TestValidateAll:
    """Test complete validation flow"""

    def test_validate_all_success(self):
        """Test successful complete validation"""
        with patch.dict(
            os.environ,
            {
                "BOX_CLIENT_ID": "test-client-id",
                "BOX_CLIENT_SECRET": "test-client-secret",
                "BOX_ENTERPRISE_ID": "test-enterprise-id",
                "QDRANT_HOST": "qdrant",
                "OPENAI_API_KEY": "test-openai-key",
            },
        ):
            # Should not raise any exception
            validate_all()

    def test_validate_all_services_failure(self):
        """Test validation fails when required services are missing"""
        with patch.dict(
            os.environ,
            {
                # Missing required services
            },
        ):
            with pytest.raises(EnvironmentError) as exc_info:
                validate_all()
            assert "Environment validation failed" in str(exc_info.value)

    def test_validate_all_handles_unexpected_error(self):
        """Test validation handles unexpected errors gracefully"""
        with patch(
            "src.utils.env_validator.validate_required_services"
        ) as mock_validate:
            mock_validate.side_effect = ValueError("Unexpected error")

            with pytest.raises(EnvironmentError) as exc_info:
                validate_all()
            assert "Unexpected error during environment validation" in str(
                exc_info.value
            )
