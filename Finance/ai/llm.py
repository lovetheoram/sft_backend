import os
from django.conf import settings


def get_llm():
    """
    LLM Factory — Tries Groq (llama-3.1-8b-instant) first, falls back to Gemini (gemini-2.5-flash).
    Uses lazy imports to minimize memory footprint on 512MB hosting tiers (Render/Free Tier).
    """
    groq_key = getattr(settings, 'GROQ_API_KEY', None) or os.getenv('GROQ_API_KEY')
    gemini_key = getattr(settings, 'GEMINI_API_KEY', None) or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

    if groq_key and not groq_key.startswith('gsk_your_') and len(groq_key) > 20:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model="llama-3.1-8b-instant",
                groq_api_key=groq_key,
                temperature=0.3
            )
        except Exception as e:
            print("⚠️ Groq LLM init failed, falling back to Gemini:", e)

    # Fallback to Gemini 2.5 Flash (Lazy Loaded)
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        google_api_key=gemini_key or "dummy_key_for_tests"
    )