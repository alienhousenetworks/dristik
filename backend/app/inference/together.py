"""
Dristik AI Inference Client (OpenAI-compatible / Multi-Provider)
Maintains backward compatibility with TogetherClient while supporting Gemini, Groq, OpenRouter, and Together AI.
"""
from app.inference.llm_client import LLMClient

# Direct alias so monkeypatching and type checks work identically
TogetherClient = LLMClient
