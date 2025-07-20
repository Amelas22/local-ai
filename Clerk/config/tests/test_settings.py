"""
Tests for configuration settings
"""

import os
from unittest.mock import patch
from config.settings import DiscoveryProcessingSettings, Settings


class TestDiscoveryProcessingSettings:
    """Test discovery processing settings configuration."""

    def test_enable_deficiency_analysis_default(self):
        """Test that enable_deficiency_analysis defaults to False."""
        settings = DiscoveryProcessingSettings()
        assert settings.enable_deficiency_analysis is False

    @patch.dict(os.environ, {"DISCOVERY_ENABLE_DEFICIENCY_ANALYSIS": "true"})
    def test_enable_deficiency_analysis_from_env(self):
        """Test loading enable_deficiency_analysis from environment variable."""
        settings = DiscoveryProcessingSettings()
        assert settings.enable_deficiency_analysis is True

    @patch.dict(os.environ, {"DISCOVERY_ENABLE_DEFICIENCY_ANALYSIS": "false"})
    def test_enable_deficiency_analysis_false_from_env(self):
        """Test loading false value from environment variable."""
        settings = DiscoveryProcessingSettings()
        assert settings.enable_deficiency_analysis is False

    @patch.dict(os.environ, {"DISCOVERY_ENABLE_DEFICIENCY_ANALYSIS": "1"})
    def test_enable_deficiency_analysis_numeric_true(self):
        """Test loading numeric true value from environment variable."""
        settings = DiscoveryProcessingSettings()
        assert settings.enable_deficiency_analysis is True

    @patch.dict(os.environ, {"DISCOVERY_ENABLE_DEFICIENCY_ANALYSIS": "0"})
    def test_enable_deficiency_analysis_numeric_false(self):
        """Test loading numeric false value from environment variable."""
        settings = DiscoveryProcessingSettings()
        assert settings.enable_deficiency_analysis is False


class TestSettingsConfigSummary:
    """Test main settings configuration summary."""

    def test_config_summary_includes_deficiency_analysis(self):
        """Test that config summary includes deficiency analysis status."""
        settings = Settings()
        summary = settings.get_config_summary()

        assert "deficiency_analysis_enabled" in summary
        assert isinstance(summary["deficiency_analysis_enabled"], bool)
        assert summary["deficiency_analysis_enabled"] is False  # Default value

    @patch.dict(os.environ, {"DISCOVERY_ENABLE_DEFICIENCY_ANALYSIS": "true"})
    def test_config_summary_with_enabled_deficiency_analysis(self):
        """Test config summary when deficiency analysis is enabled."""
        settings = Settings()
        summary = settings.get_config_summary()

        assert summary["deficiency_analysis_enabled"] is True
