"""
=============================================================================
📢 ANNOUNCEMENT, COMPLAINT, DOCUMENT & NOTIFICATION SERIALIZERS
=============================================================================
"""

from rest_framework import serializers
from Finance.models import Complaint, ComplaintComment, Announcement, SocietyDocument, Notification
from .building_serializers import BuildingSerializer
from .user_serializers import UserSerializer
from .finance_serializers import IncomeSerializer


class ComplaintCommentSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = ComplaintComment
        fields = ['id', 'complaint', 'sender', 'message', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at']


class ComplaintSerializer(serializers.ModelSerializer):
    building = BuildingSerializer(read_only=True)
    sender = UserSerializer(read_only=True)
    comments = ComplaintCommentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Complaint
        fields = ['id', 'recipient', 'sender', 'subject', 'description', 'admin_remark', 'status', 'status_display', 'comments', 'created_at', 'building']
        read_only_fields = ['id', 'created_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    building = BuildingSerializer(read_only=True)
    author_type = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ['id', 'title', 'message', 'building', 'author_type', 'created_at']

    def get_author_type(self, obj):
        if not obj.building:
            return "Super Admin (Global Notice)"
        return f"Building Admin ({obj.building.name})"


class SocietyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocietyDocument
        fields = ['id', 'title', 'file', 'uploaded_at']


class NotificationSerializer(serializers.ModelSerializer):
    income = IncomeSerializer(read_only=True)
    complaint = ComplaintSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'income', 'complaint', 'seen', 'created_at']
