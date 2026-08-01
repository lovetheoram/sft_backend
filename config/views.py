from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import connection
from datetime import datetime

class HealthCheckView(APIView):
    """
    Health check endpoint for load balancers and uptime monitoring.
    GET /api/health/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        db_status = "connected"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            db_status = f"error: {str(e)}"

        return Response({
            "status": "ok",
            "version": "1.1.0",
            "database": db_status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
