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

from Finance.models import Income, Expense, Member, Building, Notification
from Finance.serializers import IncomeSerializer, ExpenseSerializer
from Finance.services import get_financial_summary
from .permissions import is_super_admin, is_building_admin, IsBuildingAdmin, IsSuperAdmin, IsAdminOrBuildingAdmin


class IncomeViewSet(viewsets.ModelViewSet):
    """
    Manages payment inflows. Residents create pending logs; admins audit them.
    Optimized with deep select_related to eliminate N+1 query bottlenecks.
    """
    queryset = Income.objects.select_related(
        "member", "member__user", "member__user__flat", "member__user__flat__building",
        "building", "special_charge"
    ).all()
    serializer_class = IncomeSerializer

    def get_permissions(self):
        # Strict protection: Only authenticated admins can modify/delete/verify/reject income records
        if self.action in ['verify', 'reject', 'destroy', 'update', 'partial_update']:
            return [IsAdminOrBuildingAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        
        scope = self.request.query_params.get("scope") or self.request.query_params.get("admin")
        building_id = self.request.query_params.get("building_id")

        if scope in ["all", "true"] or self.action in ["verify", "reject"]:
            if is_super_admin(user):
                if building_id:
                    qs = qs.filter(building_id=building_id)
            elif is_building_admin(user):
                user_building = getattr(getattr(user, 'flat', None), 'building', None) or getattr(user, 'building_admin_for', None)
                if user_building:
                    qs = qs.filter(building=user_building)
                else:
                    qs = qs.filter(member__user=user)
            else:
                qs = qs.filter(member__user=user)
        else:
            # Default scope: return ONLY personal income payments for the logged-in user
            qs = qs.filter(member__user=user)

        # Filters
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        min_amount = self.request.query_params.get("min_amount")
        max_amount = self.request.query_params.get("max_amount")
        income_status = self.request.query_params.get("status")

        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        if min_amount:
            try:
                qs = qs.filter(amount__gte=float(min_amount))
            except ValueError:
                pass
        if max_amount:
            try:
                qs = qs.filter(amount__lte=float(max_amount))
            except ValueError:
                pass
        if income_status and income_status != 'all':
            qs = qs.filter(status=income_status)

        return qs.order_by("-date", "-id")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        limit = request.query_params.get("limit")
        offset = request.query_params.get("offset")
        
        if limit is not None:
            try:
                limit_val = max(1, int(limit))
                offset_val = max(0, int(offset)) if offset is not None else 0
                total_count = queryset.count()
                page_qs = queryset[offset_val : offset_val + limit_val]
                serializer = self.get_serializer(page_qs, many=True)
                return Response({
                    "count": total_count,
                    "results": serializer.data,
                    "has_more": (offset_val + limit_val) < total_count,
                    "limit": limit_val,
                    "offset": offset_val
                }, status=status.HTTP_200_OK)
            except ValueError:
                pass

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        user = self.request.user
        request_data = self.request.data
        
        target_member_id = request_data.get('member_id')
        target_user_id = request_data.get('user_id')

        # Admin creating payment on behalf of a resident/user
        if (is_super_admin(user) or is_building_admin(user)) and (target_member_id or target_user_id):
            target_member = None
            if target_member_id:
                try:
                    target_member = Member.objects.get(pk=target_member_id)
                except Member.DoesNotExist:
                    raise ValidationError({"member_id": "Target member record does not exist."})
            elif target_user_id:
                target_member, _ = Member.objects.get_or_create(user_id=target_user_id)

            if target_member:
                target_building = getattr(getattr(target_member.user, 'flat', None), 'building', None)
                if not target_building:
                    target_building = getattr(getattr(user, 'flat', None), 'building', None)
                
                # Cross-building isolation check for Building Admins
                if is_building_admin(user) and not is_super_admin(user):
                    admin_building = getattr(getattr(user, 'flat', None), 'building', None) or getattr(user, 'building_admin_for', None)
                    if admin_building and target_building and admin_building.id != target_building.id:
                        raise PermissionDenied("Building Admins can only record payments for residents in their own building.")
                
                explicit_building_id = request_data.get('building_id')
                if explicit_building_id:
                    if is_building_admin(user) and not is_super_admin(user):
                        admin_building = getattr(getattr(user, 'flat', None), 'building', None) or getattr(user, 'building_admin_for', None)
                        if admin_building and str(explicit_building_id) != str(admin_building.id):
                            raise PermissionDenied("Building Admins cannot specify payments for a different building.")
                    try:
                        target_building = Building.objects.get(pk=explicit_building_id)
                    except Building.DoesNotExist:
                        pass

                serializer.save(member=target_member, building=target_building, status='verified')
                return

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
        income = get_object_or_404(self.get_queryset(), pk=pk)
        income.status = 'verified'
        income.save(update_fields=["status"])
        return Response({"status": "Income record has been successfully verified."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        income = get_object_or_404(self.get_queryset(), pk=pk)
        reason = request.data.get('reason', '').strip()
        income.status = 'fraud'
        income.save(update_fields=["status"])

        if income.member and hasattr(income.member, 'user'):
            msg = f"Your payment record of ₹{income.amount} dated {income.date} was rejected by admin."
            if reason:
                msg += f" Reason: {reason}"
            Notification.objects.create(
                user=income.member.user,
                income=income,
                message=msg,
                seen=False
            )

        return Response({"status": "Income record flagged as rejected.", "reason": reason}, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        updated_income = serializer.save()
        if updated_income.member and hasattr(updated_income.member, 'user'):
            Notification.objects.create(
                user=updated_income.member.user,
                income=updated_income,
                message=f"Your payment record of ₹{updated_income.amount} dated {updated_income.date} has been updated by admin.",
                seen=False
            )

    def perform_destroy(self, instance):
        if instance.member and hasattr(instance.member, 'user'):
            Notification.objects.create(
                user=instance.member.user,
                message=f"Your payment record of ₹{instance.amount} dated {instance.date} has been removed by admin.",
                seen=False
            )
        instance.delete()


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    Manages building expense logs. Regular residents are fully blocked from accessing this system.
    """
    queryset = Expense.objects.select_related("category", "building").all()
    serializer_class = ExpenseSerializer

    def get_permissions(self):
        # Allow both Super Admin and Building Admin to manage expenses.
        # Regular residents are blocked from non-SAFE methods.
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsAdminOrBuildingAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset

        if is_super_admin(user):
            building_id = self.request.query_params.get("building_id")
            if building_id:
                qs = qs.filter(building_id=building_id)
        elif is_building_admin(user):
            user_building = getattr(getattr(user, 'flat', None), 'building', None)
            qs = qs.filter(building=user_building)
        else:
            return Expense.objects.none()

        # Filters
        category_id = self.request.query_params.get("category_id") or self.request.query_params.get("category")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        min_amount = self.request.query_params.get("min_amount")
        max_amount = self.request.query_params.get("max_amount")

        if category_id:
            qs = qs.filter(category_id=category_id)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        if min_amount:
            try:
                qs = qs.filter(amount__gte=float(min_amount))
            except ValueError:
                pass
        if max_amount:
            try:
                qs = qs.filter(amount__lte=float(max_amount))
            except ValueError:
                pass

        return qs.order_by("-date", "-id")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        limit = request.query_params.get("limit")
        offset = request.query_params.get("offset")
        
        if limit is not None:
            try:
                limit_val = max(1, int(limit))
                offset_val = max(0, int(offset)) if offset is not None else 0
                total_count = queryset.count()
                page_qs = queryset[offset_val : offset_val + limit_val]
                serializer = self.get_serializer(page_qs, many=True)
                return Response({
                    "count": total_count,
                    "results": serializer.data,
                    "has_more": (offset_val + limit_val) < total_count,
                    "limit": limit_val,
                    "offset": offset_val
                }, status=status.HTTP_200_OK)
            except ValueError:
                pass

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        user = self.request.user
        if is_super_admin(user):
            building_id = self.request.data.get('building_id') or self.request.data.get('building')
            if building_id and 'building' not in serializer.validated_data:
                try:
                    building = Building.objects.get(pk=building_id)
                    serializer.save(building=building)
                    return
                except (Building.DoesNotExist, ValueError):
                    pass
            serializer.save()
            return
            
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

        clear_cache = request.GET.get("clear_cache", "").lower() in ["true", "1"] or request.GET.get("refresh", "").lower() in ["true", "1"]
        data = get_financial_summary(start_year, building, clear_cache=clear_cache)
        return Response(data, status=status.HTTP_200_OK)


class ClearCacheView(APIView):
    """
    Clears the entire system cache (Redis/LocMem). Accessible by Admins and Building Admins.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if getattr(user, 'role', None) != 'admin' and not getattr(user, 'is_staff', False) and not getattr(user, 'is_superuser', False):
            return Response({"error": "Admin permission required to purge system cache."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from django.core.cache import cache
            cache.clear()
        except Exception as e:
            # Fallback log in case backend cache engine raises driver warning
            pass

        return Response({"status": "Cache successfully cleared."}, status=status.HTTP_200_OK)

