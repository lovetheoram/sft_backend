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
from django.core.exceptions import PermissionDenied
from .services import get_financial_summary


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

