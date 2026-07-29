from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import PermissionDenied
# from .agent import get_society_agent
from .prompt_ai import generate_financial_ai_report
from .llm import get_llm
# from .agent_v2 import run_finance_agent
from .agent import run_finance_agent
import uuid

class AIFinancialReport(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        building = getattr(user.flat, "building", None) or getattr(user, "building_admin_for", None)
        
        if not building:
            raise PermissionDenied("You are not assigned to any building.")

        try:
            start_year = int(request.GET.get("year", 2023))
        except ValueError:
            return Response({"error": "Invalid year"}, status=status.HTTP_400_BAD_REQUEST)

        report = generate_financial_ai_report(start_year, building)

        return Response({
            "ai_report": report
        })


class AIChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # from .agent import get_society_agent

        query = request.data.get("query")
        user = request.user
        building = getattr(user.flat, "building", None) or getattr(user, "building_admin_for", None)
        session_id= request.data.get("session_id") or user.id
        # str(uuid.uuid4())
        if not building:
            return Response({"error": "No building assigned"})
        

        # llm = get_llm()
        # response = llm.invoke("Explain society maintenance")
        # print(response.content)

        
        # response=generate_financial_ai_report(2025,building)
        print(query)
        response="Error"
        try:
            response=run_finance_agent(
            user.id,session_id, query,building
        )
        except Exception as e:
            print(e)

        
        print(response)

        return Response({"answer": response})