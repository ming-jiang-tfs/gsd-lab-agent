from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class InstrumentId(str, Enum):
    ABI_3100 = "ABI_3100"
    ABI_3730 = "ABI_3730"
    ABI_3500xL = "ABI_3500xL"


class SampleRecord(BaseModel):
    number: int = Field(ge=1)
    sample_id: str = Field(min_length=1)
    sample_name: str = Field(min_length=1)


class SampleInput(BaseModel):
    source_path: Path
    records: list[SampleRecord]

    @property
    def total_samples(self) -> int:
        return len(self.records)


class DocumentSection(BaseModel):
    title: str
    content: str
    page_numbers: list[int] = Field(default_factory=list)


class AssayDocument(BaseModel):
    source_path: Path
    title: str
    raw_text: str
    sections: list[DocumentSection]


class AssayParameter(BaseModel):
    name: str
    value: str
    applies_to: str | None = None


class AssayStepDefinition(BaseModel):
    id: str
    stage: str
    title: str
    instruction_template: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class AssaySpec(BaseModel):
    assay_name: str
    source_document: str
    assay_family: str | None = None
    summary: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    parameters: list[AssayParameter] = Field(default_factory=list)
    steps: list[AssayStepDefinition]


class ProtocolStep(BaseModel):
    step_number: int = Field(ge=1)
    stage: str
    title: str
    instruction: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    severity: str
    message: str


class GeneratedProtocol(BaseModel):
    assay_name: str
    instrument: InstrumentId
    total_samples: int
    source_document: str
    steps: list[ProtocolStep]
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def ensure_steps(self) -> "GeneratedProtocol":
        if not self.steps:
            raise ValueError("Generated protocol must contain at least one step.")
        return self
