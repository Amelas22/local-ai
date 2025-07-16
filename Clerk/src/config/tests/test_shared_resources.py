"""
Tests for Shared Resources Configuration.
Tests shared resource identification and filtering.
"""

import os
from unittest.mock import patch

from src.config.shared_resources import (
    is_shared_resource,
    get_shared_collections,
    add_shared_collection,
    remove_shared_collection,
    filter_case_specific_collections,
    SharedResourceConfig,
    shared_resources,
    SHARED_COLLECTIONS,
)


class TestIsSharedResource:
    """Test shared resource identification"""

    def test_exact_match_shared_resource(self):
        """Test exact match for shared resources"""
        # Default shared resources
        assert is_shared_resource("florida_statutes") is True
        assert is_shared_resource("fmcsr_regulations") is True
        assert is_shared_resource("federal_rules") is True
        assert is_shared_resource("case_law_precedents") is True

    def test_case_insensitive_matching(self):
        """Test case insensitive matching"""
        assert is_shared_resource("FLORIDA_STATUTES") is True
        assert is_shared_resource("Florida_Statutes") is True
        assert is_shared_resource("florida_STATUTES") is True

    def test_non_shared_resources(self):
        """Test non-shared resources"""
        assert is_shared_resource("smith_v_jones_2024") is False
        assert is_shared_resource("case_specific_collection") is False
        assert is_shared_resource("my_custom_case") is False

    def test_empty_or_none_input(self):
        """Test empty or None input"""
        assert is_shared_resource("") is False
        assert is_shared_resource(None) is False
        assert is_shared_resource("   ") is False

    def test_whitespace_handling(self):
        """Test whitespace handling"""
        assert is_shared_resource("  florida_statutes  ") is True
        assert is_shared_resource("florida_statutes\n") is True
        assert is_shared_resource("\tflorida_statutes") is True

    @patch("src.config.shared_resources.is_shared_resource.cache_clear")
    def test_cache_functionality(self, mock_cache_clear):
        """Test that function is cached"""
        # Multiple calls with same input
        is_shared_resource("test_resource")
        is_shared_resource("test_resource")
        is_shared_resource("test_resource")

        # Cache should not be cleared
        mock_cache_clear.assert_not_called()


class TestGetSharedCollections:
    """Test getting list of shared collections"""

    def test_returns_sorted_list(self):
        """Test that function returns sorted list"""
        collections = get_shared_collections()

        assert isinstance(collections, list)
        assert len(collections) >= 4  # At least default collections
        assert collections == sorted(collections)

    def test_contains_default_collections(self):
        """Test that default collections are included"""
        collections = get_shared_collections()

        assert "florida_statutes" in collections
        assert "fmcsr_regulations" in collections
        assert "federal_rules" in collections
        assert "case_law_precedents" in collections


class TestAddRemoveSharedCollection:
    """Test adding and removing shared collections"""

    def teardown_method(self):
        """Clean up after each test"""
        # Reset to default state
        SHARED_COLLECTIONS.discard("test_collection")
        SHARED_COLLECTIONS.discard("another_test")
        is_shared_resource.cache_clear()

    def test_add_shared_collection(self):
        """Test adding a new shared collection"""
        initial_count = len(get_shared_collections())

        add_shared_collection("test_collection")

        assert is_shared_resource("test_collection") is True
        assert len(get_shared_collections()) == initial_count + 1
        assert "test_collection" in get_shared_collections()

    def test_add_shared_collection_normalized(self):
        """Test that added collections are normalized"""
        add_shared_collection("  TEST_COLLECTION  ")

        assert is_shared_resource("test_collection") is True
        assert is_shared_resource("TEST_COLLECTION") is True
        assert "test_collection" in get_shared_collections()

    def test_add_empty_collection(self):
        """Test adding empty collection name"""
        initial_count = len(get_shared_collections())

        add_shared_collection("")
        add_shared_collection(None)

        assert len(get_shared_collections()) == initial_count

    def test_remove_shared_collection(self):
        """Test removing a shared collection"""
        add_shared_collection("test_collection")
        assert is_shared_resource("test_collection") is True

        remove_shared_collection("test_collection")

        assert is_shared_resource("test_collection") is False
        assert "test_collection" not in get_shared_collections()

    def test_remove_nonexistent_collection(self):
        """Test removing a non-existent collection"""
        initial_collections = get_shared_collections()

        remove_shared_collection("nonexistent_collection")

        assert get_shared_collections() == initial_collections

    @patch("src.config.shared_resources.is_shared_resource.cache_clear")
    def test_cache_cleared_on_modification(self, mock_cache_clear):
        """Test that cache is cleared when collections are modified"""
        add_shared_collection("test_collection")
        assert mock_cache_clear.call_count == 1

        remove_shared_collection("test_collection")
        assert mock_cache_clear.call_count == 2


