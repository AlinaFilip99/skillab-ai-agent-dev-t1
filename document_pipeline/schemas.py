from pydantic import BaseModel, Field
from typing import List

class Product(BaseModel):
    """Invoice product line item."""
    name: str
    quantity: int
    unit_price: float
    total: float

class Invoice(BaseModel):
    """Complete invoice."""
    number: str
    date: str
    client: str
    # Nested list — the LLM populates the structure automatically
    products: List[Product] = Field(default=[])
    total_amount: float

class Contract(BaseModel):
    """Complete contract."""

    number: str = Field(description="Contract number")
    signing_date: str = Field(description="Signing date")
    provider: str = Field(description="Provider name")
    recipient: str = Field(description="Recipient name")
    value: float = Field(description="Value in RON")
    duration_months: int = Field(description="Duration in months")

    obligations_provider: List[str] = Field(
        default=[],
        description="List of obligations for the provider",
    )
