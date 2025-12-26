# =============================================================================
# CLOPUS v3 Embedding Engine
# =============================================================================
"""
Embedding generation for semantic search in long-term memory.
Uses sentence-transformers for local embeddings.
"""

import asyncio
from typing import List, Optional
from functools import lru_cache
import hashlib


class EmbeddingEngine:
    """Generate embeddings for semantic search."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_size: int = 10000
    ):
        self.model_name = model_name
        self._model = None
        self._lock = asyncio.Lock()
        self._cache: dict = {}
        self._cache_size = cache_size

    async def _load_model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            async with self._lock:
                if self._model is None:
                    # Import here to avoid slow startup
                    from sentence_transformers import SentenceTransformer
                    self._model = SentenceTransformer(self.model_name)

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        await self._load_model()

        # Check cache
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Generate embedding
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self._model.encode(text, convert_to_numpy=True).tolist()
        )

        # Cache result
        if len(self._cache) < self._cache_size:
            self._cache[cache_key] = embedding

        return embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        await self._load_model()

        # Check cache for existing embeddings
        results = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []

        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
            else:
                texts_to_embed.append(text)
                indices_to_embed.append(i)

        # Generate missing embeddings
        if texts_to_embed:
            loop = asyncio.get_event_loop()
            new_embeddings = await loop.run_in_executor(
                None,
                lambda: self._model.encode(texts_to_embed, convert_to_numpy=True).tolist()
            )

            # Fill in results and cache
            for idx, embedding in zip(indices_to_embed, new_embeddings):
                results[idx] = embedding
                cache_key = self._get_cache_key(texts[idx])
                if len(self._cache) < self._cache_size:
                    self._cache[cache_key] = embedding

        return results

    async def similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        import numpy as np

        emb1 = await self.embed(text1)
        emb2 = await self.embed(text2)

        # Cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    async def find_most_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5
    ) -> List[tuple]:
        """Find most similar texts from candidates."""
        import numpy as np

        query_embedding = await self.embed(query)
        candidate_embeddings = await self.embed_batch(candidates)

        # Calculate similarities
        similarities = []
        for i, emb in enumerate(candidate_embeddings):
            dot_product = np.dot(query_embedding, emb)
            norm_q = np.linalg.norm(query_embedding)
            norm_c = np.linalg.norm(emb)
            if norm_q > 0 and norm_c > 0:
                sim = dot_product / (norm_q * norm_c)
            else:
                sim = 0.0
            similarities.append((candidates[i], float(sim), i))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()

    @property
    def embedding_dimension(self) -> int:
        """Get the embedding dimension."""
        # Common dimensions for sentence-transformers models
        dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "all-distilroberta-v1": 768,
            "paraphrase-MiniLM-L6-v2": 384,
        }
        return dimensions.get(self.model_name, 384)


class CodeEmbeddingEngine(EmbeddingEngine):
    """Specialized embedding engine for code."""

    def __init__(
        self,
        model_name: str = "microsoft/codebert-base",
        cache_size: int = 10000
    ):
        # Note: CodeBERT may need different handling
        # Fallback to general model for now
        super().__init__("all-MiniLM-L6-v2", cache_size)
        self.code_model_name = model_name

    async def embed_code(self, code: str, language: Optional[str] = None) -> List[float]:
        """Generate embedding for code with optional language context."""
        # Add language prefix for context
        if language:
            text = f"[{language}]\n{code}"
        else:
            text = code
        return await self.embed(text)

    async def embed_function(
        self,
        function_name: str,
        function_body: str,
        docstring: Optional[str] = None,
        language: Optional[str] = None
    ) -> List[float]:
        """Generate embedding for a function."""
        parts = [f"Function: {function_name}"]
        if language:
            parts.append(f"Language: {language}")
        if docstring:
            parts.append(f"Description: {docstring}")
        parts.append(f"Code:\n{function_body}")

        text = "\n".join(parts)
        return await self.embed(text)
