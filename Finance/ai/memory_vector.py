"""
=============================================================================
🧠 VECTOR MEMORY MODULE — FAISS + SafeEmbeddings Engine
=============================================================================
This module handles persistent vector storage for conversational AI memory.
It provides 0MB PyTorch disk footprint (compatible with 500MB free-tier hosting)
by utilizing a Zero-Crash Hybrid Embedding Architecture (SafeEmbeddings).

-----------------------------------------------------------------------------
📐 HOW HASH EMBEDDING WORKS (Addition, Updating & Searching):
-----------------------------------------------------------------------------
1. VECTOR GENERATION (_hash_embed):
   - Input text (e.g. "I paid 500 for maintenance") is split into normalized words.
   - Each word is hashed using MD5 (hashlib.md5(word) % 384) to map to a fixed
     array index between 0 and 383.
   - Word occurrences increment target index frequencies.
   - The resulting 384-element array is L2-normalized (length = 1.0) so it works
     directly with FAISS Cosine / Euclidean distance formulas.
   - Advantage: Requires 0 MB disk space, 0 PyTorch downloads, 0 API keys,
     and executes in < 0.1ms locally on CPU.

2. ADDITION (add_memory & embed_documents):
   - When a new chat message arrives containing financial trigger words
     ("payment", "expense", "decision", "issue", "problem"):
   - SafeEmbeddings.embed_documents([text]) calls _hash_embed(text) to create a
     384-dimensional vector.
   - FAISS binds the text string + metadata timestamp + 384-dim vector into a Document.
   - store.add_documents([doc]) appends the new vector entry to index.faiss.

3. UPDATING / PERSISTENCE (save_vector_store & store.save_local):
   - After adding new vectors, store.save_local(path) writes the updated FAISS
     index and document store to disk:
       path: vector_memory/user_{user_id}/index.faiss
       path: vector_memory/user_{user_id}/index.pkl
   - FAISS incrementally appends new vector entries to the existing index
     file without re-embedding historical messages.

4. SEARCHING (get_relevant_memory & embed_query):
   - When the user asks a question (e.g. "Did I make any payments in 2024?"):
   - SafeEmbeddings.embed_query(query) calls _hash_embed(query) to create a
     384-dimensional search query vector.
   - FAISS performs Cosine Similarity Search between the query vector and all
     vectors stored in index.faiss.
   - Top-K (default k=3) most relevant historical text entries are returned
     and injected into the AI prompt context.
=============================================================================
"""

import os
import time
import hashlib
import numpy as np
from django.conf import settings

from langchain_community.vectorstores import FAISS 
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document

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
        
        # Initialize Gemini API Embeddings only if valid key provided
        if self.api_key and self.api_key.startswith("AIzaSy"):
            try:
                self.gemini = GoogleGenerativeAIEmbeddings(
                    model="models/text-embedding-004",
                    google_api_key=self.api_key
                )
            except Exception as e:
                print("⚠️ Gemini Embeddings initialization error:", e)

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
        """
        Generates vector embeddings for ADDING new documents into FAISS.
        """
        if self.gemini:
            try:
                return self.gemini.embed_documents(texts)
            except Exception as e:
                print("⚠️ Gemini embed_documents API call failed, using local hash fallback:", e)
        
        # Fallback to local 0MB hash embedder for additions
        return [self._hash_embed(t) for t in texts]

    def embed_query(self, text):
        """
        Generates a vector embedding for SEARCHING existing documents in FAISS.
        """
        if self.gemini:
            try:
                return self.gemini.embed_query(text)
            except Exception as e:
                print("⚠️ Gemini embed_query API call failed, using local hash fallback:", e)
        
        # Fallback to local 0MB hash embedder for query searches
        return self._hash_embed(text)


# Singleton Embeddings Instance
embeddings = SafeEmbeddings()


# -----------------------------------------------------------------------------
# 📁 PATH HANDLING
# -----------------------------------------------------------------------------
def get_user_vector_path(user_id):
    """
    Returns path to user-specific FAISS storage directory.
    Creates folder if it does not exist: vector_memory/user_{user_id}/
    """
    path = os.path.join(VECTOR_DIR, f"user_{user_id}")
    os.makedirs(path, exist_ok=True)
    return path


# -----------------------------------------------------------------------------
# 🔄 LOAD / CREATE FAISS VECTOR STORE
# -----------------------------------------------------------------------------
def load_vector_store(user_id):
    """
    Loads existing FAISS vector store from disk or initializes a new index.
    """
    path = get_user_vector_path(user_id)
    index_file = os.path.join(path, "index.faiss")

    if os.path.exists(index_file):
        try:
            return FAISS.load_local(
                path,
                embeddings,
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            print("⚠️ FAISS load failed, re-initializing new index:", e)

    # Initialize new FAISS vector store if not found
    return FAISS.from_texts(["init"], embeddings)


def save_vector_store(store, user_id):
    """
    Persists updated FAISS vector store index and document pickle to disk.
    """
    path = get_user_vector_path(user_id)
    store.save_local(path)


# -----------------------------------------------------------------------------
# 🧠 KEYWORD FILTER
# -----------------------------------------------------------------------------
def should_store(text):
    """
    Determines whether a chat message contains important information worth
    vectorizing into long-term FAISS memory.
    """
    text_lower = text.lower()
    keywords = ["payment", "expense", "decision", "issue", "problem", "income", "paid"]
    return any(kw in text_lower for kw in keywords)


# -----------------------------------------------------------------------------
# ➕ ADD / UPDATE VECTOR MEMORY
# -----------------------------------------------------------------------------
def add_memory(user_id, text):
    """
    1. Checks if text contains financial/decision keywords via should_store().
    2. Loads FAISS index via load_vector_store(user_id).
    3. Calls SafeEmbeddings.embed_documents([text]) to get 384-dim hash vector.
    4. Appends new document to FAISS index.
    5. Saves updated index to disk via save_vector_store(store, user_id).
    """
    try:
        if should_store(text):
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
    """
    1. Loads FAISS index for user via load_vector_store(user_id).
    2. Calls SafeEmbeddings.embed_query(query) to get 384-dim query hash vector.
    3. Performs FAISS Cosine Similarity Search to find top k matching documents.
    4. Returns top matching text strings for injection into AI prompt context.
    """
    try:
        store = load_vector_store(user_id)
        docs = store.similarity_search(query, k=k)

        # Filter out empty/init entries
        results = [
            d.page_content
            for d in docs
            if d.page_content and d.page_content != "init"
        ]

        return results
    except Exception as e:
        print("❌ Vector retrieval error:", e)
        return []