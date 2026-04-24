# Lab Protocol Agent

This repository contains a proof-of-concept pipeline that generates a technician-facing `protocol.csv` from:

- an assay instruction PDF
- a daily sample CSV
- an explicit instrument input

The current v1 target assay is SeCore HLA using:

- `input/example-assay-documents/SeCoreHLA_Assay/SeCoreHLA_kit_IFU_PI_QuickRef_OneLambda_MfgUserGuides/SEC-SEQK-PI-EN-01_RUO.pdf`

## Quick Start

Install in editable mode:

```bash
python -m pip install -e .
```

Run the pipeline:

```bash
lab-protocol-agent \
  --assay-pdf input/example-assay-documents/SeCoreHLA_Assay/SeCoreHLA_kit_IFU_PI_QuickRef_OneLambda_MfgUserGuides/SEC-SEQK-PI-EN-01_RUO.pdf \
  --samples-csv examples/samples/example_samples.csv \
  --instrument ABI_3500xL \
  --output-dir outputs/example-run
```

To enable the OpenAI-backed extraction path, install the optional dependency and set `OPENAI_API_KEY`:

```bash
python -m pip install -e '.[openai]'
export OPENAI_API_KEY=...
```

The pipeline writes:

- `assay_spec.json`
- `protocol.json`
- `protocol.csv`
