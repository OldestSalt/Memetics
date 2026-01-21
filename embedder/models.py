from pydantic import BaseModel, Field

class EmbeddingsResponse(BaseModel):
    embedding: list[float] = Field(..., description="Embedding of each image")