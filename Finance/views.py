from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from django.db.models import Sum
from collections import defaultdict
from datetime import date
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import permissions 
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied
from .models import User, Member, Income, Expense, Category, Complaint, PreviousDue, Announcement, SocietyDocument,Notification
from .serializers import (
    UserSerializer, MemberSerializer, IncomeSerializer, ExpenseSerializer,
    CategorySerializer, ComplaintSerializer, PreviousDueSerializer,
    AnnouncementSerializer, SocietyDocumentSerializer, SignupSerializer
)

from .models import Notification,Flat,Building,SpecialCharge
from .serializers import NotificationSerializer,FlatSerializer,BuildingSerializer,SpecialChargeSerializer
from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission, SAFE_METHODS, AllowAny
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

def is_super_admin(user):
    return user.role == 'admin' and user.flat is None

def is_building_admin(user):
    return user.role == 'admin' and user.flat is not None



class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        print(is_super_admin(request.user),"let see")
        return request.user.is_authenticated and is_super_admin(request.user)

class IsBuildingAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and is_building_admin(request.user)

class IsAdminOrBuildingAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

    def has_object_permission(self, request, view, obj):
        # Super admin: allow
        if is_super_admin(request.user):
            return True
        # Building admin: only allow if it belongs to their building
        if is_building_admin(request.user):
            return getattr(obj, 'building', None) == request.user.building_admin_for
        return False




class BuildingViewSet(viewsets.ModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer

    def get_permissions(self):
        if self.action == 'my_building':
            return [permissions.IsAuthenticated()]
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsSuperAdmin()]

    @action(detail=False, methods=['get'], url_path='my_building')
    def my_building(self, request):
        user = request.user
        if user.flat and user.flat.building:
            building = user.flat.building
            serializer = self.get_serializer(building)
            return Response(serializer.data)
        return Response({"detail": "No building found for current user"}, status=404)

    
class FlatViewSet(viewsets.ModelViewSet):
    queryset = Flat.objects.all()
    serializer_class = FlatSerializer
    permission_classes = [AllowAny]

    
    
    def get_queryset(self):
        user = self.request.user
        building_id = self.request.query_params.get('building_id')
        queryset= self.queryset
            
        

        if not user.is_authenticated:
            queryset=queryset.filter(is_occupied=False)
            if building_id:
                queryset=queryset.filter(building_id=building_id)
            return queryset

        if is_super_admin(user):
            if building_id:
                queryset = queryset.filter(building_id=building_id)
            return queryset

        if is_building_admin(user):
            return queryset.filter(building=getattr(user.flat, 'building', None))

        
        return queryset.none()

        


# --- Signup View ---
class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class CurrentMemberView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request):
        try:
            member=request.user.member
            serialzier = MemberSerializer(member)
            return Response(serialzier.data)
        except Member.DoesNotExist:
            return Response({'detail':'Member not found'},status=404)

class SuperAdminDetailView(RetrieveAPIView):
    serializer_class=UserSerializer
    permission_classes=[IsAuthenticated]
    def get_object(self):
        queryset=User.objects.filter(role='admin',flat__isnull=True).first()
        return queryset

        


class BuildingAdminView(RetrieveAPIView):
    serializer_class= UserSerializer
    permission_classes=[IsAuthenticated]

    def get_object(self):
        user = self.request.user
        building = getattr(user.flat, "building",None)
        admin=User.objects.filter(role='admin',flat__building=building).first()

        if not admin:
            raise Exception("No building admin found for this building")
        return admin

# --- User ViewSet (Admin only) ---
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrBuildingAdmin]
    


