"""
=============================================================================
💰 FINANCE & REPORTS URL ROUTING MODULE
=============================================================================
"""

from django.urls import path
from rest_framework.routers import DefaultRouter
from Finance.views import IncomeViewSet, ExpenseViewSet, FinancialSummaryReport, ClearCacheView

router = DefaultRouter()
router.register('income', IncomeViewSet, basename='income')
router.register('expense', ExpenseViewSet)

urlpatterns = [
    path('financialSummary/', FinancialSummaryReport.as_view()),
    path('clear-cache/', ClearCacheView.as_view()),
]
