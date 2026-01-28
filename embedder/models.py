from pydantic import BaseModel, Field

class EmbeddingsResponse(BaseModel):
    embedding: list[float] = Field(..., description="Embedding of images")

class EmbeddingsRequest(BaseModel):
    images: list[str] | None = Field([], description="List of images in base64 format.")
    text: str | None = Field("", description="Text associated with the images.")