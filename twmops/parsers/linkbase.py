"""
XBRL Linkbase parsers: Calculation, Presentation, Label
"""

import io
import logging
from typing import Dict, List, Tuple

from lxml import etree

from twmops.models.xbrl import CalculationArc, PresentationArc

logger = logging.getLogger(__name__)


def parse_calculation_linkbase(content: bytes) -> Dict[str, List[CalculationArc]]:
    """
    Parse a Calculation Linkbase XML.
    weight = 1.0 means add, weight = -1.0 means subtract.
    """
    result: Dict[str, List[CalculationArc]] = {}

    try:
        tree = etree.parse(io.BytesIO(content))
        root = tree.getroot()

        for arc in root.iter("{http://www.xbrl.org/2003/linkbase}calculationArc"):
            from_attr = arc.get("{http://www.w3.org/1999/xlink}from", "")
            to_attr = arc.get("{http://www.w3.org/1999/xlink}to", "")
            weight = float(arc.get("weight", "1.0"))
            order = float(arc.get("order", "0.0"))

            if from_attr:
                if from_attr not in result:
                    result[from_attr] = []
                result[from_attr].append(
                    CalculationArc(
                        from_concept=from_attr,
                        to_concept=to_attr,
                        weight=weight,
                        order=order,
                    )
                )

        logger.info(f"Parsed {sum(len(v) for v in result.values())} calculation arcs")

    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error in calculation linkbase: {e}")

    return result


def parse_presentation_linkbase(content: bytes) -> Dict[str, List[PresentationArc]]:
    """Parse a Presentation Linkbase XML."""
    result: Dict[str, List[PresentationArc]] = {}

    try:
        tree = etree.parse(io.BytesIO(content))
        root = tree.getroot()

        for arc in root.iter("{http://www.xbrl.org/2003/linkbase}presentationArc"):
            from_attr = arc.get("{http://www.w3.org/1999/xlink}from", "")
            to_attr = arc.get("{http://www.w3.org/1999/xlink}to", "")
            order = float(arc.get("order", "0.0"))
            preferred_label = arc.get("preferredLabel")

            if from_attr:
                if from_attr not in result:
                    result[from_attr] = []
                result[from_attr].append(
                    PresentationArc(
                        from_concept=from_attr,
                        to_concept=to_attr,
                        order=order,
                        preferred_label=preferred_label,
                    )
                )

        logger.info(f"Parsed {sum(len(v) for v in result.values())} presentation arcs")

    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error in presentation linkbase: {e}")

    return result


def parse_label_linkbase(content: bytes) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Parse a Label Linkbase XML, returning (labels_zh, labels_en)."""
    labels_zh: Dict[str, str] = {}
    labels_en: Dict[str, str] = {}

    try:
        tree = etree.parse(io.BytesIO(content))
        root = tree.getroot()

        for label in root.iter("{http://www.xbrl.org/2003/linkbase}label"):
            label_text = label.text or ""
            lang = label.get("{http://www.w3.org/XML/1998/namespace}lang", "")
            xlink_label = label.get("{http://www.w3.org/1999/xlink}label", "")

            if "zh" in lang.lower() or "tw" in lang.lower():
                labels_zh[xlink_label] = label_text
            elif "en" in lang.lower():
                labels_en[xlink_label] = label_text

    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error in label linkbase: {e}")

    return labels_zh, labels_en
