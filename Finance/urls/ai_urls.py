"""
=============================================================================
🤖 AI ASSISTANT URL ROUTING MODULE
=============================================================================
"""

from django.urls import path
from Finance.ai.views import AIChatView, AIFinancialReport

urlpatterns = [
    path("ai/chat/", AIChatView.as_view()),
    path("ai/financial-report/", AIFinancialReport.as_view()),
]
