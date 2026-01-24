# Finance/ai/llm.py

from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings

# Initialize LLM once for all nodes
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3,  # lower → more deterministic
    api_key=settings.GEMINI_API_KEY
)
