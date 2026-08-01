"""
=============================================================================
🏢 BUILDING, FLAT & CATEGORY MANAGEMENT VIEWS
=============================================================================
"""

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied

from Finance.models import Building, Flat, Category, SpecialCharge, Member
from Finance.serializers import (
    BuildingSerializer, FlatSerializer, CategorySerializer, SpecialChargeSerializer
)
from .permissions import is_super_admin, is_building_admin, IsSuperAdmin


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
        return Response({"detail": "No building found for current user"}, status=status.HTTP_404_NOT_FOUND)


class FlatViewSet(viewsets.ModelViewSet):
    queryset = Flat.objects.all()
    serializer_class = FlatSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = self.request.user
        building_id = self.request.query_params.get('building_id')
        queryset = self.queryset

        if not user.is_authenticated:
            queryset = queryset.filter(is_occupied=False)
            if building_id:
                queryset = queryset.filter(building_id=building_id)
            return queryset

        if is_super_admin(user):
            if building_id:
                queryset = queryset.filter(building_id=building_id)
            return queryset

        if is_building_admin(user):
            return queryset.filter(building=getattr(user.flat, 'building', None))

        return queryset.none()


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        building = getattr(user.flat, "building", None)

        if is_super_admin(user):
            return Category.objects.all()
        elif building:
            return Category.objects.filter(building=building)
        return Category.objects.none()


class SpecialChargeViewSet(viewsets.ModelViewSet):
    queryset = SpecialCharge.objects.select_related('building', 'member__user').all()
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
        serializer.save(building=building, member=member)
