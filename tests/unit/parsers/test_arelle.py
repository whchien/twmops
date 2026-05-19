"""Tests for Arelle-based XBRL extraction."""
import pytest
from unittest.mock import Mock, MagicMock, patch

from twmops.parsers.arelle import (
    check_arelle_available,
    extract_calculation_arcs,
    extract_presentation_arcs,
    extract_facts,
    extract_contexts,
    extract_labels,
)

pytestmark = pytest.mark.unit


class TestArelleFunctionality:
    """Test Arelle helper functions."""

    def test_check_arelle_available(self):
        """Test Arelle availability check."""
        result = check_arelle_available()
        assert isinstance(result, bool)

    def test_extract_calculation_arcs_with_empty_model(self):
        """Test extraction with empty model."""
        mock_model = Mock()
        mock_model.relationshipSet.return_value = Mock(modelRelationships=[])

        result = extract_calculation_arcs(mock_model)
        assert isinstance(result, dict)

    def test_extract_presentation_arcs_with_empty_model(self):
        """Test extraction with empty model."""
        mock_model = Mock()
        mock_model.relationshipSet.return_value = Mock(modelRelationships=[])

        result = extract_presentation_arcs(mock_model)
        assert isinstance(result, dict)

    def test_extract_facts_returns_list(self):
        """Test that extract_facts returns a list."""
        mock_model = Mock()
        result = extract_facts(mock_model)
        assert isinstance(result, list)

    def test_extract_contexts_returns_dict(self):
        """Test that extract_contexts returns a dictionary."""
        mock_model = Mock()
        result = extract_contexts(mock_model)
        assert isinstance(result, dict)

    def test_extract_labels_returns_tuple(self):
        """Test that extract_labels returns a tuple."""
        mock_model = Mock()
        result = extract_labels(mock_model)
        assert isinstance(result, tuple)
        assert len(result) == 2  # Returns (labels_dict, labels_en_dict)


class TestArcelleErrorHandling:
    """Test error handling in Arelle extraction."""

    def test_extract_arcs_handles_errors_gracefully(self):
        """Test that arc extraction handles errors gracefully."""
        mock_model = Mock()
        mock_model.relationshipSet.side_effect = Exception("Test error")

        # Should not raise, should return empty dict
        result = extract_calculation_arcs(mock_model)
        assert isinstance(result, dict)

    def test_extract_calculation_arcs_with_invalid_model(self):
        """Test extraction with invalid model object."""
        result = extract_calculation_arcs(None)
        assert isinstance(result, dict)

    def test_extract_presentation_arcs_with_invalid_model(self):
        """Test extraction with invalid model object."""
        result = extract_presentation_arcs(None)
        assert isinstance(result, dict)
