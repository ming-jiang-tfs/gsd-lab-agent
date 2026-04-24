import unittest
from pathlib import Path

from lab_protocol_agent.csv_input import load_sample_input
from lab_protocol_agent.extractors import HeuristicAssaySpecExtractor
from lab_protocol_agent.models import InstrumentId
from lab_protocol_agent.pdf_ingestion import load_assay_document
from lab_protocol_agent.protocol_generator import generate_protocol


ROOT = Path(__file__).resolve().parents[1]
ASSAY_PDF = ROOT / "input/example-assay-documents/SeCoreHLA_Assay/SeCoreHLA_kit_IFU_PI_QuickRef_OneLambda_MfgUserGuides/SEC-SEQK-PI-EN-01_RUO.pdf"
SAMPLES_CSV = ROOT / "examples/samples/example_samples.csv"


class ProtocolPipelineTest(unittest.TestCase):
    def test_pipeline_generates_protocol_steps(self) -> None:
        document = load_assay_document(ASSAY_PDF)
        sample_input = load_sample_input(SAMPLES_CSV)
        assay_spec = HeuristicAssaySpecExtractor().extract(document)
        protocol = generate_protocol(assay_spec, sample_input, InstrumentId.ABI_3500xL)

        self.assertEqual(protocol.total_samples, 3)
        self.assertTrue(any(step.title == "Run PCR amplification" for step in protocol.steps))
        self.assertTrue(
            any(
                step.attributes.get("instrument_parameters", {}).get("run_module") == "StdSeq50"
                for step in protocol.steps
            )
        )


if __name__ == "__main__":
    unittest.main()
