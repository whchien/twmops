"""
XBRLParser — auto-detects ZIP vs iXBRL format and parses into XBRLPackage.
Uses Arelle when available; falls back to lxml for basic fact/context extraction.
"""

import io
import logging
import tempfile
import os
from typing import Dict, List, Optional
from pathlib import Path

from lxml import etree
from platformdirs import user_cache_dir

from twmops.models.xbrl import (
    XBRLPackage,
    CalculationArc,
    PresentationArc,
    XBRLFact,
    XBRLContext,
)
from twmops.parsers.linkbase import (
    parse_calculation_linkbase,
    parse_presentation_linkbase,
    parse_label_linkbase,
)
from twmops.parsers.lxml_parser import parse_instance_facts, parse_instance_contexts
from twmops.parsers.arelle import (
    check_arelle_available,
    extract_calculation_arcs,
    extract_presentation_arcs,
    extract_facts,
    extract_contexts,
    extract_labels,
)
from twmops.parsers.ixbrl import replace_schema_refs, extract_labels_from_html

logger = logging.getLogger(__name__)

TAXONOMY_BASE = Path(user_cache_dir("twmops")) / "taxonomy"


def _get_schema_mappings() -> dict:
    """Return schema path mappings, preferring TaxonomyManager over the static fallback."""
    try:
        from twmops.taxonomy.manager import TaxonomyManager

        manager = TaxonomyManager()
        mappings = manager.get_schema_mappings()
        if mappings:
            return mappings
    except Exception as e:
        logger.warning(f"Failed to get schema mappings from TaxonomyManager: {e}")

    return {
        "tifrs-ci-cr-2020-06-30.xsd": str(
            TAXONOMY_BASE
            / "tifrs-20200630/tifrs-20200630/XBRL_TW_Entry_Points/CI/CR/tifrs-ci-cr-2020-06-30.xsd"
        ),
        "tifrs-ci-cr-2019-03-31.xsd": str(
            TAXONOMY_BASE
            / "tifrs-20190331/tifrs-20190331/XBRL_TW_Entry_Points/CI/CR/tifrs-ci-cr-2019-03-31.xsd"
        ),
        "tifrs-ci-cr-2018-09-30.xsd": str(
            TAXONOMY_BASE
            / "tifrs-20180930/tifrs-20180930/XBRL_TW_Entry_Points/CI/CR/tifrs-ci-cr-2018-09-30.xsd"
        ),
        "tifrs-ci-cr-2018-03-31.xsd": str(
            TAXONOMY_BASE
            / "tifrs-20180331/tifrs-20180331/XBRL_TW_Entry_Points/CI/CR/tifrs-ci-cr-2018-03-31.xsd"
        ),
        "tifrs-ci-cr-2017-03-31.xsd": str(
            TAXONOMY_BASE
            / "tifrs-20170331/tifrs-20170331/XBRL_TW_Entry_Points/CI/CR/tifrs-ci-cr-2017-03-31.xsd"
        ),
        "tifrs-ci-cr-2015-03-31.xsd": str(
            TAXONOMY_BASE
            / "tifrs-20150331/tifrs-20150331/XBRL_TW_Entry_Points/CI/CR/tifrs-ci-cr-2015-03-31.xsd"
        ),
        "tifrs-ci-cr-2014-03-31.xsd": str(
            TAXONOMY_BASE
            / "tifrs-20140331/tifrs-20140331/XBRL_TW_Entry_Points/CI/CR/tifrs-ci-cr-2014-03-31.xsd"
        ),
        "tifrs-ci-cr-2013-03-31.xsd": str(
            TAXONOMY_BASE
            / "tifrs-20130331/tifrs-20130331/XBRL_TW_Entry_Points/CI/CR/tifrs-ci-cr-2013-03-31.xsd"
        ),
    }


class XBRLParserError(Exception):
    pass