class MemberViewSet(viewsets.ModelViewSet):
    serializer_class = MemberSerializer
    permission_classes = [IsAdminOrBuildingAdmin]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return Member.objects.select_related("user").all()
        elif is_building_admin(user):
            return Member.objects.select_related("user").filter(user__flat__building=user.flat.building)
        return Member.objects.select_related("user").filter(user=user)

    def update(self, request, *args, **kwargs):
        member = self.get_object()
        user = request.user

        if is_super_admin(user) or user == member.user:
            return super().update(request, *args, **kwargs)
        return Response({'detail': 'Permission denied'}, status=403)
 
    def destroy(self, request, *args, **kwargs):
        if is_super_admin(request.user):
            return super().destroy(request, *args, **kwargs)
        return Response({'detail': 'Only super admins can delete members'}, status=403)

    @action(detail=False, methods=["get", "put"], permission_classes=[permissions.IsAuthenticated], url_path="profile")
    def profile(self, request):
        """Get or update the logged-in user's Member profile"""
        try:
            member = Member.objects.select_related("user").get(user=request.user)
        except Member.DoesNotExist:
            return Response({'detail': 'Member profile not found.'}, status=404)

        if request.method == "GET":
            return Response(self.get_serializer(member).data)

        serializer = self.get_serializer(member, data=request.data, partial=True)
        # print(serializer)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class SpecialChargeViewSet(viewsets.ModelViewSet):
    queryset = SpecialCharge.objects.select_related('building','member__user').all()
    serializer_class = SpecialChargeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return self.queryset
        elif hasattr(user, "flat") and user.flat.building:
            return self.queryset.filter(building=user.flat.building)
        return SpecialCharge.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        building = getattr(user.flat, "building", None)
        member = Member.objects.get(user=user)

        if not building:
            raise PermissionDenied("You are not associated with a building.")
        serializer.save(building=building,member=member)


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
        status='pending'
        if is_building_admin(user):
            status='verified'
       
        try:
            member = Member.objects.get(user=user)
            serializer.save(member=member, status=status)
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


# --- Expense ViewSet ---
class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.select_related("category").all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user= self.request.user
        if is_super_admin(user):
            return self.queryset
        elif is_building_admin(user):
            building = getattr(user.flat,"building",None)
            return self.queryset.filter(building=building)
        return Expense.objects.none()

# --- Category ViewSet ---
class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        
        user = self.request.user
        building = getattr(user.flat, "building",None)

        if is_super_admin(user):
            return Category.objects.all()
        elif building:
            return Category.objects.filter(building=building)
        return Category.objects.none()
        
       




class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    # ✅ Enable filtering, searching, and ordering
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = {
        'seen': ['exact'],
        'income__status': ['exact'],
        'created_at': ['gte', 'lte'],  # ✅ Date range filter
    }
    ordering_fields = ['created_at']
    search_fields = ['message', 'income__transaction_id']

    def get_queryset(self):
        user = self.request.user
        print(user.id)
        print(user.username)
        if is_super_admin(user):
            return Notification.objects.select_related('income','user').order_by('-created_at')
        elif is_building_admin(user):
            building = getattr(user.flat, 'building',None)
            return Notification.objects.select_related('income','user').filter(
                income__member__user__flat__building=building
            ).order_by('-created_at')
        else:
            return Notification.objects.filter(user=user).select_related('income').order_by('-created_at')
    
    

    def retrieve(self, request, pk=None):
        notification = get_object_or_404(Notification, pk=pk)

        # ✅ Ensure user can only access their own notifications
        if request.user.role != 'admin' and notification.user != request.user:
            return Response({"detail": "Not allowed"}, status=403)

        # ✅ Mark as seen when notification is viewed
        if not notification.seen:
            notification.seen = True
            notification.save(update_fields=["seen"])

        return Response(self.get_serializer(notification).data)


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return Announcement.objects.all()
        building = getattr(user.flat, "building", None)
        if building:
            return Announcement.objects.filter(building=building)

        return Announcement.objects.none()

    def perform_create(self, serializer):
        user = self.request.user

        if is_super_admin(user):
            for building in Building.objects.all():
                serializer.save(building=building)
        elif is_building_admin(user):
            building = getattr(user.flat, "building", None)
            if building:
                serializer.save(building=building)
        else:
            raise PermissionDenied("You do not have permission to create announcements.")


class SocietyDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = SocietyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrBuildingAdmin]

    def get_queryset(self):
        user = self.request.user
        building = getattr(user.flat, "building", None)
        if is_super_admin(user):
            return SocietyDocument.objects.all()
        if is_building_admin(user):
            return SocietyDocument.objects.filter(building=building)
        return SocietyDocument.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        building = getattr(user.flat, "building", None)
        serializer.save(building=building)


class ComplainViewSet(viewsets.ModelViewSet):
    serializer_class=ComplaintSerializer
    permission_classes=[permissions.IsAuthenticated]

    def get_queryset(self):
        user=self.request.user
    
        if is_super_admin(user) or is_building_admin(user):
            return Complaint.objects.filter(recipient=user)
        return Complaint.objects.filter(sender=user)
    
    def perform_create(self,serializer):
        sender= self.request.user
        recipient = serializer.validated_data.get("recipient")

        if is_super_admin(recipient):
            serializer.save(sender=sender)
            return 
        
        if is_building_admin(recipient):
            sender_building=getattr(sender.flat,"building",None)
            recipient_building = getattr(recipient.flat,"building",None)
            if sender_building == recipient_building:
                serializer.save(sender=sender)
                return 
        raise PermissionDenied("You can only send complaints to your building admin or super admin.")

        



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from collections import defaultdict
from datetime import date
from calendar import month_abbr
from django.db import models
from django.core.exceptions import PermissionDenied

