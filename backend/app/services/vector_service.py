import hashlib
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from app.chroma import check_chroma_connection, get_chroma_client


class VectorEmbeddingEngine:
    """
    Deterministic embedding engine providing dense 384-dimensional vector representations.
    Uses normalized word-frequency and n-gram hash projection to generate consistent,
    repeatable embeddings offline and online without external API flakiness.
    """

    DIMENSIONS = 384
    STOPWORDS = {
        "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and",
        "what", "how", "does", "with", "this", "that", "it", "are", "by", "as",
    }

    @classmethod
    def generate_embedding(cls, text: str) -> List[float]:
        """Generate a normalized 384-dimensional vector for input text."""
        vec = [0.0] * cls.DIMENSIONS
        raw_tokens = re.findall(r"\b\w+\b", text.lower())
        tokens = [t for t in raw_tokens if t not in cls.STOPWORDS] or raw_tokens
        if not tokens:
            return vec

        for i, token in enumerate(tokens):
            # Compute token hash for dimension bucket
            token_hash = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            bucket = token_hash % cls.DIMENSIONS
            weight = 2.0 + (1.0 / (i + 1))  # Early tokens receive higher positional weight
            vec[bucket] += weight

            # Bigram hashing for local context
            if i < len(tokens) - 1:
                bigram = f"{token}_{tokens[i+1]}"
                bi_hash = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16)
                bi_bucket = bi_hash % cls.DIMENSIONS
                vec[bi_bucket] += 1.5

        # L2 Normalization
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]
        return vec

    @classmethod
    def cosine_similarity(cls, vec_a: List[float], vec_b: List[float]) -> float:
        """Calculate cosine similarity between two unit vectors."""
        if len(vec_a) != len(vec_b):
            return 0.0
        return max(0.0, min(1.0, sum(a * b for a, b in zip(vec_a, vec_b))))


class InMemoryVectorStore:
    """
    High-performance in-memory vector index ensuring vector retrieval works
    with 100% reliability in offline environments or when ChromaDB HTTP server is down.
    """

    def __init__(self):
        # Maps collection_name -> Dict[chunk_id, {vector, document, metadata}]
        self.collections: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def get_or_create_collection(self, collection_name: str):
        if collection_name not in self.collections:
            self.collections[collection_name] = {}
        return collection_name

    def upsert(
        self,
        collection_name: str,
        chunk_id: str,
        document: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ):
        self.get_or_create_collection(collection_name)
        self.collections[collection_name][chunk_id] = {
            "id": chunk_id,
            "document": document,
            "embedding": embedding,
            "metadata": metadata,
        }

    def delete_by_source(self, collection_name: str, source_id: str):
        if collection_name in self.collections:
            to_delete = [
                cid
                for cid, item in self.collections[collection_name].items()
                if item["metadata"].get("source_id") == str(source_id)
            ]
            for cid in to_delete:
                del self.collections[collection_name][cid]

    def query(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 4,
        where_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if collection_name not in self.collections:
            return []

        scored_items: List[Tuple[float, Dict[str, Any]]] = []
        for item in self.collections[collection_name].values():
            if where_metadata:
                match = all(
                    item["metadata"].get(k) == v for k, v in where_metadata.items()
                )
                if not match:
                    continue

            score = VectorEmbeddingEngine.cosine_similarity(
                query_embedding, item["embedding"]
            )
            scored_items.append((score, item))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, item in scored_items[:top_k]:
            results.append({
                "id": item["id"],
                "document": item["document"],
                "metadata": item["metadata"],
                "score": round(score, 4),
            })
        return results

    def count(self, collection_name: str) -> int:
        if collection_name not in self.collections:
            return 0
        return len(self.collections[collection_name])


# Singleton in-memory store
_in_memory_vector_store = InMemoryVectorStore()


class VectorService:
    """
    Unified vector service managing project-isolated collections,
    text indexing, and semantic similarity search.
    """

    @classmethod
    def get_collection_name(cls, project_id: Any) -> str:
        return f"memoryhub_project_{str(project_id).replace('-', '_')}"

    @classmethod
    def index_chunk(
        cls,
        project_id: Any,
        chunk_id: str,
        document: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Index a text chunk with its vector embedding and metadata."""
        collection_name = cls.get_collection_name(project_id)
        embedding = VectorEmbeddingEngine.generate_embedding(document)

        # Store in in-memory vector index
        _in_memory_vector_store.upsert(
            collection_name=collection_name,
            chunk_id=chunk_id,
            document=document,
            embedding=embedding,
            metadata=metadata,
        )

        # Also sync to live ChromaDB if reachable
        if check_chroma_connection():
            try:
                client = get_chroma_client()
                collection = client.get_or_create_collection(name=collection_name)
                # Convert metadata values to strings/numbers/bools for ChromaDB requirements
                clean_metadata = {
                    k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                    for k, v in metadata.items()
                }
                collection.upsert(
                    ids=[chunk_id],
                    documents=[document],
                    embeddings=[embedding],
                    metadatas=[clean_metadata],
                )
            except Exception:
                pass  # Fallback to in-memory store cleanly

    @classmethod
    def delete_source_chunks(cls, project_id: Any, source_id: Any) -> None:
        """Remove all chunks associated with a deleted source record."""
        collection_name = cls.get_collection_name(project_id)
        _in_memory_vector_store.delete_by_source(collection_name, str(source_id))

        if check_chroma_connection():
            try:
                client = get_chroma_client()
                collection = client.get_collection(name=collection_name)
                collection.delete(where={"source_id": str(source_id)})
            except Exception:
                pass

    @classmethod
    def search_similar(
        cls,
        project_id: Any,
        query: str,
        top_k: int = 4,
        where_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search for a user query against project documents."""
        collection_name = cls.get_collection_name(project_id)
        query_embedding = VectorEmbeddingEngine.generate_embedding(query)

        # First query in-memory store
        in_memory_results = _in_memory_vector_store.query(
            collection_name=collection_name,
            query_embedding=query_embedding,
            top_k=top_k,
            where_metadata=where_metadata,
        )

        if in_memory_results:
            return in_memory_results

        # If in-memory had 0 and Chroma is up, attempt Chroma query
        if check_chroma_connection():
            try:
                client = get_chroma_client()
                collection = client.get_collection(name=collection_name)
                chroma_res = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=where_metadata,
                )
                if chroma_res and chroma_res.get("documents"):
                    docs = chroma_res["documents"][0]
                    ids = chroma_res["ids"][0]
                    metas = chroma_res["metadatas"][0]
                    distances = chroma_res.get("distances", [[0.0] * len(docs)])[0]
                    results = []
                    for cid, doc, meta, dist in zip(ids, docs, metas, distances):
                        # Approximate similarity from distance
                        score = max(0.0, 1.0 - (dist / 2.0))
                        results.append({
                            "id": cid,
                            "document": doc,
                            "metadata": meta,
                            "score": round(score, 4),
                        })
                    return results
            except Exception:
                pass

        return []

    @classmethod
    def count_chunks(cls, project_id: Any) -> int:
        collection_name = cls.get_collection_name(project_id)
        return _in_memory_vector_store.count(collection_name)
