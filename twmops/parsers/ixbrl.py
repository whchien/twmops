"""
iXBRL (Inline XBRL) parsing helpers
"""
import io
import logging
from pathlib import Path
from typing import Dict, Tuple

from lxml import etree

logger = logging.getLogger(__name__)


def replace_schema_refs(content: bytes, schema_mappings: Dict[str, str]) -> bytes:
    """
    Replace relative schemaRef hrefs in an iXBRL document with file:// URIs
    pointing to locally downloaded taxonomy files.
    """
    try:
        content_str = content.decode('utf-8')

        for relative_schema, local_path in schema_mappings.items():
            full_local_path = Path(local_path)
            if full_local_path.exists():
                old_ref = f'xlink:href="{relative_schema}"'
                new_ref = f'xlink:href="file://{full_local_path}"'
                if old_ref in content_str:
                    content_str = content_str.replace(old_ref, new_ref)
                    logger.info(f"Replaced schema ref: {relative_schema} -> {full_local_path}")
                    break

        return content_str.encode('utf-8')
    except Exception as e:
        logger.warning(f"Failed to replace schema refs: {e}")
        return content


def extract_labels_from_html(content: bytes) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Extract zh/en labels from iXBRL HTML by walking up from ix:nonFraction
    elements to their parent table row and reading the first non-numeric cell.
    """
    labels_zh: Dict[str, str] = {}
    labels_en: Dict[str, str] = {}

    try:
        parser = etree.HTMLParser(encoding='utf-8')
        tree = etree.parse(io.BytesIO(content), parser)
        root = tree.getroot()

        for elem in root.iter():
            tag_lower = str(elem.tag).lower()
            if 'nonfraction' not in tag_lower:
                continue

            name = elem.get("name", "")
            if not name:
                continue

            concept = name.split(":")[-1] if ":" in name else name
            if concept in labels_zh:
                continue

            # Walk up to the parent <tr>
            parent = elem.getparent()
            row = None
            for _ in range(15):
                if parent is None:
                    break
                if parent.tag and 'tr' in str(parent.tag).lower():
                    row = parent
                    break
                parent = parent.getparent()

            if row is None:
                continue

            for cell in row.iter():
                cell_tag = str(cell.tag).lower() if cell.tag else ""
                if 'td' not in cell_tag and 'th' not in cell_tag:
                    continue

                text = ''.join(cell.itertext()).strip()
                if not text:
                    continue

                clean_text = text.replace(',', '').replace('-', '').replace('.', '').replace(' ', '')
                if clean_text.isdigit():
                    continue

                # Taiwan IFRS uses double full-width space or two spaces to separate zh/en
                parts = text.split('　　')
                if len(parts) < 2:
                    parts = text.split('  ')

                if len(parts) >= 2:
                    zh_text = parts[0].strip()
                    en_text = parts[1].strip()[:100]
                    if zh_text:
                        labels_zh[concept] = zh_text
                    if en_text:
                        labels_en[concept] = en_text
                else:
                    if any('一' <= c <= '鿿' for c in text):
                        labels_zh[concept] = text[:100]
                    else:
                        labels_en[concept] = text[:100]

                break

        logger.info(f"Extracted {len(labels_zh)} Chinese labels and {len(labels_en)} English labels from HTML")

    except Exception as e:
        logger.error(f"Error extracting labels from HTML: {e}")

    return labels_zh, labels_en
