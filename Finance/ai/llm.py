# # Finance/ai/llm.py

from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings


# def get_llm():
#     return ChatGoogleGenerativeAI(
#         model="gemini-2.5-flash",
#         temperature=0.3,
#         api_key=settings.GEMINI_API_KEY
#     )

# Finance/ai/llm.py

# from langchain_huggingface import HuggingFaceEndpoint
from django.conf import settings
from langchain_groq import ChatGroq



def get_llm():
    try:
        return ChatGroq(
model="llama-3.1-8b-instant",
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0.3
    )
    except Exception as e:
        print("LLM init error:", e)
        return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        api_key=settings.GEMINI_API_KEY
    )
        
        # return None