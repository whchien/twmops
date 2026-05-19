"""Tests for iXBRL HTML parsing."""
import pytest
from unittest.mock import Mock, patch

from twmops.parsers.ixbrl import (
    replace_schema_refs,
    extract_labels_from_html,
)

pytestmark = pytest.mark.unit


class TestSchemaRefReplacement:
    """Test schema reference replacement functionality."""

    def test_replace_schema_refs_with_empty_html(self):
        """Test replacement with empty HTML."""
        result = replace_schema_refs("", {})
        assert isinstance(result, str)

    def test_replace_schema_refs_with_no_refs(self):
        """Test replacement when no schema refs are present."""
        html = "<html><body><p>No refs here</p></body></html>"
        result = replace_schema_refs(html, {})
        assert isinstance(result, str)

    def test_replace_schema_refs_returns_string(self):
        """Test that replacement returns a string."""
        html = "<html><body></body></html>"
        mappings = {}
        result = replace_schema_refs(html, mappings)
        assert isinstance(result, str)

    @pytest.mark.parametrize("mapping_type", [
        {},
        {"schema1": "path/to/schema1"},
        {"schema1": "path/to/schema1", "schema2": "path/to/schema2"},
    ])
    def test_replace_with_different_mappings(self, mapping_type):
        """Test replacement with different mapping configurations."""
        html = "<html></html>"
        result = replace_schema_refs(html, mapping_type)
        assert isinstance(result, str)


class TestHTMLLabelExtraction:
    """Test label extraction from iXBRL HTML."""

    def test_extract_labels_from_empty_html(self):
        """Test label extraction from empty HTML."""
        result = extract_labels_from_html(b"")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_extract_labels_returns_tuple(self):
        """Test that extraction returns a tuple of two dicts."""
        html = b"<html><body></body></html>"
        result = extract_labels_from_html(html)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], dict)  # zh labels
        assert isinstance(result[1], dict)  # en labels

    def test_extract_labels_with_html_tags(self):
        """Test extraction with various HTML tags."""
        html = b"""
        <html>
            <body>
                <div>Content</div>
                <p>Paragraph</p>
                <span>Span</span>
            </body>
        </html>
        """
        result = extract_labels_from_html(html)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_extract_labels_with_special_characters(self):
        """Test extraction with special characters."""
        html = b"<html><body>Special: &amp; &lt; &gt; &quot;</body></html>"
        result = extract_labels_from_html(html)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_extract_labels_with_malformed_html(self):
        """Test extraction from malformed HTML."""
        html = b"<html><body><unclosed><tag>"
        result = extract_labels_from_html(html)
        assert isinstance(result, tuple)
        assert len(result) == 2
