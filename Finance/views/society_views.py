"""
=============================================================================
📢 SOCIETY MANAGEMENT VIEWS (Announcements, Complaints, Documents, Notifications)
=============================================================================
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q

from Finance.models import (
    Notification, Announcement, SocietyDocument, Complaint, ComplaintComment, Building
)
from Finance.serializers import (
    NotificationSerializer, AnnouncementSerializer,
    SocietyDocumentSerializer, ComplaintSerializer, ComplaintCommentSerializer
)
from .permissions import IsAdminOrBuildingAdmin, is_super_admin, is_building_admin

def _paginate_queryset(request, queryset, serializer_class):
    limit = int(request.query_params.get("limit", 10))
    offset = int(request.query_params.get("offset", 0))
    total = queryset.count()
    results = queryset[offset : offset + limit]
    serializer = serializer_class(results, many=True)
    return Response({
        "count": total,
        "results": serializer.data,
        "has_more": (offset + limit) < total,
        "limit": limit,
        "offset": offset,
    })


class NotificationViewSet(viewsets.ModelViewSet):
    """
    [NOTIFICATIONS INBOX] Activity feed for verified payments, reject alerts, and system announcements.
    Supports: ?limit=10&offset=0&seen=false
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.select_related(
            'income',
            'income__member',
            'income__member__user',
            'income__member__user__flat',
            'income__member__user__flat__building',
            'income__building',
            'income__special_charge',
            'complaint',
            'complaint__sender',
            'complaint__recipient',
            'complaint__building',
            'user',
            'user__flat',
            'user__flat__building'
        ).prefetch_related(
            'complaint__comments',
            'complaint__comments__sender'
        ).filter(user=user).exclude(message__icontains="submitted ₹").order_by('-created_at')

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        return _paginate_queryset(request, qs, self.get_serializer_class())

    def retrieve(self, request, pk=None):
        notification = get_object_or_404(self.get_queryset(), pk=pk)

        if not notification.seen:
            notification.seen = True
            notification.save(update_fields=["seen"])

        return Response(self.get_serializer(notification).data)


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    [TOP-TO-BOTTOM SYSTEM] Broadcast board for official communications.
    Supports: ?limit=10&offset=0
    """
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsAdminOrBuildingAdmin()]

    def get_queryset(self):
        user = self.request.user
        base_qs = Announcement.objects.select_related('building').order_by('-created_at')
        if is_super_admin(user):
            return base_qs.all()

        user_building = getattr(getattr(user, 'flat', None), 'building', None)
        if user_building:
            return base_qs.filter(building__in=[user_building, None])

        return base_qs.filter(building=None)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return _paginate_queryset(request, qs, self.get_serializer_class())

    def perform_create(self, serializer):
        user = self.request.user
        if is_super_admin(user):
            serializer.save(building=None)
            return

        if is_building_admin(user):
            user_building = getattr(getattr(user, 'flat', None), 'building', None)
            if not user_building:
                raise PermissionDenied("You must be assigned to an active building profile to publish updates.")
            serializer.save(building=user_building)


class SocietyDocumentViewSet(viewsets.ModelViewSet):
    """
    [KNOWLEDGE BASE] Shared official society documentation file archive repository.
    Supports: ?limit=10&offset=0
    """
    serializer_class = SocietyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsAdminOrBuildingAdmin()]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return SocietyDocument.objects.all().order_by('-id')

        user_building = getattr(getattr(user, 'flat', None), 'building', None)
        if user_building:
            return SocietyDocument.objects.filter(building=user_building).order_by('-id')

        return SocietyDocument.objects.none()

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return _paginate_queryset(request, qs, self.get_serializer_class())

    def perform_create(self, serializer):
        user = self.request.user
        if is_super_admin(user):
            serializer.save()
            return

        user_building = getattr(getattr(user, 'flat', None), 'building', None)
        if not user_building:
            raise PermissionDenied("You must be linked to a building layout to upload documentation files.")
        serializer.save(building=user_building)


class ComplainViewSet(viewsets.ModelViewSet):
    """
    [BOTTOM-TO-TOP SYSTEM] Helpdesk and ticketing support board.
    Supports: ?limit=10&offset=0&status=open
    """
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_qs = Complaint.objects.select_related('sender', 'recipient', 'building').prefetch_related('comments', 'comments__sender').order_by('-created_at')
        if is_super_admin(user) or is_building_admin(user):
            return base_qs.filter(Q(recipient=user) | Q(sender=user))
        return base_qs.filter(sender=user)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        status_filter = request.query_params.get('status')
        if status_filter and status_filter != 'all':
            qs = qs.filter(status=status_filter)
        return _paginate_queryset(request, qs, self.get_serializer_class())

    def perform_create(self, serializer):
        sender = self.request.user
        recipient = serializer.validated_data.get("recipient")
        subject = serializer.validated_data.get("subject", "General Issue")

        if not recipient:
            raise ValidationError({"recipient": "An explicit recipient target manager must be provided."})

        complaint = None
        if is_super_admin(recipient):
            complaint = serializer.save(sender=sender)
        elif is_building_admin(recipient):
            sender_building = getattr(getattr(sender, 'flat', None), 'building', None)
            recipient_building = getattr(getattr(recipient, 'flat', None), 'building', None)

            if sender_building and sender_building == recipient_building:
                complaint = serializer.save(sender=sender)
            else:
                raise PermissionDenied("You can only route escalation tickets to your direct Building Administrator or a global Super Admin.")
        else:
            raise PermissionDenied("You can only route escalation tickets to your direct Building Administrator or a global Super Admin.")

        if complaint and recipient:
            Notification.objects.create(
                user=recipient,
                message=f"⚠️ New Complaint Ticket: '{subject}' submitted by {sender.username}.",
                complaint=complaint,
                seen=False
            )

    def perform_update(self, serializer):
        updated_complaint = serializer.save()
        user = self.request.user
        target_user = updated_complaint.sender if user != updated_complaint.sender else updated_complaint.recipient

        if target_user:
            Notification.objects.create(
                user=target_user,
                message=f"⚠️ Ticket #{updated_complaint.id} '{updated_complaint.subject}' updated to status: {updated_complaint.get_status_display()}.",
                complaint=updated_complaint,
                seen=False
            )


class ComplaintCommentViewSet(viewsets.ModelViewSet):
    """
    Threaded ticket comment endpoints for complaint resolution follow-ups.
    """
    serializer_class = ComplaintCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        complaint_id = self.request.query_params.get('complaint_id')
        base_qs = ComplaintComment.objects.select_related('sender', 'complaint')
        if complaint_id:
            base_qs = base_qs.filter(complaint_id=complaint_id)
        if is_super_admin(user) or is_building_admin(user):
            return base_qs.filter(Q(complaint__recipient=user) | Q(complaint__sender=user))
        return base_qs.filter(complaint__sender=user)

    def perform_create(self, serializer):
        sender = self.request.user
        comment = serializer.save(sender=sender)
        complaint = comment.complaint

        target_user = complaint.recipient if sender == complaint.sender else complaint.sender
        if target_user:
            Notification.objects.create(
                user=target_user,
                message=f"💬 Ticket #{complaint.id} comment from {sender.username}: {comment.message[:60]}",
                complaint=complaint,
                seen=False
            )

