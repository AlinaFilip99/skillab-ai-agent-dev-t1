import pprint
import logging
from google import genai
from typing import Type
from pydantic import BaseModel
from langchain_core.documents import Document
from .chunking import ChunkConfig
# from .schemas import DocumentExtraction

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extract structured metadata from the document below.

Filename: {filename}

Content:
{content}
"""

class ExtractionService:
    def __init__(self, model: str = "gemini-3.5-flash-lite") -> None:
        self.model = model
        self.chunk_config= ChunkConfig(2000, 200)
        self._client: genai.Client | None = None  # lazy

    @property
    def client(self) -> genai.Client:
        # init per proces — clientul nu e pickle-able
        if self._client is None:
            self._client = genai.Client()
        return self._client

    def extract_metadata(self, schema: Type[BaseModel], content: str, filename: str,) -> BaseModel | None:
        prompt = EXTRACTION_PROMPT.format(filename=filename, content=content)
        pprint.pprint(schema)
        try:
            response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                    },
                )
            # SDK validează deja schema; .parsed returnează instanța Pydantic
            extraction = response.parsed
            extraction.filename = filename       # asigurăm filename-ul real
            extraction.content = content         # full content, nu trunchierea
            return extraction
        except Exception as e:
            pprint.pprint(e)
            logger.error("LLM extraction failed for %s: %s", filename, e)
            return None


