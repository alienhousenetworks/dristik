"""
Dristik AI Embedding Service
Supports:
1. Local Hugging Face E5-Small (intfloat/e5-small-v2) (~130 MB, 384-dim) [Default]
2. OpenRouter Remote E5-Small / Embedding API
Adheres strictly to E5 specification with 'passage: ' and 'query: ' prefixes.
"""
import os
import time
import logging
import hashlib
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger("dristik.embedding_service")


class EmbeddingService:
    def __init__(self):
        self._local_model = None
        self._local_model_name: Optional[str] = None
        self._cache: Dict[str, List[float]] = {}
        self._max_cache_size = 2000

    def _get_cache_key(self, text: str, prefix: str) -> str:
        return hashlib.sha256(f"{prefix}:{text}".encode("utf-8")).hexdigest()

    def _load_local_model(self):
        """Lazy loads SentenceTransformer model."""
        target_model = settings.EMBEDDING_MODEL or "intfloat/e5-small-v2"
        if self._local_model is not None and self._local_model_name == target_model:
            return self._local_model

        device = settings.EMBEDDING_DEVICE or "cpu"
        if device == "auto":
            try:
                import torch
                if torch.backends.mps.is_available():
                    device = "mps"
                elif torch.cuda.is_available():
                    device = "cuda"
                else:
                    device = "cpu"
            except Exception:
                device = "cpu"

        try:
            from sentence_transformers import SentenceTransformer
            hf_token = settings.HF_TOKEN or settings.HUGGINGFACE_TOKEN or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
            if hf_token:
                os.environ["HF_TOKEN"] = hf_token
                os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token

            logger.info("[EmbeddingService] Loading local Hugging Face model '%s' on %s...", target_model, device)
            try:
                # Try loading from local HuggingFace cache first (instant, 0s delay)
                self._local_model = SentenceTransformer(target_model, device=device, model_kwargs={"local_files_only": True})
            except Exception:
                # If not yet in cache, fetch authenticated from Hugging Face Hub
                extra_kwargs = {"token": hf_token} if hf_token else {}
                self._local_model = SentenceTransformer(target_model, device=device, **extra_kwargs)
            self._local_model_name = target_model
            logger.info("[EmbeddingService] Successfully loaded local model '%s'", target_model)
            return self._local_model
        except ImportError:
            logger.warning("[EmbeddingService] sentence-transformers not installed. Install with: pip install sentence-transformers")
            return None
        except Exception as exc:
            logger.error("[EmbeddingService] Failed to load local model '%s': %s", target_model, exc)
            return None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of document passages. E5 requires 'passage: ' prefix.
        """
        if not texts:
            return []

        provider = (settings.EMBEDDING_PROVIDER or "huggingface").lower().strip()
        prefixed = [f"passage: {t.strip()}" for t in texts]

        # 1. Local Hugging Face (Default)
        if provider in ("huggingface", "local"):
            model = self._load_local_model()
            if model is not None:
                try:
                    embeddings = model.encode(
                        prefixed,
                        batch_size=settings.EMBEDDING_BATCH_SIZE or 32,
                        normalize_embeddings=True,
                        show_progress_bar=False
                    )
                    return [list(map(float, vec)) for vec in embeddings]
                except Exception as exc:
                    logger.error("[EmbeddingService] Local embedding generation failed: %s", exc)

        # 2. OpenRouter / Remote Provider
        return self._embed_remote_sync(prefixed)

    def embed_query(self, query: str) -> List[float]:
        """
        Embeds a search query or intent. E5 requires 'query: ' prefix.
        """
        if not query or not query.strip():
            return [0.0] * 1024

        clean_q = query.strip()
        cache_key = self._get_cache_key(clean_q, "query")
        if cache_key in self._cache:
            return self._cache[cache_key]

        provider = (settings.EMBEDDING_PROVIDER or "huggingface").lower().strip()
        prefixed = [f"query: {clean_q}"]

        vector: List[float] = []
        # 1. Local Hugging Face
        if provider in ("huggingface", "local"):
            model = self._load_local_model()
            if model is not None:
                try:
                    vecs = model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
                    vector = [float(x) for x in vecs[0]]
                except Exception as exc:
                    logger.error("[EmbeddingService] Local query embedding failed: %s", exc)

        # 2. Remote OpenRouter if local failed or remote configured
        if not vector:
            remote_vecs = self._embed_remote_sync(prefixed)
            if remote_vecs:
                vector = remote_vecs[0]

        # Fail closed: never fabricate pseudo-embeddings when neural models are offline
        if not vector:
            logger.warning("[EmbeddingService] Neural embedding unavailable for query: %s", clean_q[:40])
            return []

        # Cache vector
        if len(self._cache) < self._max_cache_size:
            self._cache[cache_key] = vector
        return vector

    def is_available(self) -> bool:
        """Returns True if a real neural embedding model (local or remote API) is configured and available."""
        provider = (settings.EMBEDDING_PROVIDER or "huggingface").lower().strip()
        if provider in ("huggingface", "local"):
            if self._local_model is not None:
                return True
            try:
                from sentence_transformers import SentenceTransformer
                target_model = settings.EMBEDDING_MODEL or "intfloat/e5-small-v2"
                self._local_model = SentenceTransformer(target_model, local_files_only=True)
                return True
            except Exception:
                return False
        api_key = settings.EMBEDDING_API_KEY or settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY")
        return bool(api_key)

    async def embed_query_async(self, query: str) -> List[float]:
        """Async version of embed_query."""
        return self.embed_query(query)

    async def embed_documents_async(self, texts: List[str]) -> List[List[float]]:
        """Async version of embed_documents."""
        provider = (settings.EMBEDDING_PROVIDER or "huggingface").lower().strip()
        if provider in ("openrouter", "remote"):
            prefixed = [f"passage: {t.strip()}" for t in texts]
            return await self._embed_remote_async(prefixed)
        return self.embed_documents(texts)

    def _embed_remote_sync(self, prefixed_texts: List[str]) -> List[List[float]]:
        """Calls OpenRouter or OpenAI-compatible remote embedding endpoint synchronously."""
        api_key = settings.EMBEDDING_API_KEY or settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning("[EmbeddingService] No API key available for remote embedding provider.")
            return []

        base_url = (settings.EMBEDDING_BASE_URL or "https://openrouter.ai/api/v1").rstrip("/")
        endpoint = f"{base_url}/embeddings"
        model = settings.EMBEDDING_MODEL or "intfloat/e5-small-v2"

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://dristik.ai",
                        "X-Title": "Dristik AI Embedding Service"
                    },
                    json={
                        "model": model,
                        "input": prefixed_texts
                    }
                )
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    return [item["embedding"] for item in sorted(data, key=lambda x: x.get("index", 0))]
                logger.error("[EmbeddingService] Remote embedding failed with HTTP %d: %s", res.status_code, res.text)
        except Exception as exc:
            logger.error("[EmbeddingService] Remote embedding request error: %s", exc)

        return []

    async def _embed_remote_async(self, prefixed_texts: List[str]) -> List[List[float]]:
        """Calls OpenRouter or OpenAI-compatible remote embedding endpoint asynchronously."""
        api_key = settings.EMBEDDING_API_KEY or settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return []

        base_url = (settings.EMBEDDING_BASE_URL or "https://openrouter.ai/api/v1").rstrip("/")
        endpoint = f"{base_url}/embeddings"
        model = settings.EMBEDDING_MODEL or "intfloat/e5-small-v2"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://dristik.ai",
                        "X-Title": "Dristik AI Embedding Service"
                    },
                    json={
                        "model": model,
                        "input": prefixed_texts
                    }
                )
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    return [item["embedding"] for item in sorted(data, key=lambda x: x.get("index", 0))]
                logger.error("[EmbeddingService] Async remote embedding HTTP %d: %s", res.status_code, res.text)
        except Exception as exc:
            logger.error("[EmbeddingService] Async remote embedding error: %s", exc)

        return []

    def _get_target_dim(self) -> int:
        model = (settings.EMBEDDING_MODEL or "intfloat/e5-small-v2").lower()
        if "large" in model or "1024" in model:
            return 1024
        if "base" in model or "768" in model:
            return 768
        return 384



embedding_service = EmbeddingService()
