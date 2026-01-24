from Finance.ai.vector_store import VectorStore
from Finance.ai.doc_builder import build_internal_docs

internal_store = VectorStore()

def initialize_rag(building):
    docs = build_internal_docs(building)
    internal_store.build(docs)


def retrieve_context(query, k=5):
    results = internal_store.search(query, k=k)
    return "\n".join([r["text"] for r in results])
