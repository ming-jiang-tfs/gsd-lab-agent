from __future__ import annotations

import argparse
from pathlib import Path

from .csv_input import load_sample_input
from .extractors import build_extractor
from .models import InstrumentId
from .pdf_ingestion import load_assay_document
from .protocol_generator import generate_protocol
from .renderers import write_assay_spec_json, write_protocol_csv, write_protocol_json


def main() -> None:
    args = parse_args()
    assay_pdf = args.assay_pdf.resolve()
    samples_csv = args.samples_csv.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    document = load_assay_document(assay_pdf)
    sample_input = load_sample_input(samples_csv)
    extractor = build_extractor()
    assay_spec = extractor.extract(document)
    protocol = generate_protocol(
        assay_spec=assay_spec,
        sample_input=sample_input,
        instrument=InstrumentId(args.instrument),
    )

    write_assay_spec_json(output_dir / "assay_spec.json", assay_spec)
    write_protocol_json(output_dir / "protocol.json", protocol)
    fieldnames = write_protocol_csv(output_dir / "protocol.csv", protocol)

    print(f"Wrote assay spec to {output_dir / 'assay_spec.json'}")
    print(f"Wrote protocol JSON to {output_dir / 'protocol.json'}")
    print(f"Wrote protocol CSV to {output_dir / 'protocol.csv'}")
    print(f"Dynamic CSV headers: {', '.join(fieldnames)}")
    if protocol.validation_issues:
        print("Validation issues:")
        for issue in protocol.validation_issues:
            print(f"- [{issue.severity}] {issue.message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a technician-ready protocol from an assay PDF and sample CSV.")
    parser.add_argument("--assay-pdf", type=Path, required=True, help="Path to the authoritative assay PDF.")
    parser.add_argument("--samples-csv", type=Path, required=True, help="Path to the sample list CSV.")
    parser.add_argument(
        "--instrument",
        choices=[instrument.value for instrument in InstrumentId],
        required=True,
        help="Instrument identifier for run-specific protocol materialization.",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for generated output artifacts.")
    return parser.parse_args()
