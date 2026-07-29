import os
from django.conf import settings

from langchain_community.vectorstores import FAISS 
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
# ----------------------------
# 📁 BASE DIRECTORY
# ----------------------------
VECTOR_DIR = os.path.join(settings.BASE_DIR, "vector_memory")

# ----------------------------
# 🧠 LOCAL EMBEDDING MODEL (FREE)
# ----------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ----------------------------
# 📁 PATH HANDLING
# ----------------------------
def get_user_vector_path(user_id):
    path = os.path.join(VECTOR_DIR, f"user_{user_id}")
    os.makedirs(path, exist_ok=True)
    return path


# ----------------------------
# 🔄 LOAD / CREATE VECTOR STORE
# ----------------------------
def load_vector_store(user_id):
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
            print("⚠️ FAISS load failed, creating new:", e)

    # Create new if not exists or fails
    return FAISS.from_texts(["init"], embeddings)


def save_vector_store(store, user_id):
    path = get_user_vector_path(user_id)
    store.save_local(path)


# ----------------------------
# 🧠 FILTER (IMPORTANT)
# ----------------------------
def should_store(text):
    text = text.lower()

    patterns = [
        "payment",
        "expense",
        "decision",
        "issue",
        "problem"
    ]

    return any(p in text for p in patterns)


# ----------------------------
# ➕ ADD MEMORY
# ----------------------------
import time

def add_memory(user_id, text):
    try:
        if should_store(text):
            
            store = load_vector_store(user_id)

            doc = Document(
                page_content=text,
                metadata={
                    "timestamp": time.time()
                }
            )

            store.add_documents([doc])
            save_vector_store(store, user_id)

    except Exception as e:
        print("❌ Vector add error:", e)


# ----------------------------
# 🔍 RETRIEVE MEMORY
# ----------------------------
def get_relevant_memory(user_id, query, k=3):
    try:
        store = load_vector_store(user_id)

        docs = store.similarity_search(query, k=k)

        # remove empty/init entries
        results = [
            d.page_content
            for d in docs
            if d.page_content and d.page_content != "init"
        ]

        return results

    except Exception as e:
        print("❌ Vector retrieval error:", e)
        return []