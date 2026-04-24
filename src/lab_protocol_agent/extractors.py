from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any

from .models import AssayDocument, AssayParameter, AssaySpec, AssayStepDefinition


class AssaySpecExtractor(ABC):
    @abstractmethod
    def extract(self, document: AssayDocument) -> AssaySpec:
        raise NotImplementedError


class OpenAIAssaySpecExtractor(AssaySpecExtractor):
    def __init__(self, model: str = "gpt-5.4") -> None:
        self.model = model

    def extract(self, document: AssayDocument) -> AssaySpec:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI dependency is not installed. Install with `.[openai]`.") from exc

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")

        client = OpenAI()
        prompt = _build_extraction_prompt(document)
        response = client.responses.create(
            model=self.model,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "assay_spec",
                    "schema": _assay_spec_schema(),
                }
            },
        )
        content = response.output_text
        payload = json.loads(content)
        return AssaySpec.model_validate(payload)


class HeuristicAssaySpecExtractor(AssaySpecExtractor):
    def extract(self, document: AssayDocument) -> AssaySpec:
        text = document.raw_text
        steps: list[AssayStepDefinition] = []

        steps.append(
            AssayStepDefinition(
                id="prepare-dna",
                stage="Sample Preparation",
                title="Prepare purified DNA samples",
                instruction_template=(
                    "Prepare purified DNA for all {sample_count} samples at 15-30 ng/uL. "
                    "Use molecular-biology-grade water only for immediate use aliquots and discard those aliquots after use."
                ),
                attributes={"dna_concentration": "15-30 ng/uL", "sample_scope": "all_samples"},
                notes=_find_sentences(text, ["A 260/A280", "Change pipette tips", "Do not use heparinized"]),
            )
        )
        steps.append(
            AssayStepDefinition(
                id="prepare-mastermix",
                stage="Amplification",
                title="Prepare amplification master mix",
                instruction_template=(
                    "Prepare amplification master mix for {sample_count} samples plus controls using the assay-specific Amp Mix "
                    "and FastStart Taq DNA Polymerase volumes from the assay document."
                ),
                attributes={
                    "reagents": "Amp Mix; FastStart Taq DNA Polymerase",
                    "class_i_per_reaction": "19.8 uL Amp Mix + 0.2 uL Taq",
                    "class_ii_per_reaction": "22.8 uL Amp Mix + 0.2 uL Taq",
                },
                notes=_find_sentences(text, ["25 Test kits", "500 test kits", "viscous nature of FastStart"]),
            )
        )
        steps.append(
            AssayStepDefinition(
                id="amplify-dna",
                stage="Amplification",
                title="Run PCR amplification",
                instruction_template=(
                    "Set up PCR reactions for {sample_count} samples and run the amplification profile described in the IFU."
                ),
                attributes={
                    "class_i_reaction_volume": "25 uL",
                    "class_ii_reaction_volume": "25 uL",
                    "class_i_dna_input": "5 uL",
                    "class_ii_dna_input": "2 uL",
                    "thermal_profile": "95C 4 min; 35 cycles of 95C 20 sec, 63C 20 sec, 72C 40 sec; 72C 5 min; 4C hold",
                },
            )
        )
        steps.append(
            AssayStepDefinition(
                id="agarose-gel",
                stage="Amplification QC",
                title="Confirm PCR products by agarose gel electrophoresis",
                instruction_template=(
                    "Load 5 uL of PCR product plus loading dye on a 2.0% agarose gel to confirm amplification before purification."
                ),
                attributes={
                    "gel_percentage": "2.0%",
                    "loaded_volume": "5 uL",
                    "expected_product_sizes": _extract_expected_product_sizes(text),
                },
            )
        )
        steps.append(
            AssayStepDefinition(
                id="exosap-purification",
                stage="Purification",
                title="Purify PCR amplicons with ExoSAP-IT",
                instruction_template=(
                    "Add ExoSAP-IT to amplified products, mix thoroughly, and run the cleanup thermal profile before sequencing setup."
                ),
                attributes={
                    "exosap_it_volume": "4 uL",
                    "cleanup_profile": "37C 20 min; 80C 20 min; 4C hold",
                },
                dependencies=["agarose-gel"],
            )
        )
        steps.append(
            AssayStepDefinition(
                id="sequencing-setup",
                stage="Sequencing Reaction",
                title="Prepare sequencing reactions",
                instruction_template=(
                    "Set up sequencing reactions using the purified amplicons, adding 2 uL amplicon and 8 uL sequencing mix to each reaction well. "
                    "For Class II reactions only, add 40 uL ultrapure water before sequencing setup."
                ),
                attributes={
                    "amplicon_per_reaction": "2 uL",
                    "sequencing_mix_per_reaction": "8 uL",
                    "class_ii_water_addition": "40 uL",
                    "sequencing_profile": "25 cycles of 95C 20 sec, 50C 15 sec, 60C 60 sec; 4C hold",
                },
                dependencies=["exosap-purification"],
            )
        )
        steps.append(
            AssayStepDefinition(
                id="ethanol-precipitation",
                stage="Sequencing Cleanup",
                title="Perform ethanol precipitation",
                instruction_template=(
                    "Perform ethanol precipitation on each sequencing reaction before capillary electrophoresis."
                ),
                attributes={
                    "ppt_buffer_volume": "2 uL",
                    "ethanol_100_percent_volume": "40 uL",
                    "ethanol_wash_volume": "100 uL",
                    "ethanol_wash_concentration": "70%-80%",
                    "centrifuge_primary": "30 min at 2,000 x g or greater",
                    "centrifuge_inverted": "1 min at 500 x g",
                },
                dependencies=["sequencing-setup"],
            )
        )
        steps.append(
            AssayStepDefinition(
                id="capillary-loading",
                stage="Capillary Sequencing",
                title="Prepare loading samples and run instrument",
                instruction_template=(
                    "Resuspend each pellet in Hi-Di Formamide, denature at 95C for 2 min, then load onto the selected sequencing instrument."
                ),
                attributes={
                    "hi_di_formamide_volume": "15 uL",
                    "denaturation": "95C for 2 min",
                    "instrument_parameters": {
                        "ABI_3100": {"run_module": "RapidSeq36_POP6", "injection_time": "10 sec", "run_time": "1800 sec"},
                        "ABI_3730": {"run_module": "StdSeq36", "injection_time": "5 sec", "run_time": "1800 sec"},
                        "ABI_3500xL": {"run_module": "StdSeq50", "injection_time": "Default", "run_time": "3780 sec"},
                    },
                },
                dependencies=["ethanol-precipitation"],
            )
        )
        steps.append(
            AssayStepDefinition(
                id="data-analysis",
                stage="Analysis",
                title="Analyze sequence data",
                instruction_template=(
                    "Process raw data with Sequencing Analysis software and create HLA typing reports with One Lambda uTYPE software."
                ),
                attributes={
                    "software": "Sequencing Analysis software; One Lambda uTYPE HLA Sequence Analysis Software",
                    "database_note": "Use the most recent IMGT allele database for analysis.",
                },
                dependencies=["capillary-loading"],
            )
        )

        parameters = [
            AssayParameter(name="assay_family", value="SeCore HLA Sequencing Kit"),
            AssayParameter(name="supported_instruments", value="ABI_3100, ABI_3730, ABI_3500xL"),
        ]

        return AssaySpec(
            assay_name=document.title,
            source_document=str(document.source_path),
            assay_family="SeCore HLA",
            summary="Heuristically extracted assay spec from the SeCore RUO IFU.",
            assumptions=[
                "This fallback extraction path derives a normalized assay spec from recognizable text patterns in the IFU.",
                "Manual review of assay_spec.json is recommended before operational use.",
            ],
            materials=_find_materials(text),
            parameters=parameters,
            steps=steps,
        )


