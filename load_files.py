import logging
from ingest import ExtractionPipeline

logger = logging.getLogger(__name__)


pipe = ExtractionPipeline()
results = pipe.process_batch(["rag_docs/EACR_Terms_and_Conditions.pdf"])

successful = [r for r in results if r.success]
failed = [r for r in results if not r.success]

logger.info("Batch done: %d ok, %d failed", len(successful), len(failed))
for r in failed:
    logger.error("Failed: %s", r.error)