from .models import Income, Expense, SpecialCharge


# --- Month Range Generator ---
def get_fy_months(start_year):
    months = []
    for m in range(4, 13):
        months.append(f"{month_abbr[m]}-{str(start_year)[-2:]}")
    for m in range(1, 4):
        months.append(f"{month_abbr[m]}-{str(start_year + 1)[-2:]}")
    return months


# --- Member Income Table Data ---
def get_member_income_table(start_year, building):
    months = get_fy_months(start_year)
    start_date = date(start_year, 4, 1)
    end_date = date(start_year + 1, 3, 31)

    incomes = Income.objects.filter(
        building=building,
        date__range=(start_date, end_date),
        status='verified',
    ).select_related("member__user", "member__user__flat", "special_charge")

    member_rows = {}
    total_row = {m: 0 for m in months}
    total_special = defaultdict(int)
    grand_total = 0

    for income in incomes:
        member = income.member
        name = member.user.get_full_name()
        flat = member.user.flat.number if member.user.flat else ""
        month_label = f"{income.date.strftime('%b')}-{str(income.date.year)[-2:]}"
        member_id = member.id

        if member_id not in member_rows:
            member_rows[member_id] = {
                "name": name,
                "flat": flat,
                "monthly": {m: 0 for m in months},
                "special_income": defaultdict(int),
                "total": 0
            }

        if income.special_charge:
            title = income.special_charge.title
            member_rows[member_id]["special_income"][title] += income.amount
            total_special[title] += income.amount
        else:
            member_rows[member_id]["monthly"][month_label] += income.amount
            total_row[month_label] += income.amount

        member_rows[member_id]["total"] += income.amount
        grand_total += income.amount

    # Convert defaultdicts to dicts for JSON
    for row in member_rows.values():
        row["special_income"] = dict(row["special_income"])

    return {
        "members": list(member_rows.values()),
        "total_row": {
            "monthly": total_row,
            "special_income": dict(total_special),
            "total": grand_total
        },
        "months": months
    }


# --- Opening Balance Helper ---
def get_opening_balance_for_table(start_year, building):
    income_total = Income.objects.filter(
        building=building,
        date__lt=date(start_year, 4, 1),
        status='verified',
        special_charge__isnull=True
    ).aggregate(total=models.Sum("amount"))["total"] or 0

    expense_total = Expense.objects.filter(
        building=building,
        date__lt=date(start_year, 4, 1)
    ).aggregate(total=models.Sum("amount"))["total"] or 0

    return income_total - expense_total


# --- Expense Summary ---
def get_expense_summary(start_year, building):
    months = get_fy_months(start_year)
    start_date = date(start_year, 4, 1)
    end_date = date(start_year + 1, 3, 31)

    expenses = Expense.objects.filter(
        building=building,
        date__range=(start_date, end_date)
    )

    category_map = defaultdict(lambda: {
        "category": "",
        "monthly_expenses": {m: 0 for m in months},
        "total_spent": 0
    })

    total_monthly = {m: 0 for m in months}
    total_expense = 0

    for exp in expenses:
        category = exp.category.name if exp.category else "Uncategorized"
        month_label = f"{exp.date.strftime('%b')}-{str(exp.date.year)[-2:]}"
        category_map[category]["category"] = category
        category_map[category]["monthly_expenses"][month_label] += exp.amount
        category_map[category]["total_spent"] += exp.amount

        total_monthly[month_label] += exp.amount
        total_expense += exp.amount

    return {
        "categories": list(category_map.values()),
        "total_monthly_expense": total_monthly,
        "total_expense": total_expense
    }


# --- Final API View ---
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

        # Gather data
        opening_balance = get_opening_balance_for_table(start_year, building)
        income_table = get_member_income_table(start_year, building)
        expense_summary = get_expense_summary(start_year, building)

        total_income = income_table["total_row"]["total"]
        total_expense = expense_summary["total_expense"]
        closing_balance = opening_balance + total_income - total_expense

        return Response({
            "opening_balance": opening_balance,
            "months": income_table["months"],
            "members": income_table["members"],
            "total_row": income_table["total_row"],
            "expenses": expense_summary,
            "closing_balance": closing_balance,
            "total_receipt": total_income
        }, status=status.HTTP_200_OK)
