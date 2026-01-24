import faiss
import numpy as np
from Finance.ai.embeddings import embed

class VectorStore:
    def __init__(self):
        self.index = None
        self.documents = []

    def build(self, docs):
        texts = [d["text"] for d in docs]
        embeddings = embed(texts)

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(np.array(embeddings))

        self.documents = docs

    def search(self, query, k=5):
        q_emb = embed([query])
        scores, ids = self.index.search(q_emb, k)

        return [self.documents[i] for i in ids[0]]
