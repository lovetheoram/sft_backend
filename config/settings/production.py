import os
from .base import *  # noqa: F401, F403

# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTION SETTINGS — Society Finance Tracker
# ─────────────────────────────────────────────────────────────────────────────
# Set DJANGO_SETTINGS_MODULE=config.settings.production in your WSGI/deployment.
# ─────────────────────────────────────────────────────────────────────────────

DEBUG = False
LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING')

ALLOWED_HOSTS = os.getenv(
    'ALLOWED_HOSTS',
    'your-app.pythonanywhere.com'
).split(',')

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'https://your-frontend.netlify.app'
).split(',')

# ── Security Headers ──────────────────────────────────────────────────────────
# HSTS — tell browsers to only use HTTPS for 1 year
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Prevent browser from sniffing MIME types
SECURE_CONTENT_TYPE_NOSNIFF = True

# Enable browser XSS filter (legacy — still useful for older browsers)
SECURE_BROWSER_XSS_FILTER = True

# Prevent clickjacking
X_FRAME_OPTIONS = 'DENY'

# Force HTTPS redirect (set to True when behind SSL-terminating proxy)
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'

# Control how much referrer info is sent with cross-origin requests
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Cross-Origin Opener Policy — isolates browsing context for security
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# ── Cookie Security ───────────────────────────────────────────────────────────
SESSION_COOKIE_SECURE = True      # Only send session cookie over HTTPS
SESSION_COOKIE_HTTPONLY = True    # Prevent JS access to session cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection for session cookie

CSRF_COOKIE_SECURE = True         # Only send CSRF cookie over HTTPS
CSRF_COOKIE_HTTPONLY = True       # Prevent JS access to CSRF cookie (use header instead)
CSRF_COOKIE_SAMESITE = 'Lax'

# ── Production Logging Override ───────────────────────────────────────────────
# In production, suppress console noise and only write to file.
# Overrides the console handler from base.py.
LOGGING['handlers']['console']['level'] = 'ERROR'  # noqa: F405
LOGGING['loggers']['Finance']['level'] = 'INFO'    # noqa: F405
LOGGING['loggers']['Finance.ai']['level'] = 'WARNING'  # noqa: F405
LOGGING['root']['level'] = 'ERROR'  # noqa: F405
