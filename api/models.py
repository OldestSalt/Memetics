from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    text: str | None = Field("", description="Optional text associated with the image.")
    images: list[str] | None = Field([], description="Optional list of images in base64 format.")
    k: int | None = Field(5, description="Number of the nearest results to return.")

class SearchResult(BaseModel):
    images: list[str] | None = Field([], description="Optional image in base64 format.")
    text: str | None = Field("", description="Optional text associated with the image.")
    score: float = Field(..., description="Similarity of the image related to search query.")

class SearchResponse(BaseModel):
    results: list[SearchResult] = Field(..., description="List of search results.")