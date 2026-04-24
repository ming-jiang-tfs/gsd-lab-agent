from __future__ import annotations

import csv
from pathlib import Path

from .models import SampleInput, SampleRecord


REQUIRED_COLUMNS = ("number", "sample_id", "sample_name")


def load_sample_input(path: Path) -> SampleInput:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Sample CSV {path} is missing headers.")

        missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"Sample CSV {path} is missing required columns: {', '.join(missing)}")

        records = [
            SampleRecord(
                number=int(row["number"]),
                sample_id=row["sample_id"].strip(),
                sample_name=row["sample_name"].strip(),
            )
            for row in reader
            if any((row.get(column) or "").strip() for column in REQUIRED_COLUMNS)
        ]

    if not records:
        raise ValueError(f"Sample CSV {path} does not contain any sample rows.")

    return SampleInput(source_path=path, records=records)
