"""
=============================================================================
⚙️ MAIN DJANGO SETTINGS ENTRYPOINT — Society Finance Tracker
=============================================================================
Delegates to modular settings in config/settings/base.py.
For production deployment, set DJANGO_SETTINGS_MODULE=config.settings.production
=============================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load base environment settings
from config.settings.base import *  # noqa: F401, F403

# Ensure environment variables are loaded
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")