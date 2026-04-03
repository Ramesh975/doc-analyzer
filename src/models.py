from pydantic import BaseModel, field_validator
from typing import List

class DocumentRequest(BaseModel):
    fileName: str
    fileType: str
    fileBase64: str

class EntitiesResponse(BaseModel):
    names: List[str] = []
    dates: List[str] = []
    organizations: List[str] = []
    amounts: List[str] = []

class AnalyzeResponse(BaseModel):
    status: str
    fileName: str
    summary: str
    entities: EntitiesResponse
    sentiment: str

    @field_validator('sentiment', mode='before')
    @classmethod
    def validate_sentiment(cls, v):
        allowed = ['Positive', 'Negative', 'Neutral']
        for a in allowed:
            if v and str(v).lower() == a.lower():
                return a
        return 'Neutral'