class TestFilterCaseSpecificCollections:
    """Test filtering case-specific collections"""

    def test_filter_excludes_shared(self):
        """Test filtering excludes shared resources by default"""
        all_collections = [
            "florida_statutes",
            "smith_v_jones_2024",
            "fmcsr_regulations",
            "doe_v_roe_2023",
            "federal_rules",
        ]

        filtered = filter_case_specific_collections(all_collections)

        assert len(filtered) == 2
        assert "smith_v_jones_2024" in filtered
        assert "doe_v_roe_2023" in filtered
        assert "florida_statutes" not in filtered

    def test_filter_includes_shared_when_requested(self):
        """Test filtering includes shared when requested"""
        all_collections = [
            "florida_statutes",
            "smith_v_jones_2024",
            "fmcsr_regulations",
        ]

        filtered = filter_case_specific_collections(
            all_collections, include_shared=True
        )

        assert filtered == all_collections

    def test_filter_empty_list(self):
        """Test filtering empty list"""
        filtered = filter_case_specific_collections([])
        assert filtered == []

    def test_filter_all_shared(self):
        """Test filtering when all collections are shared"""
        all_collections = ["florida_statutes", "fmcsr_regulations", "federal_rules"]

        filtered = filter_case_specific_collections(all_collections)

        assert filtered == []


class TestSharedResourceConfig:
    """Test SharedResourceConfig class"""

    def test_is_shared_method(self):
        """Test is_shared method"""
        config = SharedResourceConfig()

        assert config.is_shared("florida_statutes") is True
        assert config.is_shared("custom_case") is False

    def test_get_all_shared_method(self):
        """Test get_all_shared method"""
        config = SharedResourceConfig()
        collections = config.get_all_shared()

        assert isinstance(collections, list)
        assert "florida_statutes" in collections

    def test_contains_operator(self):
        """Test __contains__ operator support"""
        config = SharedResourceConfig()

        assert "florida_statutes" in config
        assert "custom_case" not in config

    def test_config_attributes(self):
        """Test config attributes"""
        config = SharedResourceConfig()

        assert hasattr(config, "collections")
        assert hasattr(config, "patterns")
        assert isinstance(config.collections, set)
        assert isinstance(config.patterns, list)


class TestEnvironmentConfiguration:
    """Test environment-based configuration"""

    @patch.dict(os.environ, {"SHARED_COLLECTIONS": "custom1,custom2,custom3"})
    def test_custom_env_collections(self):
        """Test loading collections from environment variable"""
        # Need to reload module to pick up env changes
        import importlib
        import src.config.shared_resources

        importlib.reload(src.config.shared_resources)

        from src.config.shared_resources import is_shared_resource

        assert is_shared_resource("custom1") is True
        assert is_shared_resource("custom2") is True
        assert is_shared_resource("custom3") is True

    @patch.dict(os.environ, {"SHARED_COLLECTIONS": "  spaces_test  ,  another_test  "})
    def test_env_collections_whitespace_handling(self):
        """Test that env collections handle whitespace properly"""
        import importlib
        import src.config.shared_resources

        importlib.reload(src.config.shared_resources)

        from src.config.shared_resources import is_shared_resource

        assert is_shared_resource("spaces_test") is True
        assert is_shared_resource("another_test") is True


class TestGlobalInstance:
    """Test global shared_resources instance"""

    def test_global_instance_exists(self):
        """Test that global instance is available"""
        assert shared_resources is not None
        assert isinstance(shared_resources, SharedResourceConfig)

    def test_global_instance_functionality(self):
        """Test global instance functionality"""
        assert shared_resources.is_shared("florida_statutes") is True
        assert "florida_statutes" in shared_resources
        assert len(shared_resources.get_all_shared()) >= 4
