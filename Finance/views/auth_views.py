"""
=============================================================================
🔐 AUTHENTICATION & USER MANAGEMENT VIEWS
=============================================================================
"""

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import RetrieveAPIView
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken

from Finance.models import User, Member
from Finance.serializers import (
    UserSerializer, MemberSerializer, SignupSerializer
)
from .permissions import is_super_admin, is_building_admin, IsAdminOrBuildingAdmin


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
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            member = request.user.member
            serializer = MemberSerializer(member)
            return Response(serializer.data)
        except Member.DoesNotExist:
            return Response({'detail': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)


class SuperAdminDetailView(RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return User.objects.filter(role='admin', flat__isnull=True).first()


class BuildingAdminView(RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        building = getattr(user.flat, "building", None)
        admin = User.objects.filter(role='admin', flat__building=building).first()
        if not admin:
            raise Exception("No building admin found for this building")
        return admin


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
        return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        if is_super_admin(request.user):
            return super().destroy(request, *args, **kwargs)
        return Response({'detail': 'Only super admins can delete members'}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=False, methods=["get", "put", "patch"], permission_classes=[permissions.IsAuthenticated], url_path="profile")
    def profile(self, request):
        try:
            member = Member.objects.select_related("user").get(user=request.user)
        except Member.DoesNotExist:
            return Response({'detail': 'Member profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "GET":
            return Response(self.get_serializer(member).data)

        # Dynamically set partial=True ONLY if the method is PATCH
        is_partial = (request.method == "PATCH")

        serializer = self.get_serializer(member, data=request.data, partial=is_partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
