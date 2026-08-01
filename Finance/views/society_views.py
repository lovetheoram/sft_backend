"""
=============================================================================
📢 SOCIETY MANAGEMENT VIEWS (Announcements, Complaints, Documents, Notifications)
=============================================================================
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from Finance.models import (
    Notification, Announcement, SocietyDocument, Complaint, Building
)
from Finance.serializers import (
    NotificationSerializer, AnnouncementSerializer,
    SocietyDocumentSerializer, ComplaintSerializer
)
from .permissions import is_super_admin, is_building_admin, IsAdminOrBuildingAdmin


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = {
        'seen': ['exact'],
        'income__status': ['exact'],
        'created_at': ['gte', 'lte'],
    }
    ordering_fields = ['created_at']
    search_fields = ['message', 'income__transaction_id']

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return Notification.objects.select_related('income', 'user').order_by('-created_at')
        elif is_building_admin(user):
            building = getattr(user.flat, 'building', None)
            return Notification.objects.select_related('income', 'user').filter(
                income__member__user__flat__building=building
            ).order_by('-created_at')
        else:
            return Notification.objects.filter(user=user).select_related('income').order_by('-created_at')

    def retrieve(self, request, pk=None):
        notification = get_object_or_404(Notification, pk=pk)

        if request.user.role != 'admin' and notification.user != request.user:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

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
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user) or is_building_admin(user):
            return Complaint.objects.filter(recipient=user)
        return Complaint.objects.filter(sender=user)

    def perform_create(self, serializer):
        sender = self.request.user
        recipient = serializer.validated_data.get("recipient")

        if is_super_admin(recipient):
            serializer.save(sender=sender)
            return

        if is_building_admin(recipient):
            sender_building = getattr(sender.flat, "building", None)
            recipient_building = getattr(recipient.flat, "building", None)
            if sender_building == recipient_building:
                serializer.save(sender=sender)
                return
        raise PermissionDenied("You can only send complaints to your building admin or super admin.")
