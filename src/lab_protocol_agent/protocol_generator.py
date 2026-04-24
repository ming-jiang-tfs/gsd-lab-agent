from __future__ import annotations

from collections import Counter
from typing import Any

from .models import AssaySpec, GeneratedProtocol, InstrumentId, ProtocolStep, SampleInput, ValidationIssue


def generate_protocol(
    assay_spec: AssaySpec,
    sample_input: SampleInput,
    instrument: InstrumentId,
) -> GeneratedProtocol:
    step_rows: list[ProtocolStep] = []
    sample_count = sample_input.total_samples

    for index, step in enumerate(assay_spec.steps, start=1):
        rendered_instruction = step.instruction_template.format(sample_count=sample_count)
        attributes = _materialize_attributes(step.attributes, sample_input, instrument)
        if step.notes:
            attributes["notes"] = " | ".join(step.notes)
        if step.dependencies:
            attributes["depends_on"] = ", ".join(step.dependencies)

        step_rows.append(
            ProtocolStep(
                step_number=index,
                stage=step.stage,
                title=step.title,
                instruction=rendered_instruction,
                attributes=attributes,
            )
        )

    protocol = GeneratedProtocol(
        assay_name=assay_spec.assay_name,
        instrument=instrument,
        total_samples=sample_count,
        source_document=assay_spec.source_document,
        steps=step_rows,
        validation_issues=validate_generated_protocol(step_rows, sample_input),
        metadata={
            "sample_ids": [record.sample_id for record in sample_input.records],
            "sample_names": [record.sample_name for record in sample_input.records],
            "source_samples_csv": str(sample_input.source_path),
        },
    )
    return protocol


def validate_generated_protocol(
    steps: list[ProtocolStep],
    sample_input: SampleInput,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    titles = Counter(step.title for step in steps)

    if sample_input.total_samples < 1:
        issues.append(ValidationIssue(severity="error", message="No samples were provided."))

    duplicates = [title for title, count in titles.items() if count > 1]
    if duplicates:
        issues.append(
            ValidationIssue(
                severity="warning",
                message=f"Duplicate step titles detected: {', '.join(sorted(duplicates))}",
            )
        )

    if not any("instrument_parameters" in step.attributes for step in steps):
        issues.append(
            ValidationIssue(
                severity="warning",
                message="No instrument parameters were materialized into the generated protocol.",
            )
        )

    for expected_title in ["Prepare purified DNA samples", "Run PCR amplification", "Analyze sequence data"]:
        if not any(step.title == expected_title for step in steps):
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message=f"Expected workflow stage missing from generated protocol: {expected_title}",
                )
            )

    return issues


def _materialize_attributes(
    attributes: dict[str, Any],
    sample_input: SampleInput,
    instrument: InstrumentId,
) -> dict[str, Any]:
    materialized: dict[str, Any] = {}

    for key, value in attributes.items():
        if key == "instrument_parameters" and isinstance(value, dict):
            materialized[key] = value.get(instrument.value, {})
            continue
        materialized[key] = value

    materialized["sample_count"] = sample_input.total_samples
    materialized["sample_ids"] = ", ".join(record.sample_id for record in sample_input.records)
    return materialized
