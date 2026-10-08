from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class ChunkConfig:
    """Complete pipeline for document extraction: load, chunk, extract."""

    def __init__(self, size: int, overlap: int, separators: list[str] | None = None):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=size, chunk_overlap=overlap, separators=separators, length_function=len
            )

    def should_chunk(self, content: str, max_size: int = 4000) -> bool:
            """Decide if the document should be chunked"""
            return len(content) > max_size

    def chunk_documents(self, docs: list[Document]) -> list[Document]:
        """Split documents into smaller chunks."""
        chunks = self.splitter.split_documents(docs)
        return chunks
    