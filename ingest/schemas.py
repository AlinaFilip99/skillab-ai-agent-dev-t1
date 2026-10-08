from pydantic import BaseModel, Field, field_validator
from typing import  Literal, Any

DocType = Literal["invoice", "contract", "report", "letter", "other"]

class DocumentExtraction(BaseModel):
    filename: str = Field(description="Original file")
    content: str = Field(min_length=1, description="Extracted text")
    doc_type: DocType = Field(default="other")
    # extra_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content cannot be empty or whitespace-only")
        return v

    @field_validator("doc_type", mode="before")
    @classmethod
    def validate_doc_type(cls, v: Any) -> str:
        # valori necunoscute → 'other' (în loc să crape validarea)
        allowed = {"invoice", "contract", "report", "letter", "other"}
        return v if v in allowed else "other"

    def to_db_format(self) -> dict[str, Any]:
        # convertește la formatul cerut de DocumentRepository.create()
        return {
            "filename": self.filename,
            "content": self.content,
            "metadata": {"doc_type": self.doc_type},
        }

class ExtractionResult(BaseModel):
    success: bool
    document: DocumentExtraction | None = None
    error: str | None = None
