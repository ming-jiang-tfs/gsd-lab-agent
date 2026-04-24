# V1 Plan Summary

## Scope

- `v1` supports only `SeCore HLA` as the proof-of-concept assay.
- The pipeline should still be assay-agnostic so that a very different assay can be supported later without rewriting the core logic.
- Input is a `CSV` sample list with the columns `number`, `sample_id`, and `sample_name`.
- Output is a technician-facing `protocol.csv` intended for practical in-lab execution.
- The pipeline should attempt direct `PDF -> protocol` generation, while keeping intermediate artifacts available for review if results look wrong.

## Core Design

1. `PDF ingestion`
   Read the SeCore assay PDF documents and extract text, section structure, and tabular content.

2. `Protocol understanding`
   Use the model to convert the PDF content into a normalized internal assay representation, including:
   - workflow stages
   - ordered procedural steps
   - sample-dependent logic
   - quantities and constraints
   - branching conditions
   - instrument and run settings
   - warnings and cautions

3. `Run instantiation`
   Combine the assay representation with the daily sample CSV to create the actual run plan for that day.

4. `Validation`
   Check that the generated run is internally consistent:
   - all samples accounted for
   - steps are in a valid order
   - counts and quantities are coherent
   - required operational details are not missing

5. `CSV rendering`
   Write the technician-facing `protocol.csv`.
   - A very small number of structural fields can stay fixed, such as step identity/order.
   - All assay-specific operational headers are generated on the fly from the attributes actually present in the generated steps.
   - No hard-coded columns like `temperature` or `time` unless they are truly present in the interpreted protocol.

## Artifacts

- Final output: `protocol.csv`
- Review/debug artifact: structured intermediate output such as `assay_spec.json`

## Implementation Shape

1. Define internal schemas for assay spec, run input, generated steps, and validations.
2. Build PDF extraction for SeCore documents.
3. Build PDF-to-assay-spec generation.
4. Build sample CSV ingestion and run instantiation.
5. Build validation checks.
6. Build dynamic CSV header generation and final export.
7. Test across a few sample-count scenarios.

## Important Design Rules

- Avoid hard-coding SeCore-specific workflow rules in code.
- Allow configurable framework assumptions where needed, such as input column mapping and output paths.
- Keep intermediate structures inspectable so that wrong generations can be diagnosed instead of guessed at.
