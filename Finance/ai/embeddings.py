# from sentence_transformers import SentenceTransformer

# model = SentenceTransformer("all-MiniLM-L6-v2")

# def embed(texts):
#     return model.encode(texts, normalize_embeddings=True)



from langchain_google_genai import GoogleGenerativeAIEmbeddings
from django.conf import settings

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    # google_api_key=os.getenv("GEMINI_API_KEY")
    api_key=settings.GEMINI_API_KEY

)

def embed(texts: list[str]):
    return embeddings.embed_documents(texts)
