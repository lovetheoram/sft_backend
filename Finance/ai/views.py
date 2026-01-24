# Finance/ai/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from Finance.ai.graph import build_graph

graph = build_graph()


class AIChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        state = {
            "query": request.data.get("query", "hi"),
            "user": request.user
        }

        result = graph.invoke(state)

        return Response({
            "answer": result.get("response", "No response")
        })