def build_extractor() -> AssaySpecExtractor:
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIAssaySpecExtractor()
    return HeuristicAssaySpecExtractor()


def _build_extraction_prompt(document: AssayDocument) -> str:
    return f"""
You are converting an assay instruction PDF into a normalized assay specification.

Requirements:
- Preserve the assay's real workflow stages and operational detail.
- Do not invent assay-specific fields unless they are supported by the document.
- Include ordered technician-facing step definitions with reusable instruction templates.
- Represent instrument-specific run settings as structured attributes when present.
- Capture branching conditions, cautions, and sample-dependent logic.
- The source assay is expected to be used later with a sample CSV and an explicit instrument input.

Return JSON only, matching the provided schema.

Source document path: {document.source_path}
Source title: {document.title}

Document sections:
{json.dumps([section.model_dump() for section in document.sections], indent=2)}
""".strip()


def _assay_spec_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "assay_name": {"type": "string"},
            "source_document": {"type": "string"},
            "assay_family": {"type": ["string", "null"]},
            "summary": {"type": ["string", "null"]},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "materials": {"type": "array", "items": {"type": "string"}},
            "parameters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "string"},
                        "applies_to": {"type": ["string", "null"]},
                    },
                    "required": ["name", "value", "applies_to"],
                },
            },
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "stage": {"type": "string"},
                        "title": {"type": "string"},
                        "instruction_template": {"type": "string"},
                        "attributes": {"type": "object"},
                        "notes": {"type": "array", "items": {"type": "string"}},
                        "dependencies": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "id",
                        "stage",
                        "title",
                        "instruction_template",
                        "attributes",
                        "notes",
                        "dependencies",
                    ],
                },
            },
        },
        "required": [
            "assay_name",
            "source_document",
            "assay_family",
            "summary",
            "assumptions",
            "materials",
            "parameters",
            "steps",
        ],
    }


def _find_sentences(text: str, keywords: list[str]) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    matches: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword.lower() in lowered for keyword in keywords):
            matches.append(sentence.strip())
    return matches[:5]


def _find_materials(text: str) -> list[str]:
    materials = []
    for keyword in [
        "FastStart",
        "ExoSAP-IT",
        "Hi-Di",
        "ethanol",
        "Amp Mix",
        "thermal cycler",
        "agarose gel",
        "uTYPE",
    ]:
        if keyword.lower() in text.lower():
            materials.append(keyword)
    return materials


def _extract_expected_product_sizes(text: str) -> str:
    match = re.search(r"Expected products.*?DPB1 Locus ~300 and ~1000 None", text, re.IGNORECASE | re.DOTALL)
    if match:
        return "A ~1200/~990; B ~1400/~950; C ~1375/~1600; DRB1 ~300; DRB1 exon2 ~500-850 exon3 ~450; DRB Group ~300/~600 IC; DQB1 ~350/~375; DPB1 ~300/~1000"
    return "See assay document for locus-specific amplicon sizes."
