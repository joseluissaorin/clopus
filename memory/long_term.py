# =============================================================================
# CLOPUS v3 Long-Term Memory (ChromaDB)
# =============================================================================
"""
ChromaDB-based long-term memory for semantic search and learning.
Stores learnings, patterns, solutions, and reusable knowledge.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import chromadb
from chromadb.config import Settings

from .embeddings import EmbeddingEngine


def _safe_enum_value(val):
    """Safely get the string value from an Enum or pass through a string."""
    return val.value if hasattr(val, 'value') else str(val)


class MemoryType(str, Enum):
    LEARNING = "learning"           # What worked, what didn't
    PATTERN = "pattern"             # Recognized coding patterns
    SOLUTION = "solution"           # Complete solutions to problems
    ERROR_FIX = "error_fix"         # How errors were resolved
    DECISION = "decision"           # Important decisions and outcomes
    SKILL = "skill"                 # Skill-related knowledge
    TEMPLATE = "template"           # Template-related knowledge
    API = "api"                     # API documentation and usage
    CODEBASE = "codebase"           # Codebase knowledge


@dataclass
class Memory:
    id: str
    memory_type: MemoryType
    content: str
    metadata: Dict
    embedding: Optional[List[float]] = None
    created_at: Optional[str] = None
    relevance_score: Optional[float] = None


class LongTermMemory:
    """ChromaDB-based long-term memory manager with graceful degradation."""

    def __init__(
        self,
        host: str = "chromadb",
        port: int = 8000,
        embedding_engine: Optional[EmbeddingEngine] = None
    ):
        self.host = host
        self.port = port
        self._client: Optional[chromadb.HttpClient] = None
        self._collections: Dict[str, chromadb.Collection] = {}
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self._lock = asyncio.Lock()

        # Fallback mode when ChromaDB is unavailable
        self._fallback_mode = False
        self._fallback_storage: Dict[str, List[Dict]] = {}

        # Logging
        import logging
        self._logger = logging.getLogger("clopus.long_term_memory")

    async def initialize(self) -> None:
        """Initialize ChromaDB connection with retry and fallback."""
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self._client = chromadb.HttpClient(
                    host=self.host,
                    port=self.port,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )

                # Test connection with heartbeat
                self._client.heartbeat()
                self._logger.info(f"ChromaDB connected successfully on attempt {attempt + 1}")
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    self._logger.warning(
                        f"ChromaDB connection attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {retry_delay * (2 ** attempt)}s..."
                    )
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    self._logger.error(
                        f"ChromaDB unavailable after {max_retries} attempts. "
                        "Entering fallback mode with in-memory storage."
                    )
                    self._fallback_mode = True
                    self._fallback_storage = {
                        "learnings": [],
                        "patterns": [],
                        "solutions": [],
                        "error_fixes": [],
                        "decisions": [],
                        "skills": [],
                        "templates": [],
                        "apis": [],
                        "codebases": []
                    }
                    return

        # Create collections for different memory types
        collection_configs = {
            "learnings": "Learnings from completed tasks and projects",
            "patterns": "Recognized coding patterns and best practices",
            "solutions": "Complete solutions to problems",
            "error_fixes": "Error resolutions and debugging steps",
            "decisions": "Important decisions and their outcomes",
            "skills": "Skill-related knowledge and capabilities",
            "templates": "Template-related knowledge",
            "apis": "API documentation and usage examples",
            "codebases": "Codebase knowledge and structure"
        }

        for name, description in collection_configs.items():
            try:
                self._collections[name] = self._client.get_or_create_collection(
                    name=f"clopus_{name}",
                    metadata={"description": description}
                )
            except Exception as e:
                self._logger.error(f"Failed to create collection {name}: {e}")
                self._collections[name] = None

    def is_available(self) -> bool:
        """Check if ChromaDB is available (not in fallback mode)."""
        return not self._fallback_mode

    def _get_collection(self, memory_type: MemoryType) -> chromadb.Collection:
        """Get collection for memory type."""
        mapping = {
            MemoryType.LEARNING: "learnings",
            MemoryType.PATTERN: "patterns",
            MemoryType.SOLUTION: "solutions",
            MemoryType.ERROR_FIX: "error_fixes",
            MemoryType.DECISION: "decisions",
            MemoryType.SKILL: "skills",
            MemoryType.TEMPLATE: "templates",
            MemoryType.API: "apis",
            MemoryType.CODEBASE: "codebases"
        }
        return self._collections[mapping[memory_type]]

    # =========================================================================
    # STORE MEMORIES
    # =========================================================================

    async def store(
        self,
        memory_type: MemoryType,
        content: str,
        metadata: Optional[Dict] = None,
        memory_id: Optional[str] = None
    ) -> str:
        """Store a memory with embedding."""
        memory_id = memory_id or str(uuid.uuid4())
        metadata = metadata or {}
        metadata["created_at"] = datetime.now().isoformat()
        metadata["memory_type"] = _safe_enum_value(memory_type)

        # Convert lists to comma-separated strings (ChromaDB only accepts primitives)
        for key, value in list(metadata.items()):
            if isinstance(value, list):
                metadata[key] = ",".join(str(v) for v in value) if value else ""
            elif value is None:
                metadata[key] = ""

        # Fallback mode - store in memory
        if self._fallback_mode:
            collection_name = self._get_collection_name(memory_type)
            self._fallback_storage[collection_name].append({
                "id": memory_id,
                "content": content,
                "metadata": metadata
            })
            self._logger.debug(f"Stored memory {memory_id} in fallback storage")
            return memory_id

        # Generate embedding
        embedding = await self.embedding_engine.embed(content)

        # Store in ChromaDB
        collection = self._get_collection(memory_type)
        if collection is None:
            self._logger.warning(f"Collection for {memory_type} is None, using fallback")
            collection_name = self._get_collection_name(memory_type)
            self._fallback_storage.setdefault(collection_name, []).append({
                "id": memory_id,
                "content": content,
                "metadata": metadata
            })
            return memory_id

        try:
            async with self._lock:
                collection.add(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[metadata]
                )
        except Exception as e:
            self._logger.error(f"Failed to store in ChromaDB: {e}, using fallback")
            collection_name = self._get_collection_name(memory_type)
            self._fallback_storage.setdefault(collection_name, []).append({
                "id": memory_id,
                "content": content,
                "metadata": metadata
            })

        return memory_id

    def _get_collection_name(self, memory_type: MemoryType) -> str:
        """Get collection name for memory type."""
        mapping = {
            MemoryType.LEARNING: "learnings",
            MemoryType.PATTERN: "patterns",
            MemoryType.SOLUTION: "solutions",
            MemoryType.ERROR_FIX: "error_fixes",
            MemoryType.DECISION: "decisions",
            MemoryType.SKILL: "skills",
            MemoryType.TEMPLATE: "templates",
            MemoryType.API: "apis",
            MemoryType.CODEBASE: "codebases"
        }
        return mapping[memory_type]

    async def store_learning(
        self,
        content: str,
        task_id: Optional[str] = None,
        objective_id: Optional[str] = None,
        outcome: str = "success",
        tags: Optional[List[str]] = None
    ) -> str:
        """Store a learning from a task or project."""
        metadata = {
            "task_id": task_id,
            "objective_id": objective_id,
            "outcome": outcome,
            "tags": tags or []
        }
        return await self.store(MemoryType.LEARNING, content, metadata)

    async def store_pattern(
        self,
        pattern_name: str,
        description: str,
        example_code: str,
        language: str,
        tags: Optional[List[str]] = None
    ) -> str:
        """Store a coding pattern."""
        content = f"Pattern: {pattern_name}\n\nDescription: {description}\n\nExample:\n```{language}\n{example_code}\n```"
        metadata = {
            "pattern_name": pattern_name,
            "language": language,
            "tags": tags or []
        }
        return await self.store(MemoryType.PATTERN, content, metadata)

    async def store_solution(
        self,
        problem: str,
        solution: str,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Store a complete solution."""
        content = f"Problem: {problem}\n\nSolution:\n{solution}"
        metadata = {
            "problem": problem[:200],  # Truncate for metadata
            "language": language,
            "framework": framework,
            "tags": tags or []
        }
        return await self.store(MemoryType.SOLUTION, content, metadata)

    async def store_error_fix(
        self,
        error_message: str,
        error_context: str,
        fix: str,
        language: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Store an error fix."""
        content = f"Error: {error_message}\n\nContext: {error_context}\n\nFix:\n{fix}"
        metadata = {
            "error_type": error_message[:100],
            "language": language,
            "tags": tags or []
        }
        return await self.store(MemoryType.ERROR_FIX, content, metadata)

    async def store_decision(
        self,
        decision: str,
        reasoning: str,
        outcome: str,
        context: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Store a decision with its outcome."""
        content = f"Decision: {decision}\n\nReasoning: {reasoning}\n\nOutcome: {outcome}"
        if context:
            content = f"Context: {context}\n\n{content}"
        metadata = {
            "decision_summary": decision[:200],
            "outcome": outcome,
            "tags": tags or []
        }
        return await self.store(MemoryType.DECISION, content, metadata)

    async def store_api_knowledge(
        self,
        api_name: str,
        endpoint: str,
        description: str,
        example_usage: str,
        tags: Optional[List[str]] = None
    ) -> str:
        """Store API knowledge."""
        content = f"API: {api_name}\nEndpoint: {endpoint}\n\nDescription: {description}\n\nExample:\n{example_usage}"
        metadata = {
            "api_name": api_name,
            "endpoint": endpoint,
            "tags": tags or []
        }
        return await self.store(MemoryType.API, content, metadata)

    async def store_codebase_knowledge(
        self,
        project_name: str,
        knowledge_type: str,
        content: str,
        file_paths: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Store codebase knowledge."""
        full_content = f"Project: {project_name}\nKnowledge Type: {knowledge_type}\n\n{content}"
        metadata = {
            "project_name": project_name,
            "knowledge_type": knowledge_type,
            "file_paths": file_paths or [],
            "tags": tags or []
        }
        return await self.store(MemoryType.CODEBASE, full_content, metadata)

    # =========================================================================
    # SEARCH MEMORIES
    # =========================================================================

    async def search(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        n_results: int = 10,
        where: Optional[Dict] = None,
        min_relevance: float = 0.0
    ) -> List[Memory]:
        """Search memories by semantic similarity."""
        # Fallback mode - simple text matching
        if self._fallback_mode:
            return self._fallback_search(query, memory_type, n_results)

        # Generate query embedding
        query_embedding = await self.embedding_engine.embed(query)

        if memory_type:
            # Search specific collection
            collection = self._get_collection(memory_type)
            collections = [collection] if collection else []
        else:
            # Search all collections (skip None collections)
            collections = [c for c in self._collections.values() if c is not None]

        if not collections:
            self._logger.warning("No collections available, using fallback search")
            return self._fallback_search(query, memory_type, n_results)

        all_results = []

        for collection in collections:
            try:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where
                )

                if results and results["ids"] and results["ids"][0]:
                    for i, doc_id in enumerate(results["ids"][0]):
                        distance = results["distances"][0][i] if results["distances"] else 0
                        relevance = 1 - distance  # Convert distance to relevance

                        if relevance >= min_relevance:
                            memory = Memory(
                                id=doc_id,
                                memory_type=MemoryType(results["metadatas"][0][i].get("memory_type", "learning")),
                                content=results["documents"][0][i],
                                metadata=results["metadatas"][0][i],
                                relevance_score=relevance
                            )
                            all_results.append(memory)
            except Exception as e:
                self._logger.error(f"Error searching collection: {e}")
                continue

        # Sort by relevance and limit
        all_results.sort(key=lambda x: x.relevance_score or 0, reverse=True)
        return all_results[:n_results]

    def _fallback_search(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        n_results: int = 10
    ) -> List[Memory]:
        """Simple text-based search for fallback mode."""
        query_lower = query.lower()
        all_results = []

        if memory_type:
            collection_names = [self._get_collection_name(memory_type)]
        else:
            collection_names = list(self._fallback_storage.keys())

        for collection_name in collection_names:
            items = self._fallback_storage.get(collection_name, [])
            for item in items:
                content = item.get("content", "")
                # Simple word overlap scoring
                content_lower = content.lower()
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                if overlap > 0:
                    relevance = overlap / max(len(query_words), 1)
                    memory = Memory(
                        id=item.get("id", ""),
                        memory_type=MemoryType(item.get("metadata", {}).get("memory_type", "learning")),
                        content=content,
                        metadata=item.get("metadata", {}),
                        relevance_score=relevance
                    )
                    all_results.append(memory)

        # Sort by relevance
        all_results.sort(key=lambda x: x.relevance_score or 0, reverse=True)
        return all_results[:n_results]

    async def search_learnings(
        self,
        query: str,
        outcome: Optional[str] = None,
        n_results: int = 5
    ) -> List[Memory]:
        """Search learnings."""
        where = {"outcome": outcome} if outcome else None
        return await self.search(query, MemoryType.LEARNING, n_results, where)

    async def search_patterns(
        self,
        query: str,
        language: Optional[str] = None,
        n_results: int = 5
    ) -> List[Memory]:
        """Search coding patterns."""
        where = {"language": language} if language else None
        return await self.search(query, MemoryType.PATTERN, n_results, where)

    async def search_solutions(
        self,
        query: str,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        n_results: int = 5
    ) -> List[Memory]:
        """Search solutions."""
        where = {}
        if language:
            where["language"] = language
        if framework:
            where["framework"] = framework
        return await self.search(query, MemoryType.SOLUTION, n_results, where or None)

    async def search_error_fixes(
        self,
        error_message: str,
        language: Optional[str] = None,
        n_results: int = 5
    ) -> List[Memory]:
        """Search error fixes."""
        where = {"language": language} if language else None
        return await self.search(error_message, MemoryType.ERROR_FIX, n_results, where)

    async def find_similar_decisions(
        self,
        decision_context: str,
        n_results: int = 5
    ) -> List[Memory]:
        """Find similar past decisions."""
        return await self.search(decision_context, MemoryType.DECISION, n_results)

    # =========================================================================
    # MEMORY MANAGEMENT
    # =========================================================================

    async def get(self, memory_id: str, memory_type: MemoryType) -> Optional[Memory]:
        """Get a specific memory by ID."""
        collection = self._get_collection(memory_type)
        result = collection.get(ids=[memory_id])

        if result and result["ids"]:
            return Memory(
                id=result["ids"][0],
                memory_type=memory_type,
                content=result["documents"][0],
                metadata=result["metadatas"][0]
            )
        return None

    async def update(
        self,
        memory_id: str,
        memory_type: MemoryType,
        content: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Update a memory."""
        collection = self._get_collection(memory_type)

        updates = {}
        if content:
            updates["documents"] = [content]
            updates["embeddings"] = [await self.embedding_engine.embed(content)]
        if metadata:
            # Preserve existing metadata
            existing = collection.get(ids=[memory_id])
            if existing and existing["metadatas"]:
                merged = {**existing["metadatas"][0], **metadata}
                merged["updated_at"] = datetime.now().isoformat()
                updates["metadatas"] = [merged]

        if updates:
            async with self._lock:
                collection.update(ids=[memory_id], **updates)

    async def delete(self, memory_id: str, memory_type: MemoryType) -> None:
        """Delete a memory."""
        collection = self._get_collection(memory_type)
        async with self._lock:
            collection.delete(ids=[memory_id])

    async def count(self, memory_type: Optional[MemoryType] = None) -> int:
        """Count memories."""
        if memory_type:
            return self._get_collection(memory_type).count()
        return sum(c.count() for c in self._collections.values())

    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================

    async def bulk_store(
        self,
        memories: List[Tuple[MemoryType, str, Dict]]
    ) -> List[str]:
        """Store multiple memories efficiently."""
        ids = []
        for memory_type, content, metadata in memories:
            memory_id = await self.store(memory_type, content, metadata)
            ids.append(memory_id)
        return ids

    async def export_collection(self, memory_type: MemoryType) -> List[Dict]:
        """Export all memories of a type."""
        collection = self._get_collection(memory_type)
        result = collection.get()

        memories = []
        if result and result["ids"]:
            for i, doc_id in enumerate(result["ids"]):
                memories.append({
                    "id": doc_id,
                    "content": result["documents"][i],
                    "metadata": result["metadatas"][i]
                })
        return memories

    async def import_collection(
        self,
        memory_type: MemoryType,
        memories: List[Dict]
    ) -> int:
        """Import memories from export."""
        count = 0
        for memory in memories:
            await self.store(
                memory_type,
                memory["content"],
                memory.get("metadata", {}),
                memory.get("id")
            )
            count += 1
        return count

    # =========================================================================
    # LEARNING HELPERS
    # =========================================================================

    async def learn_from_task(
        self,
        task_description: str,
        task_result: Dict,
        success: bool,
        lessons: List[str]
    ) -> List[str]:
        """Extract and store learnings from a completed task."""
        ids = []

        # Store overall task learning
        outcome = "success" if success else "failure"
        content = f"Task: {task_description}\n\nOutcome: {outcome}\n\nResult Summary:\n{json.dumps(task_result, indent=2)}"
        ids.append(await self.store_learning(content, outcome=outcome))

        # Store individual lessons
        for lesson in lessons:
            ids.append(await self.store_learning(
                lesson,
                outcome=outcome,
                tags=["lesson", "automated"]
            ))

        return ids

    async def get_relevant_context(
        self,
        task_description: str,
        n_results: int = 5
    ) -> str:
        """Get relevant context for a new task."""
        memories = await self.search(
            task_description,
            n_results=n_results,
            min_relevance=0.3
        )

        if not memories:
            return ""

        context_parts = []
        for memory in memories:
            context_parts.append(f"---\n[{_safe_enum_value(memory.memory_type)}] (relevance: {memory.relevance_score:.2f})\n{memory.content}\n")

        return "Relevant memories:\n" + "\n".join(context_parts)
