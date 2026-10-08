import json
import pprint
from typing import Type
from pathlib import Path

from google import genai
from pydantic import BaseModel, ValidationError
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from .schemas import Invoice, Contract
from .loader import load_document

EXTRACTION_REGISTRY = {
    Invoice: {
        "chunk_size": None, # Nu chunk-ui facturi
    },
    Contract: {
        "chunk_size": 2000,
    },
}

class ExtractionPipeline:
    """Complete pipeline for document extraction: load, chunk, extract."""

    def __init__(self, model: str = "gemini-3.5-flash-lite"):
        self.model = model
        self._client: genai.Client | None = None   # lazy

    @property
    def client(self) -> genai.Client:
        # Inițializat per proces — clientul nu e pickle-able
        if self._client is None:
            self._client = genai.Client()
        return self._client

    def chunk_documents(self, docs: list[Document], chunk_size: int) -> list[Document]:
        """Split documents into smaller chunks."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_size // 10  # 10% overlap,
            )
        chunks = splitter.split_documents(docs)
        return chunks

    def process(self, file_path: str, schema: Type[BaseModel]):
        config = EXTRACTION_REGISTRY[schema]
        # 1. Load
        try:
            docs = load_document(file_path)
        except FileNotFoundError:
            print("File not found")
        except ValueError as e:
            print(e)                      # Tip nesuportat: .xlsx
        except UnicodeDecodeError:
            print("Invalid encoding")

        # 2. Chunk dacă e necesar
        if config["chunk_size"]:
            docs = self.chunk_documents(docs, config["chunk_size"])

        # 3. Extract
        responses = []
        for doc in docs:
            text = doc.page_content
            for attempt in range(3):
                try:
                    responses += [self.client.models.generate_content(
                        model=self.model,
                        contents=text,
                        config={
                            "response_mime_type": "application/json",
                            "response_schema": schema,
                        },
                    )]
                    break  # validarea a trecut → ieșim din loop
                except ValidationError as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                except Exception as e:
                    print(f"General error: {e}")
                    break  # erori de rețea/API → nu mai retry-uim

        self.save_json(responses, schema.__name__)

        return responses

    def save_json(self, responses: list, doc_type: str):
        try:
            data = []

            for res in responses:
                dict = res.model_dump(mode='json')
                
                # merge data into response
                dict_data=dict['parsed']
                data.append(dict_data)
            
            if len(data) == 0:
                return
        
            out = Path("extracted_data") / doc_type
            out.mkdir(parents=True, exist_ok=True)
            filename = f"{data[0]['number'].replace('/', '_')}.json"
            with open(out / filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(e)
