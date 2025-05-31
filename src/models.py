from pydantic import BaseModel, Field
from typing import Optional


class SearchResult(BaseModel):
    """Represents a single search result from EXA API."""

    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    published_date: Optional[str] = Field(None, description="Published date in ISO format")
    author: Optional[str] = Field(None, description="Author of the content")
    score: float = Field(..., description="Relevance score of the result")
    text: Optional[str] = Field(None, description="Extracted text content")
    summary: Optional[str] = Field(None, description="AI-generated summary")


# class SearchResponse(BaseModel):
#     """Represents the complete search response from EXA API."""

#     request_id: str = Field(..., description="Unique identifier for the request")
#     resolved_search_type: str = Field(..., description="Search type used for the request")
#     results: list[SearchResult] = Field(..., description="List of search results")
#     search_type: Optional[str] = Field(None, description="Original search type parameter")
#     cost_dollars: Optional[dict[str, Any]] = Field(None, description="Cost information")


class ExaSearchException(Exception):
    """Custom exception for EXA search errors."""

    pass


class ExtractionResult(BaseModel):
    """Holds the results of a content extraction operation."""

    url: str
    success: bool
    content: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None
