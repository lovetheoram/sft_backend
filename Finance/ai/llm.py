import os
from django.conf import settings


def get_llm():
    """
    LLM Factory — Uses Gemini (gemini-2.5-flash) primary / fallback.
    Uses lazy imports to minimize memory footprint on 512MB hosting tiers (Render/Free Tier).
    """
    gemini_key = getattr(settings, 'GEMINI_API_KEY', None) or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    groq_key = getattr(settings, 'GROQ_API_KEY', None) or os.getenv('GROQ_API_KEY')

    if gemini_key and not gemini_key.startswith('AIzaSy_your_') and len(gemini_key) > 20:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.3,
                google_api_key=gemini_key
            )
        except Exception as e:
            print("⚠️ Gemini LLM init failed, falling back to Groq:", e)

    if groq_key and not groq_key.startswith('gsk_your_') and len(groq_key) > 20:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model="llama-3.3-70b-versatile",
                groq_api_key=groq_key,
                temperature=0.3
            )
        except Exception as e:
            print("⚠️ Groq LLM init failed:", e)

    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        google_api_key=gemini_key or "dummy_key_for_tests"
    )