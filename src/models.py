# Pydantic request/response schemas

# models.py
from pydantic import BaseModel
from typing import List, Optional

class Entity(BaseModel):
    text: str
    type: str   # PERSON | ORG | DATE | MONEY | LOCATION | OTHER

class Sentiment(BaseModel):
    label: str  # positive | negative | neutral
    score: float

class AnalyzeResponse(BaseModel):
    filename: Optional[str] = None
    summary: str
    entities: List[Entity]
    sentiment: Sentiment
    word_count: Optional[int] = None
