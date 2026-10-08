import pprint
import logging
from pathlib import Path
from .loaders import load_document
from .schemas import ExtractionResult
from .extraction import ExtractionService
from .schemas import DocumentExtraction
from .chunking import ChunkConfig
from db import transaction, DocumentRepository, ChunkRepository
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extract structured metadata from the document below.

Filename: {filename}

Content:
{content}
"""

EMB_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

class ExtractionPipeline:
    _emb_model: SentenceTransformer | None = None   # singleton per proces

    def __init__(self) -> None:
        self.extract = ExtractionService()
        self.chunk_config = ChunkConfig(800, 100)

    @property
    def emb_model(self) -> SentenceTransformer:
        # lazy + shared: modelul (~80MB) se încarcă o singură dată per proces
        if ExtractionPipeline._emb_model is None:
            ExtractionPipeline._emb_model = SentenceTransformer(EMB_MODEL_NAME)
        return ExtractionPipeline._emb_model

    def process_document(self, path: str | Path) -> ExtractionResult:
        path = Path(path)
    
        # 1. Load
        docs = None
        try:
            docs = load_document(path)
        except FileNotFoundError:
            logger.error("File not found")
        except ValueError:
            logger.error("Unsupported format")
        except UnicodeDecodeError:
            logger.error("Invalid encoding")

        if docs is None:
            return ExtractionResult(success=False, error=f"load failed: {path.name}")
        
        # chunk document if needed
        chunks = None
        full_content = "\n\n".join(d.page_content for d in docs)
        if self.chunk_config.should_chunk(full_content, 800):
            chunks = self.chunk_config.chunk_documents(docs)
        
        # 2. Extract + Validate (Pydantic via response_schema)
        extraction_result = self.extract.extract_metadata(DocumentExtraction, full_content[:200], path.name)
        if extraction_result is None:
            return ExtractionResult(success=False, error=f"extract failed: {path.name}")
    
        # 3. Save — idempotent: dacă filename există deja, skip
        with transaction() as db:
            repo = DocumentRepository(db)
            existing = repo.get_by_filename(path.name)
            if existing is not None:
                logger.info("Skip duplicate: %s (id=%d)", path.name, existing.id)
                return ExtractionResult(success=True, document=extraction_result)
    
            doc = repo.create(**extraction_result.to_db_format())
            
            # save chunks
            if chunks is not None:
                chunk_repo = ChunkRepository(db)
                for i, chunk in enumerate(chunks):
                    chunk_content = chunk.page_content
                    emb = self.emb_model.encode(chunk_content)
                    chunk_repo.create_chunk(doc.id, chunk_content, i, emb)

            logger.info("Saved %s (id=%d)", path.name, doc.id)
            return ExtractionResult(success=True, document=extraction_result)

    def process_batch(self, paths: list[str | Path]) -> list[ExtractionResult]:
        results: list[ExtractionResult] = []
        for path in paths:
            try:
                results.append(self.process_document(path))
            except Exception as e:
                # safety net — eroare neașteptată nu oprește batch-ul
                logger.exception("Unexpected error on %s", path)
                results.append(ExtractionResult(success=False, error=str(e)))
        return results
