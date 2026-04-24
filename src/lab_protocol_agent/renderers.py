from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models import AssaySpec, GeneratedProtocol


FIXED_COLUMNS = ("step_number", "stage", "title", "instruction")


def write_assay_spec_json(path: Path, assay_spec: AssaySpec) -> None:
    path.write_text(assay_spec.model_dump_json(indent=2), encoding="utf-8")


def write_protocol_json(path: Path, protocol: GeneratedProtocol) -> None:
    path.write_text(protocol.model_dump_json(indent=2), encoding="utf-8")


def write_protocol_text(path: Path, protocol: GeneratedProtocol) -> None:
    lines: list[str] = []
    lines.append(f"Assay: {protocol.assay_name}")
    lines.append(f"Instrument: {protocol.instrument.value}")
    lines.append(f"Total samples: {protocol.total_samples}")
    lines.append(f"Source document: {protocol.source_document}")
    lines.append("")
    lines.append("Step-by-step protocol")
    lines.append("")

    for step in protocol.steps:
        lines.append(f"Step {step.step_number}: {step.title}")
        lines.append(f"Stage: {step.stage}")
        lines.append(step.instruction)

        detail_lines = _format_step_details(step.attributes)
        if detail_lines:
            lines.append("Details:")
            lines.extend(detail_lines)

        lines.append("")

    if protocol.validation_issues:
        lines.append("Validation issues")
        lines.append("")
        for issue in protocol.validation_issues:
            lines.append(f"- [{issue.severity}] {issue.message}")
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_protocol_csv(path: Path, protocol: GeneratedProtocol) -> list[str]:
    dynamic_columns = _collect_dynamic_columns(protocol)
    fieldnames = [*FIXED_COLUMNS, *dynamic_columns]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for step in protocol.steps:
            row = {
                "step_number": step.step_number,
                "stage": step.stage,
                "title": step.title,
                "instruction": step.instruction,
            }
            for column in dynamic_columns:
                value = step.attributes.get(column, "")
                row[column] = _serialize_csv_value(value)
            writer.writerow(row)

    return fieldnames


def _collect_dynamic_columns(protocol: GeneratedProtocol) -> list[str]:
    keys: set[str] = set()
    for step in protocol.steps:
        keys.update(step.attributes.keys())
    return sorted(keys)


def _serialize_csv_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return str(value)


def _format_step_details(attributes: dict[str, Any]) -> list[str]:
    hidden_keys = {"sample_count", "sample_ids"}
    detail_lines: list[str] = []

    for key in sorted(attributes):
        if key in hidden_keys:
            continue
        value = attributes[key]
        if value in ("", None, {}, []):
            continue

        label = key.replace("_", " ")
        if key == "notes":
            label = "notes"
        elif key == "depends_on":
            label = "depends on"

        rendered_value = _serialize_text_value(value)
        detail_lines.append(f"- {label}: {rendered_value}")

    return detail_lines


def _serialize_text_value(value: Any) -> str:
    if isinstance(value, dict):
        parts = [f"{subkey.replace('_', ' ')}={subvalue}" for subkey, subvalue in sorted(value.items())]
        return "; ".join(parts)
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value)
