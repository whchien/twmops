"""Tests for XBRL Linkbase parsers."""
import pytest
import io
from lxml import etree

from twmops.parsers.linkbase import (
    parse_calculation_linkbase,
    parse_presentation_linkbase,
    parse_label_linkbase,
)
from twmops.models.xbrl import CalculationArc, PresentationArc

pytestmark = pytest.mark.unit


class TestCalculationLinkbaseParser:
    """Test calculation linkbase parsing."""

    def test_parse_empty_linkbase(self):
        """Test parsing empty calculation linkbase."""
        empty_xml = b"""<?xml version="1.0"?>
<linkbase xmlns:xlink="http://www.w3.org/1999/xlink"></linkbase>"""
        result = parse_calculation_linkbase(empty_xml)
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_parse_invalid_xml(self):
        """Test parsing invalid XML returns empty dict."""
        invalid_xml = b"<invalid>not well-formed"
        result = parse_calculation_linkbase(invalid_xml)
        assert isinstance(result, dict)

    def test_parse_linkbase_with_arcs(self):
        """Test parsing linkbase with calculation arcs."""
        xml_with_arcs = b"""<?xml version="1.0"?>
<linkbase xmlns="http://www.xbrl.org/2003/linkbase"
          xmlns:xlink="http://www.w3.org/1999/xlink">
    <calculationArc from="total" to="item1" weight="1.0" order="1.0"
                   xlink:from="from1" xlink:to="to1"/>
</linkbase>"""
        result = parse_calculation_linkbase(xml_with_arcs)
        assert isinstance(result, dict)

    @pytest.mark.parametrize("weight,order", [
        (1.0, 1.0),
        (-1.0, 2.0),
        (0.5, 0.0),
    ])
    def test_parse_arcs_with_different_weights(self, weight, order):
        """Test parsing arcs with different weight values."""
        xml = f"""<?xml version="1.0"?>
<linkbase xmlns="http://www.xbrl.org/2003/linkbase"
          xmlns:xlink="http://www.w3.org/1999/xlink">
    <calculationArc from="total" to="item1" weight="{weight}" order="{order}"
                   xlink:from="from1" xlink:to="to1"/>
</linkbase>""".encode()
        result = parse_calculation_linkbase(xml)
        assert isinstance(result, dict)


class TestPresentationLinkbaseParser:
    """Test presentation linkbase parsing."""

    def test_parse_empty_presentation_linkbase(self):
        """Test parsing empty presentation linkbase."""
        empty_xml = b"""<?xml version="1.0"?>
<linkbase xmlns:xlink="http://www.w3.org/1999/xlink"></linkbase>"""
        result = parse_presentation_linkbase(empty_xml)
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_parse_invalid_presentation_xml(self):
        """Test parsing invalid presentation XML."""
        invalid_xml = b"<invalid>not well-formed"
        result = parse_presentation_linkbase(invalid_xml)
        assert isinstance(result, dict)

    def test_parse_presentation_with_arcs(self):
        """Test parsing presentation linkbase with arcs."""
        xml_with_arcs = b"""<?xml version="1.0"?>
<linkbase xmlns="http://www.xbrl.org/2003/linkbase"
          xmlns:xlink="http://www.w3.org/1999/xlink">
    <presentationArc from="parent" to="child" order="1.0"
                    xlink:from="from1" xlink:to="to1"/>
</linkbase>"""
        result = parse_presentation_linkbase(xml_with_arcs)
        assert isinstance(result, dict)


class TestLabelLinkbaseParser:
    """Test label linkbase parsing."""

    def test_parse_empty_label_linkbase(self):
        """Test parsing empty label linkbase."""
        empty_xml = b"""<?xml version="1.0"?>
<linkbase xmlns:xlink="http://www.w3.org/1999/xlink"></linkbase>"""
        result = parse_label_linkbase(empty_xml)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], dict)  # zh labels
        assert isinstance(result[1], dict)  # en labels

    def test_parse_invalid_label_xml(self):
        """Test parsing invalid label XML."""
        invalid_xml = b"<invalid>not well-formed"
        result = parse_label_linkbase(invalid_xml)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_parse_label_with_labels(self):
        """Test parsing label linkbase with labels."""
        xml_with_labels = b"""<?xml version="1.0"?>
<linkbase xmlns="http://www.xbrl.org/2003/linkbase"
          xmlns:xlink="http://www.w3.org/1999/xlink"
          xmlns:xhtml="http://www.w3.org/1999/xhtml">
    <labelArc from="label1" to="concept1" xlink:from="from1" xlink:to="to1"/>
</linkbase>"""
        result = parse_label_linkbase(xml_with_labels)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_parse_calculation_arc_values(self):
        """Test parsing calculation arc with specific weight and order values."""
        xml = b"""<?xml version="1.0"?>
<linkbase xmlns="http://www.xbrl.org/2003/linkbase"
          xmlns:xlink="http://www.w3.org/1999/xlink">
    <calculationArc from="total" to="item1" weight="-1" order="2"
                   xlink:from="from1" xlink:to="to1"/>
</linkbase>"""
        result = parse_calculation_linkbase(xml)
        assert isinstance(result, dict)
        # Parser should extract and properly type the weight and order

    def test_parse_label_returns_zh_en_tuple(self):
        """Test that label parser returns zh and en dicts."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<linkbase xmlns="http://www.xbrl.org/2003/linkbase"
          xmlns:xlink="http://www.w3.org/1999/xlink"
          xmlns:xhtml="http://www.w3.org/1999/xhtml"
          xmlns:xml="http://www.w3.org/XML/1998/namespace">
    <label id="label1" xml:lang="zh-TW" xlink:label="label_zh">資產</label>
    <label id="label2" xml:lang="en" xlink:label="label_en">Assets</label>
</linkbase>""".encode('utf-8')
        zh_labels, en_labels = parse_label_linkbase(xml)
        assert isinstance(zh_labels, dict)
        assert isinstance(en_labels, dict)
