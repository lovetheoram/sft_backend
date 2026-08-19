"""
=============================================================================
🧠 VECTOR MEMORY MODULE — FAISS + SafeEmbeddings Engine
=============================================================================
This module handles persistent vector storage for conversational AI memory.
It provides 0MB PyTorch disk footprint (compatible with 500MB free-tier hosting)
by utilizing a Zero-Crash Hybrid Embedding Architecture (SafeEmbeddings).
Imports heavy AI packages lazily to stay within 512MB RAM on Render.
=============================================================================
"""

import os
import time
import hashlib
import numpy as np
from django.conf import settings
from langchain_core.embeddings import Embeddings

# -----------------------------------------------------------------------------
# 📁 BASE VECTOR MEMORY DIRECTORY
# -----------------------------------------------------------------------------
VECTOR_DIR = os.path.join(settings.BASE_DIR, "vector_memory")


# -----------------------------------------------------------------------------
# 🧠 SAFE EMBEDDINGS CLASS — ZERO-CRASH HYBRID ENGINE
# -----------------------------------------------------------------------------
class SafeEmbeddings(Embeddings):
    """
    Hybrid Embedding Provider:
    - Primary: Google Gemini Cloud API (models/text-embedding-004) if valid AIzaSy... key exists.
    - Fallback: Local 0MB Deterministic Feature Hashing (_hash_embed) if key is missing/offline.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.gemini = None

    def __call__(self, text):
        if isinstance(text, list):
            return self.embed_documents(text)
        return self.embed_query(text)

    def _get_gemini(self):
        if self.gemini is None and self.api_key and self.api_key.startswith("AIzaSy"):
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                self.gemini = GoogleGenerativeAIEmbeddings(
                    model="models/text-embedding-004",
                    google_api_key=self.api_key
                )
            except Exception as e:
                print("⚠️ Gemini Embeddings initialization error:", e)
        return self.gemini

    def _hash_embed(self, text, dim=384):
        """
        Deterministic Word Feature Hashing (0MB PyTorch / 0MB API Overhead)
        Maps string text into a 384-dimensional L2-normalized float vector.
        """
        words = text.lower().split()
        vec = np.zeros(dim, dtype=np.float32)
        for w in words:
            h = int(hashlib.md5(w.encode()).hexdigest(), 16)
            idx = h % dim
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        return (vec / norm if norm > 0 else vec).tolist()

    def embed_documents(self, texts):
        gemini = self._get_gemini()
        if gemini:
            try:
                return gemini.embed_documents(texts)
            except Exception as e:
                print("⚠️ Gemini embed_documents API call failed, using local hash fallback:", e)
        return [self._hash_embed(t) for t in texts]

    def embed_query(self, text):
        gemini = self._get_gemini()
        if gemini:
            try:
                return gemini.embed_query(text)
            except Exception as e:
                print("⚠️ Gemini embed_query API call failed, using local hash fallback:", e)
        return self._hash_embed(text)


# Lazy Singleton Embeddings Instance
_embeddings_instance = None


def get_embeddings():
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = SafeEmbeddings()
    return _embeddings_instance


# -----------------------------------------------------------------------------
# 📁 PATH HANDLING
# -----------------------------------------------------------------------------
def get_user_vector_path(user_id):
    path = os.path.join(VECTOR_DIR, f"user_{user_id}")
    os.makedirs(path, exist_ok=True)
    return path


# -----------------------------------------------------------------------------
# 🔄 LOAD / CREATE FAISS VECTOR STORE
# -----------------------------------------------------------------------------
def load_vector_store(user_id):
    """
    Lazy-loads FAISS vector store from disk or initializes a new index.
    """
    from langchain_community.vectorstores import FAISS
    path = get_user_vector_path(user_id)
    index_file = os.path.join(path, "index.faiss")

    embeddings = get_embeddings()
    if os.path.exists(index_file):
        try:
            return FAISS.load_local(
                path,
                embeddings,
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            print("⚠️ FAISS load failed, re-initializing new index:", e)

    return FAISS.from_texts(["init"], embeddings)


def save_vector_store(store, user_id):
    path = get_user_vector_path(user_id)
    store.save_local(path)


# -----------------------------------------------------------------------------
# 🧠 KEYWORD FILTER
# -----------------------------------------------------------------------------
def should_store(text):
    text_lower = text.lower()
    keywords = ["payment", "expense", "decision", "issue", "problem", "income", "paid"]
    return any(kw in text_lower for kw in keywords)


# -----------------------------------------------------------------------------
# ➕ ADD / UPDATE VECTOR MEMORY
# -----------------------------------------------------------------------------
def add_memory(user_id, text):
    try:
        if should_store(text):
            from langchain_core.documents import Document
            store = load_vector_store(user_id)

            doc = Document(
                page_content=text,
                metadata={"timestamp": time.time()}
            )

            store.add_documents([doc])
            save_vector_store(store, user_id)
    except Exception as e:
        print("❌ Vector add memory error:", e)


# -----------------------------------------------------------------------------
# 🔍 RETRIEVE / SEARCH VECTOR MEMORY
# -----------------------------------------------------------------------------
def get_relevant_memory(user_id, query, k=3):
    try:
        store = load_vector_store(user_id)
        docs = store.similarity_search(query, k=k)

        results = [
            d.page_content
            for d in docs
            if d.page_content and d.page_content != "init"
        ]

        return results
    except Exception as e:
        print("❌ Vector retrieval error:", e)
        return []