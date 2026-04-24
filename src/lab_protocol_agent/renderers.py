from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import AssaySpec, GeneratedProtocol


FIXED_COLUMNS = ("step_number", "stage", "title", "instruction")


def write_assay_spec_json(path: Path, assay_spec: AssaySpec) -> None:
    path.write_text(assay_spec.model_dump_json(indent=2), encoding="utf-8")


def write_protocol_json(path: Path, protocol: GeneratedProtocol) -> None:
    path.write_text(protocol.model_dump_json(indent=2), encoding="utf-8")


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
