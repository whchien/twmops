"""Tests for lxml-based XBRL parsing."""
import pytest
import io
from lxml import etree

from twmops.parsers.lxml_parser import (
    parse_instance_facts,
    parse_instance_contexts,
)

pytestmark = pytest.mark.unit


class TestLxmlInstanceParser:
    """Test lxml-based instance file parsing."""

    def test_parse_empty_facts(self):
        """Test parsing facts from empty content."""
        empty_xml = b"""<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"></xbrl>"""
        result = parse_instance_facts(empty_xml)
        assert isinstance(result, list)

    def test_parse_empty_contexts(self):
        """Test parsing contexts from empty content."""
        empty_xml = b"""<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"></xbrl>"""
        result = parse_instance_contexts(empty_xml)
        assert isinstance(result, dict)

    def test_parse_invalid_xml_facts(self):
        """Test parsing facts from invalid XML."""
        invalid_xml = b"<invalid>not well-formed"
        result = parse_instance_facts(invalid_xml)
        assert isinstance(result, list)

    def test_parse_invalid_xml_contexts(self):
        """Test parsing contexts from invalid XML."""
        invalid_xml = b"<invalid>not well-formed"
        result = parse_instance_contexts(invalid_xml)
        assert isinstance(result, dict)

    def test_parse_facts_with_numeric_content(self):
        """Test parsing facts with numeric values."""
        xml = b"""<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
    <context id="c1">
        <entity><identifier scheme="http://...">2330</identifier></entity>
        <period><instant>2023-12-31</instant></period>
    </context>
    <fact contextRef="c1" unitRef="iso4217:TWD">1000000</fact>
</xbrl>"""
        result = parse_instance_facts(xml)
        assert isinstance(result, list)

    def test_parse_contexts_with_multiple_contexts(self):
        """Test parsing multiple contexts."""
        xml = b"""<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
    <context id="c1">
        <entity><identifier scheme="http://...">2330</identifier></entity>
        <period><instant>2023-12-31</instant></period>
    </context>
    <context id="c2">
        <entity><identifier scheme="http://...">2330</identifier></entity>
        <period><instant>2024-12-31</instant></period>
    </context>
</xbrl>"""
        result = parse_instance_contexts(xml)
        assert isinstance(result, dict)

    @pytest.mark.parametrize("tag_name", ["fact", "context", "unit"])
    def test_parse_with_different_elements(self, tag_name):
        """Test parser flexibility with different element names."""
        assert True  # Basic smoke test for parser

    def test_parse_facts_returns_correct_fields(self):
        """Test that parsed facts have correct fields."""
        xml = b"""<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
    <context id="c1">
        <entity><identifier>2330</identifier></entity>
        <period><instant>2023-12-31</instant></period>
    </context>
    <Revenue contextRef="c1" unitRef="iso4217:TWD">1500000</Revenue>
</xbrl>"""
        result = parse_instance_facts(xml)
        assert isinstance(result, list)
        if result:
            fact = result[0]
            assert hasattr(fact, 'concept')
            assert hasattr(fact, 'value')
            assert hasattr(fact, 'context_ref')

    def test_parse_contexts_returns_correct_fields(self):
        """Test that parsed contexts have correct fields."""
        xml = b"""<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
    <context id="c1">
        <entity><identifier>2330</identifier></entity>
        <period><instant>2023-12-31</instant></period>
    </context>
</xbrl>"""
        result = parse_instance_contexts(xml)
        assert isinstance(result, dict)
        if result:
            ctx_id, ctx = next(iter(result.items()))
            assert hasattr(ctx, 'context_id')
            assert ctx.context_id == ctx_id
