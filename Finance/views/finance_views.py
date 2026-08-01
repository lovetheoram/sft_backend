"""
=============================================================================
💰 FINANCIAL OPERATIONS VIEWS (Income, Expense, Summary Reports)
=============================================================================
"""

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from Finance.models import Income, Expense, Member
from Finance.serializers import IncomeSerializer, ExpenseSerializer
from Finance.services import get_financial_summary
from .permissions import is_super_admin, is_building_admin, IsBuildingAdmin


class IncomeViewSet(viewsets.ModelViewSet):
    queryset = Income.objects.select_related(
        "member", "member__user", "member__user__flat", "member__user__flat__building"
    ).all()
    serializer_class = IncomeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return self.queryset
        elif is_building_admin(user):
            user_building = getattr(user.flat, 'building', None)
            return self.queryset.filter(member__user__flat__building=user_building)
        else:
            return self.queryset.filter(member__user=user)

    def perform_create(self, serializer):
        user = self.request.user
        income_status = 'pending'
        if is_building_admin(user):
            income_status = 'verified'

        try:
            member = Member.objects.get(user=user)
            serializer.save(member=member, status=income_status)
        except Member.DoesNotExist:
            raise PermissionDenied("You are not associated with any member.")

    @action(detail=True, methods=['post'], permission_classes=[IsBuildingAdmin])
    def verify(self, request, pk=None):
        income = get_object_or_404(Income, pk=pk)
        income.status = 'verified'
        income.save(update_fields=["status"])
        return Response({"status": "Income verified"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsBuildingAdmin])
    def reject(self, request, pk=None):
        income = get_object_or_404(Income, pk=pk)
        income.status = 'fraud'
        income.save(update_fields=["status"])
        return Response({"status": "Income rejected as fraud"}, status=status.HTTP_200_OK)


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.select_related("category").all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return self.queryset
        elif is_building_admin(user):
            building = getattr(user.flat, "building", None)
            return self.queryset.filter(building=building)
        return Expense.objects.none()


class FinancialSummaryReport(APIView):
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

        data = get_financial_summary(start_year, building)
        return Response(data, status=status.HTTP_200_OK)
