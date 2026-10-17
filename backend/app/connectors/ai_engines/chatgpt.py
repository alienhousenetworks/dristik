"""ChatGPT model API adapter. Not a consumer search-product query."""
from app.intelligence.geo.adapters.openai_search import OpenAISearchAdapter

ChatGptAdapter = OpenAISearchAdapter

__all__ = ["ChatGptAdapter", "OpenAISearchAdapter"]