class XBRLParser:
    """
    Parses XBRL/iXBRL financial report files into XBRLPackage.

    Instantiate once and call parse() with raw bytes.
    """

    def __init__(self):
        self._arelle_available = check_arelle_available()
        if not self._arelle_available:
            logger.warning(
                "Arelle not available — falling back to lxml parsing (no hierarchy/calculation)"
            )

    def parse(
        self, content: bytes, stock_id: str, year: int, quarter: int
    ) -> XBRLPackage:
        """
        Auto-detect format and parse.

        Args:
            content: Raw bytes (ZIP magic PK, or iXBRL HTML)
            stock_id: Stock ID (e.g., "2330")
            year: ROC year (民國年)
            quarter: Quarter (1–4)
        """
        if content[:2] == b"PK":
            return self.parse_zip(content, stock_id, year, quarter)
        elif b"ix:nonFraction" in content or b"ix:nonNumeric" in content:
            return self.parse_ixbrl(content, stock_id, year, quarter)
        else:
            raise XBRLParserError("Unknown file format — expected ZIP or iXBRL HTML")

    def parse_zip(
        self, zip_content: bytes, stock_id: str, year: int, quarter: int
    ) -> XBRLPackage:
        from twmops.clients.xbrl_client import MOPSXBRLClient

        client = MOPSXBRLClient()
        files = client.extract_zip(zip_content)

        logger.info(f"Extracted {len(files)} files from XBRL ZIP")

        package = XBRLPackage(stock_id=stock_id, year=year, quarter=quarter)

        if self._arelle_available:
            return self._parse_with_arelle(files, package)
        return self._parse_with_lxml(files, package)

    def parse_ixbrl(
        self, ixbrl_content: bytes, stock_id: str, year: int, quarter: int
    ) -> XBRLPackage:
        package = XBRLPackage(stock_id=stock_id, year=year, quarter=quarter)

        if self._arelle_available:
            try:
                return self._parse_ixbrl_with_arelle(ixbrl_content, package)
            except Exception as e:
                logger.warning(
                    f"Arelle parsing failed for iXBRL, falling back to lxml: {e}"
                )

        try:
            parser = etree.HTMLParser(encoding="utf-8")
            tree = etree.parse(io.BytesIO(ixbrl_content), parser)
            root = tree.getroot()

            ix_ns = "http://www.xbrl.org/2013/inlineXBRL"

            facts = []
            for elem in root.iter():
                tag_lower = str(elem.tag).lower()

                if "nonfraction" in tag_lower:
                    name = elem.get("name", "")
                    context_ref = elem.get("contextref", "") or elem.get(
                        "contextRef", ""
                    )
                    unit_ref = elem.get("unitref") or elem.get("unitRef")
                    decimals = elem.get("decimals")
                    raw_value = (elem.text or "").replace(",", "").strip()
                    concept = name.split(":")[-1] if ":" in name else name

                    facts.append(
                        XBRLFact(
                            concept=concept,
                            value=raw_value,
                            unit=unit_ref,
                            context_ref=context_ref,
                            decimals=int(decimals)
                            if decimals and decimals.lstrip("-").isdigit()
                            else None,
                        )
                    )

                elif "nonnumeric" in tag_lower:
                    name = elem.get("name", "")
                    context_ref = elem.get("contextref", "") or elem.get(
                        "contextRef", ""
                    )
                    concept = name.split(":")[-1] if ":" in name else name

                    facts.append(
                        XBRLFact(
                            concept=concept,
                            value=elem.text,
                            unit=None,
                            context_ref=context_ref,
                            decimals=None,
                        )
                    )

            package.facts = facts
            logger.info(f"Parsed {len(facts)} facts from iXBRL with lxml")

            contexts = {}
            for ctx in root.iter():
                if "context" in str(ctx.tag).lower() and ctx.get("id"):
                    ctx_id = ctx.get("id", "")
                    entity = ""
                    for id_elem in ctx.iter():
                        if "identifier" in str(id_elem.tag).lower():
                            entity = id_elem.text or ""
                            break

                    instant = None
                    start_date = None
                    end_date = None

                    for period_elem in ctx.iter():
                        tag_lower2 = str(period_elem.tag).lower()
                        if "instant" in tag_lower2:
                            instant = period_elem.text
                        elif "startdate" in tag_lower2:
                            start_date = period_elem.text
                        elif "enddate" in tag_lower2:
                            end_date = period_elem.text

                    contexts[ctx_id] = XBRLContext(
                        context_id=ctx_id,
                        entity=entity,
                        period_start=start_date,
                        period_end=end_date,
                        instant=instant,
                    )

            package.contexts = contexts
            logger.info(f"Parsed {len(contexts)} contexts from iXBRL with lxml")

        except Exception as e:
            logger.error(f"Error parsing iXBRL with lxml: {e}")
            raise XBRLParserError(f"Failed to parse iXBRL: {e}")

        return package

    def _parse_ixbrl_with_arelle(
        self, content: bytes, package: XBRLPackage
    ) -> XBRLPackage:
        from arelle import Cntlr, ModelManager, FileSource

        content_modified = replace_schema_refs(content, _get_schema_mappings())

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp.write(content_modified)
            tmp_path = tmp.name

        try:
            cntlr = Cntlr.Cntlr(logFileName="logToPrint")
            model_manager = ModelManager.initialize(cntlr)

            try:
                model_xbrl = model_manager.load(FileSource.FileSource(tmp_path))

                if model_xbrl is None:
                    raise XBRLParserError("Failed to load iXBRL document with Arelle")

                package.calculation_arcs = extract_calculation_arcs(model_xbrl)
                package.presentation_arcs = extract_presentation_arcs(model_xbrl)
                package.facts = extract_facts(model_xbrl)
                package.contexts = extract_contexts(model_xbrl)
                package.labels, package.labels_en = extract_labels(model_xbrl)

                if not package.labels:
                    logger.warning(
                        "Arelle returned empty labels, extracting from HTML structure"
                    )
                    package.labels, package.labels_en = extract_labels_from_html(
                        content
                    )

                model_xbrl.close()
                logger.info(
                    f"Parsed iXBRL with Arelle: {len(package.facts)} facts, "
                    f"{len(package.labels)} labels, {len(package.calculation_arcs)} calc parents"
                )
            finally:
                cntlr.close()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return package

    def _parse_with_arelle(
        self, files: Dict[str, bytes], package: XBRLPackage
    ) -> XBRLPackage:
        from arelle import Cntlr, ModelManager, FileSource

        instance_file = self._find_instance_file(files)
        if not instance_file:
            raise XBRLParserError("No instance document found in ZIP")

        with tempfile.TemporaryDirectory() as tmpdir:
            for filename, content in files.items():
                filepath = Path(tmpdir) / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_bytes(content)

            instance_path = Path(tmpdir) / instance_file

            cntlr = Cntlr.Cntlr(logFileName="logToPrint")
            model_manager = ModelManager.initialize(cntlr)

            try:
                model_xbrl = model_manager.load(
                    FileSource.FileSource(str(instance_path))
                )

                if model_xbrl is None:
                    raise XBRLParserError("Failed to load XBRL document with Arelle")

                package.calculation_arcs = extract_calculation_arcs(model_xbrl)
                package.presentation_arcs = extract_presentation_arcs(model_xbrl)
                package.facts = extract_facts(model_xbrl)
                package.contexts = extract_contexts(model_xbrl)
                package.labels, package.labels_en = extract_labels(model_xbrl)
                model_xbrl.close()
            finally:
                cntlr.close()

        return package

    def _parse_with_lxml(
        self, files: Dict[str, bytes], package: XBRLPackage
    ) -> XBRLPackage:
        for filename, content in files.items():
            if "_cal" in filename.lower() and filename.endswith(".xml"):
                package.calculation_arcs = parse_calculation_linkbase(content)
            elif "_pre" in filename.lower() and filename.endswith(".xml"):
                package.presentation_arcs = parse_presentation_linkbase(content)
            elif "_lab" in filename.lower() and filename.endswith(".xml"):
                labels_zh, labels_en = parse_label_linkbase(content)
                package.labels.update(labels_zh)
                package.labels_en.update(labels_en)

        instance_file = self._find_instance_file(files)
        if instance_file:
            instance_content = files[instance_file]
            package.facts = parse_instance_facts(instance_content)
            package.contexts = parse_instance_contexts(instance_content)

        return package

    def _find_instance_file(self, files: Dict[str, bytes]) -> Optional[str]:
        for filename in files.keys():
            if filename.endswith((".htm", ".html")):
                return filename
            if filename.endswith(".xml") and not any(
                x in filename.lower()
                for x in ["_cal", "_pre", "_lab", "_def", "_ref", ".xsd"]
            ):
                return filename
        return None
