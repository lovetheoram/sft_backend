"""
=============================================================================
💰 FINANCIAL OPERATIONS VIEWS (Income, Expense, Summary Reports)
=============================================================================
"""

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404

from Finance.models import Income, Expense, Member
from Finance.serializers import IncomeSerializer, ExpenseSerializer
from Finance.services import get_financial_summary
from .permissions import is_super_admin, is_building_admin, IsBuildingAdmin, IsSuperAdmin


class IncomeViewSet(viewsets.ModelViewSet):
    """
    Manages payment inflows. Residents create pending logs; admins audit them.
    Optimized with deep select_related to eliminate N+1 query bottlenecks.
    """
    queryset = Income.objects.select_related(
        "member", "member__user", "member__user__flat", "member__user__flat__building"
    ).all()
    serializer_class = IncomeSerializer

    def get_permissions(self):
        # Strict protection: Only authenticated users can touch income endpoints
        if self.action in ['verify', 'reject']:
            return [IsBuildingAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return self.queryset
            
        # Safe structural navigation to protect against NoneType attribute drops
        user_building = getattr(getattr(user, 'flat', None), 'building', None)
        
        if is_building_admin(user):
            return self.queryset.filter(member__user__flat__building=user_building)
            
        # Regular residents only see their own payment histories
        return self.queryset.filter(member__user=user)

    def perform_create(self, serializer):
        user = self.request.user
        
        # Super Admins bypass profile restrictions and define fields directly
        if is_super_admin(user):
            serializer.save()
            return

        building = getattr(getattr(user, 'flat', None), 'building', None)
        income_status = 'verified' if is_building_admin(user) else 'pending'

        try:
            member = Member.objects.get(user=user)
            serializer.save(member=member, building=building, status=income_status)
        except Member.DoesNotExist:
            raise PermissionDenied("An active Member registration record is required to file payments.")

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        # FIX: Filter lookup through get_queryset to stop Admins from altering foreign building records
        income = get_object_or_404(self.get_queryset(), pk=pk)
        income.status = 'verified'
        income.save(update_fields=["status"])
        return Response({"status": "Income record has been successfully verified."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        # FIX: Cross-building isolation filter via local get_queryset lookup injection
        income = get_object_or_404(self.get_queryset(), pk=pk)
        income.status = 'fraud'
        income.save(update_fields=["status"])
        return Response({"status": "Income record flagged as fraudulent and rejected."}, status=status.HTTP_200_OK)


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    Manages building expense logs. Regular residents are fully blocked from accessing this system.
    """
    queryset = Expense.objects.select_related("category").all()
    serializer_class = ExpenseSerializer

    def get_permissions(self):
        # FIX: Restrict write actions (POST, PUT, DELETE) exclusively to Admins.
        # This blocks malicious residents from executing unauthorized financial operations.
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsBuildingAdmin()]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return self.queryset
            
        if is_building_admin(user):
            user_building = getattr(getattr(user, 'flat', None), 'building', None)
            return self.queryset.filter(building=user_building)
            
        # Standard residents have no visibility over underlying society layout expenses
        return Expense.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if is_super_admin(user):
            serializer.save()
            return
            
        # Automatically tie the building to the logged-in Building Admin's domain profile
        user_building = getattr(getattr(user, 'flat', None), 'building', None)
        if not user_building:
            raise PermissionDenied("You must be linked to an operational building footprint to submit expenses.")
            
        serializer.save(building=user_building)


class FinancialSummaryReport(APIView):
    """
    Generates high-level analytic ledger charts tracking balances across annual timelines.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Super Admins specify target footprints manually using incoming parameters
        if is_super_admin(user):
            building_id = request.GET.get("building_id")
            if not building_id:
                raise ValidationError({"building_id": "Super Admins must supply a targeting building query parameter."})
            building = building_id
        else:
            # Safe parsing logic fallback chain
            building = getattr(getattr(user, 'flat', None), 'building', None) or getattr(user, "building_admin_for", None)

        if not building:
            raise PermissionDenied("You are not assigned to an active property management layout.")

        try:
            # Enforce strict parsing on parameters
            start_year = int(request.GET.get("year", 2026))
        except ValueError:
            return Response({"error": "Target year must be a valid base-10 numerical entry."}, status=status.HTTP_400_BAD_REQUEST)

        data = get_financial_summary(start_year, building)
        return Response(data, status=status.HTTP_200_OK)
