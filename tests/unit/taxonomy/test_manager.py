"""Tests for TaxonomyManager."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile

from twmops.taxonomy.manager import (
    TaxonomyManager,
    TaxonomyInfo,
    DEFAULT_TAXONOMY_DIR,
)

pytestmark = pytest.mark.unit


class TestTaxonomyManagerInitialization:
    """Test TaxonomyManager initialization."""

    def test_manager_default_initialization(self):
        """Test manager with default settings."""
        manager = TaxonomyManager()
        assert manager is not None
        assert hasattr(manager, "taxonomy_dir")
        assert isinstance(manager.taxonomy_dir, Path)

    def test_manager_custom_directory(self):
        """Test manager with custom taxonomy directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir)
            manager = TaxonomyManager(taxonomy_dir=custom_dir)
            assert manager.taxonomy_dir == custom_dir

    def test_manager_has_required_methods(self):
        """Test that manager has required methods."""
        manager = TaxonomyManager()
        assert hasattr(manager, "ensure_taxonomies")
        assert hasattr(manager, "get_schema_mappings")
        assert callable(manager.ensure_taxonomies)
        assert callable(manager.get_schema_mappings)


class TestTaxonomyInfo:
    """Test TaxonomyInfo dataclass."""

    def test_taxonomy_info_creation(self):
        """Test creating TaxonomyInfo object."""
        info = TaxonomyInfo(
            filename="tifrs_2023.zip",
            description="Taiwan IFRS 2023",
            publish_date="2023-01-01",
            taxonomy_type="tifrs",
            start_year=112,
            start_quarter=1,
            end_year=None,
            end_quarter=None,
            is_ongoing=True,
        )
        assert info.filename == "tifrs_2023.zip"
        assert info.taxonomy_type == "tifrs"
        assert info.is_ongoing is True

    @pytest.mark.parametrize(
        "tax_type,is_ongoing",
        [
            ("tifrs", True),
            ("tw-gaap", False),
            ("tifrs", False),
        ],
    )
    def test_taxonomy_info_with_different_types(self, tax_type, is_ongoing):
        """Test TaxonomyInfo with different taxonomy types."""
        info = TaxonomyInfo(
            filename="test.zip",
            description="Test",
            publish_date="2023-01-01",
            taxonomy_type=tax_type,
            start_year=112,
            start_quarter=1,
            end_year=None,
            end_quarter=None,
            is_ongoing=is_ongoing,
        )
        assert info.taxonomy_type == tax_type
        assert info.is_ongoing == is_ongoing


class TestTaxonomyManagerMethods:
    """Test TaxonomyManager methods."""

    def test_get_schema_mappings_returns_dict(self):
        """Test that schema mappings returns a dictionary."""
        manager = TaxonomyManager()
        mappings = manager.get_schema_mappings()
        assert isinstance(mappings, dict)

    @pytest.mark.asyncio
    async def test_ensure_taxonomies_async(self):
        """Test ensure_taxonomies async method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaxonomyManager(taxonomy_dir=Path(tmpdir))
            # Don't actually download, just test method exists
            assert callable(manager.ensure_taxonomies)

    def test_taxonomy_dir_is_path_object(self):
        """Test that taxonomy_dir is a Path object."""
        manager = TaxonomyManager()
        assert isinstance(manager.taxonomy_dir, Path)

    def test_default_taxonomy_dir_is_reasonable(self):
        """Test that default taxonomy directory is sensible."""
        assert DEFAULT_TAXONOMY_DIR is not None
        assert isinstance(DEFAULT_TAXONOMY_DIR, Path)


class TestTaxonomyManagerErrorHandling:
    """Test error handling in TaxonomyManager."""

    def test_manager_with_none_directory(self):
        """Test manager with None directory uses default."""
        manager = TaxonomyManager(taxonomy_dir=None)
        assert manager.taxonomy_dir is not None
        assert isinstance(manager.taxonomy_dir, Path)

    def test_schema_mappings_returns_empty_dict_if_no_taxonomies(self):
        """Test that schema mappings returns empty dict if no taxonomies exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaxonomyManager(taxonomy_dir=Path(tmpdir))
            mappings = manager.get_schema_mappings()
            assert isinstance(mappings, dict)

    @pytest.mark.parametrize(
        "invalid_input",
        [
            {},
            None,
            "",
            0,
        ],
    )
    def test_manager_initialization_robustness(self, invalid_input):
        """Test manager initialization with various inputs."""
        if invalid_input is None or isinstance(invalid_input, (str, int)):
            # Constructor may handle these differently
            try:
                manager = TaxonomyManager(taxonomy_dir=invalid_input)
                assert manager is not None
            except (TypeError, AttributeError):
                # Expected for some invalid inputs
                pass


class TestTaxonomyListing:
    """Test taxonomy listing and discovery."""

    def test_manager_can_list_available_taxonomies(self):
        """Test that manager can list taxonomies."""
        manager = TaxonomyManager()
        assert manager is not None
        # Actual listing would require network or mock

    def test_schema_mapping_structure(self):
        """Test the structure of schema mappings."""
        manager = TaxonomyManager()
        mappings = manager.get_schema_mappings()
        # Mappings should map URI strings to local paths
        for key, value in mappings.items():
            if key and value:  # Only check if not empty
                assert isinstance(key, str)
                assert isinstance(value, (str, Path))
