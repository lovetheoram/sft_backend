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
    Notification, Announcement, SocietyDocument, Complaint, Building
)
from Finance.serializers import (
    NotificationSerializer, AnnouncementSerializer,
    SocietyDocumentSerializer, ComplaintSerializer
)
from .permissions import is_super_admin, is_building_admin, IsAdminOrBuildingAdmin


def _paginate_queryset(request, queryset, serializer_class):
    """
    Shared helper: returns limit/offset paginated response.
    Falls back to full list if no 'limit' param present.
    Response: { count, results, has_more, limit, offset }
    """
    limit_param = request.query_params.get('limit')
    if limit_param is None:
        # No pagination requested — return full list
        return Response(serializer_class(queryset, many=True).data)

    try:
        limit = max(1, min(int(limit_param), 100))  # cap at 100
        offset = max(0, int(request.query_params.get('offset', 0)))
    except (ValueError, TypeError):
        limit, offset = 10, 0

    total = queryset.count()
    page_qs = queryset[offset: offset + limit]
    serialized = serializer_class(page_qs, many=True).data
    return Response({
        'count': total,
        'results': serialized,
        'has_more': (offset + limit) < total,
        'limit': limit,
        'offset': offset,
    })


class NotificationViewSet(viewsets.ModelViewSet):
    """
    [ONE-TO-ONE SYSTEM] Handles direct personal alerts.
    Optimized with select_related to eliminate N+1 database queries.
    Supports: ?limit=10&offset=0&seen=false&income__status=pending
    """
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
        base_query = Notification.objects.select_related(
            'income',
            'income__member',
            'income__member__user',
            'income__member__user__flat',
            'income__member__user__flat__building',
            'income__building',
            'income__special_charge',
            'user',
            'user__flat',
            'user__flat__building'
        ).order_by('-created_at')

        if is_super_admin(user):
            return base_query

        # Safe traversal using chained getattrs to find the building domain
        user_building = getattr(getattr(user, 'flat', None), 'building', None)

        if is_building_admin(user):
            if user_building:
                return base_query.filter(Q(user=user) | Q(income__member__user__flat__building=user_building))
            return base_query.filter(user=user)

        # Regular residents can strictly see their own one-to-one inbox stream
        return base_query.filter(user=user)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        return _paginate_queryset(request, qs, self.get_serializer_class())

    def retrieve(self, request, pk=None):
        # FIX: Query through get_queryset bounds to stop users from accessing random IDs
        notification = get_object_or_404(self.get_queryset(), pk=pk)

        # Mark as read automatically when opened
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
        # Only admins can publish or edit announcements; residents get safe read-only access
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsAdminOrBuildingAdmin()]

    def get_queryset(self):
        user = self.request.user
        base_qs = Announcement.objects.select_related('building').order_by('-created_at')
        if is_super_admin(user):
            return base_qs.all()

        user_building = getattr(getattr(user, 'flat', None), 'building', None)

        # FIX: Residents see global announcements (building=None) OR notices for their building block
        if user_building:
            return base_qs.filter(building__in=[user_building, None])

        return base_qs.filter(building=None)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return _paginate_queryset(request, qs, self.get_serializer_class())

    def perform_create(self, serializer):
        user = self.request.user

        # FIX: Repetitive .save() loops do not clone objects in Django.
        # Instead, Super Admins leave building=None to broadcast a truly global announcement.
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
        # Protect uploads: Only management roles can write/edit/delete paperwork rows
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsAdminOrBuildingAdmin()]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return SocietyDocument.objects.all().order_by('-id')

        user_building = getattr(getattr(user, 'flat', None), 'building', None)

        # FIX: Regular tenants can view documents matching their community block
        if user_building:
            return SocietyDocument.objects.filter(building=user_building).order_by('-id')

        return SocietyDocument.objects.none()

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return _paginate_queryset(request, qs, self.get_serializer_class())

    def perform_create(self, serializer):
        user = self.request.user

        # Super Admin uploads can target a specific building via the payload data
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
        base_qs = Complaint.objects.select_related('sender', 'recipient', 'building').order_by('-created_at')
        if is_super_admin(user) or is_building_admin(user):
            return base_qs.filter(recipient=user)
        return base_qs.filter(sender=user)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        # Optional status filter
        status_filter = request.query_params.get('status')
        if status_filter and status_filter != 'all':
            qs = qs.filter(status=status_filter)
        return _paginate_queryset(request, qs, self.get_serializer_class())

    def perform_create(self, serializer):
        sender = self.request.user
        recipient = serializer.validated_data.get("recipient")

        if not recipient:
            raise ValidationError({"recipient": "An explicit recipient target manager must be provided."})

        # Scenario 1: Sending directly up to a Super Admin
        if is_super_admin(recipient):
            serializer.save(sender=sender)
            return

        # Scenario 2: Sending up to a local Building Admin
        if is_building_admin(recipient):
            # FIX: Standardized secure nested parsing using defensive chaining
            sender_building = getattr(getattr(sender, 'flat', None), 'building', None)
            recipient_building = getattr(getattr(recipient, 'flat', None), 'building', None)

            if sender_building and sender_building == recipient_building:
                serializer.save(sender=sender)
                return

        raise PermissionDenied("You can only route escalation tickets to your direct Building Administrator or a global Super Admin.")

