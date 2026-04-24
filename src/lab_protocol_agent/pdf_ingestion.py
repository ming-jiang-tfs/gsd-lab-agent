from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from .models import AssayDocument, DocumentSection


SECTION_HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+([A-Z][A-Za-z0-9®™()\-/, ]{3,})\s*:?$")


def load_assay_document(path: Path) -> AssayDocument:
    reader = PdfReader(str(path))
    page_texts: list[str] = []
    sections: list[DocumentSection] = []
    current_title = "Document Overview"
    current_lines: list[str] = []
    current_pages: set[int] = set()

    for page_index, page in enumerate(reader.pages, start=1):
        extracted = page.extract_text() or ""
        normalized_lines = [_normalize_line(line) for line in extracted.splitlines()]
        page_texts.append("\n".join(line for line in normalized_lines if line))

        for line in normalized_lines:
            if not line:
                continue

            match = SECTION_HEADING_RE.match(line)
            if match:
                if current_lines:
                    sections.append(
                        DocumentSection(
                            title=current_title,
                            content="\n".join(current_lines).strip(),
                            page_numbers=sorted(current_pages),
                        )
                    )
                current_title = f"{match.group(1)} {match.group(2).strip()}"
                current_lines = []
                current_pages = {page_index}
                continue

            current_lines.append(line)
            current_pages.add(page_index)

    if current_lines:
        sections.append(
            DocumentSection(
                title=current_title,
                content="\n".join(current_lines).strip(),
                page_numbers=sorted(current_pages),
            )
        )

    raw_text = "\n\n".join(text for text in page_texts if text).strip()
    return AssayDocument(
        source_path=path,
        title=path.stem,
        raw_text=raw_text,
        sections=sections,
    )


def _normalize_line(line: str) -> str:
    collapsed = " ".join(line.replace("\x00", " ").split())
    return collapsed.strip()
