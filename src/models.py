from typing import Optional
from pydantic import BaseModel, Field

class MatchRequest(BaseModel):
    record1: dict = Field(..., description="First customer record")
    record2: dict = Field(..., description="Second customer record")

class MatchResponse(BaseModel):
    match: bool
    confidence: float
    reason: Optional[str] = None
