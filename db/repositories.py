from typing import Any
from sqlalchemy.orm import joinedload, Session
from sqlalchemy import func, update as sql_update, delete as sql_delete, select

from .models import Document, DocumentChunk

class DocumentError(Exception):
    """Base for Document errors"""


class DocumentNotFoundError(DocumentError):
    def __init__(self, doc_id: int) -> None:
        super().__init__(f"Document with id={doc_id} not found")
        self.doc_id = doc_id


class DuplicateDocumentError(DocumentError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"Document with filename='{filename}' already exists")
        self.filename = filename


class InvalidMetadataError(DocumentError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid metadata: {reason}")
        self.reason = reason

class DocumentRepository:
    # câmpuri permise la update — protecție împotriva mass assignment
    _UPDATABLE = {"filename", "content", "doc_metadata"}

    def __init__(self, db: Session) -> None:
        self.db = db

    # CREATE
    def create(self, filename: str, content: str, metadata: dict[str, Any]) -> Document:
        doc = Document(filename=filename, content=content, doc_metadata=metadata)  # 1. creează obiect
        self.db.add(doc)        # 2. adaugă în session (nu în DB încă)
        self.db.commit()        # 3. scrie în DB
        self.db.refresh(doc)    # 4. citește ID-ul generat înapoi
        return doc
    
    def create_batch(self, documents: list[dict[str, Any]]) -> list[Document]:
        docs = [Document(**d) for d in documents]
        self.db.add_all(docs)   # un singur INSERT batch, mult mai rapid decât N add()
        self.db.commit()
        for doc in docs:
            self.db.refresh(doc)
        return docs

    # READ
    def get_by_id(self, doc_id: int) -> Document | None:
        # API-ul modern SQLAlchemy: Session.get() folosește direct PK-ul
        return self.db.get(Document, doc_id)
    
    def get_by_filename(self, filename: str) -> Document | None:
        return self.db.query(Document).filter(Document.filename == filename).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> list[Document]:
        return (
            self.db.query(Document)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count(self) -> int:
        return self.db.query(func.count(Document.id)).scalar()

    def filter_by_metadata(self, key: str, value: str) -> list[Document]:
        # operatorul ->> din PostgreSQL: extrage field din JSONB ca text
        return (
            self.db.query(Document)
            .filter(Document.doc_metadata[key].astext == value)
            .all()
        )
    
    def search(self, query: str, limit: int = 20) -> list[Document]:
        # tsquery construit cu același dicționar ca search_vector → stemming consistent
        ts_query = func.plainto_tsquery("romanian", query)
        return (
            self.db.query(Document)
            .filter(Document.search_vector.op("@@")(ts_query))
            .order_by(func.ts_rank(Document.search_vector, ts_query).desc())
            .limit(limit)
            .all()
        )

    # UPDATE
    def update(self, doc_id: int, **fields: Any) -> Document | None:
        clean = {k: v for k, v in fields.items() if k in self._UPDATABLE}
        if not clean:
            return self.db.get(Document, doc_id)
        self.db.execute(sql_update(Document).where(Document.id == doc_id).values(**clean))
        self.db.commit()
        return self.db.get(Document, doc_id)
    
    def update_metadata(self, doc_id: int, metadata: dict[str, Any]) -> Document | None:
        # JSONB merge la nivel de DB (atomic) — operatorul || din PostgreSQL
        self.db.execute(
            sql_update(Document)
            .where(Document.id == doc_id)
            .values(doc_metadata=Document.doc_metadata.op("||")(metadata))
        )
        self.db.commit()
        return self.db.get(Document, doc_id)
    
    # DELETE
    def delete(self, doc_id: int) -> bool:
        result = self.db.execute(sql_delete(Document).where(Document.id == doc_id))
        self.db.commit()
        return result.rowcount > 0
    
    def delete_batch(self, doc_ids: list[int]) -> int:
        if not doc_ids:
            return 0
        result = self.db.execute(sql_delete(Document).where(Document.id.in_(doc_ids)))
        self.db.commit()
        return result.rowcount

    # safe methods — ridică excepții în loc să returneze None
    def get_by_id_safe(self, doc_id: int) -> Document:
        doc = self.db.get(Document, doc_id)
        if doc is None:
            raise DocumentNotFoundError(doc_id)
        return doc
    
    def create_safe(self, filename: str, content: str, metadata: dict) -> Document:
        if self.get_by_filename(filename) is not None:
            raise DuplicateDocumentError(filename)
        if not isinstance(metadata, dict):
            raise InvalidMetadataError("metadata must be a dict")
        return self.create(filename=filename, content=content, metadata=metadata)

class ChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # WRITE
    def create_chunk(
        self,
        document_id: int,
        content: str,
        chunk_index: int,
        embedding: list[float],
    ) -> DocumentChunk:
        doc = DocumentChunk(document_id=document_id, content=content, chunk_index=chunk_index, embedding=embedding)  # 1. creează obiect
        self.db.add(doc)        # 2. adaugă în session (nu în DB încă)
        self.db.commit()        # 3. scrie în DB
        self.db.refresh(doc)    # 4. citește ID-ul generat înapoi
        return doc

    def create_chunks_batch(self, chunks: list[dict]) -> list[DocumentChunk]:
        docs = [DocumentChunk(**c) for c in chunks]
        self.db.add_all(docs)   # un singur INSERT batch, mult mai rapid decât N add()
        self.db.commit()
        for doc in docs:
            self.db.refresh(doc)
        return docs

    # READ
    def get_document_chunks(self, document_id: int) -> list[DocumentChunk]:
        return self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    
    def get_chunk_by_id(self, chunk_id: int) -> DocumentChunk | None:
        return self.db.get(DocumentChunk, chunk_id)

    # SEARCH
    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        # 1 - (emb <=> q)  →  cosine distance convertit în similaritate [0, 1]
        similarity = (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("score")
    
        stmt = (
            select(DocumentChunk, similarity)
            .options(joinedload(DocumentChunk.document))   # eager load — evită N+1
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
    
        rows = self.db.execute(stmt).all()
        return [(chunk, float(score)) for chunk, score in rows]

    def search_with_threshold(
        self,
        query_embedding: list[float],
        min_score: float = 0.4,
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        # 1 - (emb <=> q) → cosine distance converted to similarity [0, 1]
        similarity = (
            1 - DocumentChunk.embedding.cosine_distance(query_embedding)
        ).label("score")

        stmt = (
            select(DocumentChunk, similarity)
            .options(joinedload(DocumentChunk.document))
            .where(similarity >= min_score)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )

        rows = self.db.execute(stmt).all()

        return [(chunk, float(score)) for chunk, score in rows]
