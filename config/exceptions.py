"""
=============================================================================
🛡️ GLOBAL DRF EXCEPTION HANDLER — Standardized JSON Error Envelope
=============================================================================
Responsibilities:
  1. Return consistent JSON error envelopes to all API clients
  2. Log full tracebacks for 5xx (server) errors
  3. Log warnings for 4xx (client) errors with request context
  4. Handle non-DRF (raw Python) exceptions with critical logging

Response Format (all errors):
  {
    "success": false,
    "error": {
      "code": "AuthenticationFailed",
      "message": "Human-readable description",
      "details": { ... }   # validation field errors (only for 4xx non-detail errors)
    },
    "timestamp": "2026-08-01T12:00:00Z",
    "request_id": "..."   # echoes X-Request-ID header if provided
  }
=============================================================================
"""

import logging
import traceback
from datetime import datetime, timezone

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('config')


def _get_request_context(context):
    """Extract safe loggable request metadata from the DRF exception context."""
    request = context.get('request') if context else None
    if not request:
        return {}
    return {
        'method': getattr(request, 'method', 'UNKNOWN'),
        'path': getattr(request, 'path', 'UNKNOWN'),
        'user_id': getattr(getattr(request, 'user', None), 'id', None),
        'request_id': request.headers.get('X-Request-ID', 'N/A'),
    }


def custom_exception_handler(exc, context):
    """
    Intercept all DRF exceptions and unhandled Python exceptions.
    Produces a standardized JSON error envelope and structured log entries.
    """
    request_ctx = _get_request_context(context)

    # ── Let DRF handle known exception types first ────────────────────────────
    response = exception_handler(exc, context)

    if response is not None:
        # ── 4xx Client Errors — log as WARNING ───────────────────────────────
        http_status = response.status_code
        error_code = exc.__class__.__name__

        # Extract human-readable message
        if isinstance(response.data, dict):
            error_message = response.data.get('detail', str(response.data))
        elif isinstance(response.data, list) and response.data:
            error_message = str(response.data[0])
        else:
            error_message = str(response.data) if response.data else 'An error occurred.'

        # Validation errors (400) — preserve field-level details
        details = None
        if isinstance(response.data, dict) and 'detail' not in response.data:
            details = response.data

        if http_status >= 500:
            logger.error(
                '[%s] Server error: %s — %s',
                http_status,
                error_code,
                error_message,
                extra={'request': request_ctx},
                exc_info=True,   # includes full traceback in log
            )
        else:
            logger.warning(
                '[%s] Client error: %s — %s | req=%s',
                http_status,
                error_code,
                error_message,
                request_ctx.get('request_id', 'N/A'),
                extra={'request': request_ctx},
            )

        # Build standardized envelope
        response.data = _build_envelope(
            error_code=error_code,
            error_message=str(error_message),
            details=details,
            request_id=request_ctx.get('request_id'),
        )
        return response

    # ── Unhandled Python Exception (non-DRF) — log as CRITICAL ───────────────
    tb = traceback.format_exc()
    logger.critical(
        'Unhandled exception: %s | %s %s | user=%s | req_id=%s\n%s',
        exc.__class__.__name__,
        request_ctx.get('method', '?'),
        request_ctx.get('path', '?'),
        request_ctx.get('user_id', 'anon'),
        request_ctx.get('request_id', 'N/A'),
        tb,
    )

    return Response(
        _build_envelope(
            error_code='InternalServerError',
            error_message='An unexpected server error occurred. Please try again later.',
            request_id=request_ctx.get('request_id'),
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _build_envelope(*, error_code, error_message, details=None, request_id=None):
    """Construct the standardized error response body."""
    envelope = {
        'success': False,
        'error': {
            'code': error_code,
            'message': error_message,
        },
        'timestamp': datetime.now(tz=timezone.utc).isoformat(),
    }
    if details:
        envelope['error']['details'] = details
    if request_id and request_id != 'N/A':
        envelope['request_id'] = request_id
    return envelope
