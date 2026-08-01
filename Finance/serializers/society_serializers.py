"""
=============================================================================
📢 ANNOUNCEMENT, COMPLAINT, DOCUMENT & NOTIFICATION SERIALIZERS
=============================================================================
"""

from rest_framework import serializers
from Finance.models import Complaint, Announcement, SocietyDocument, Notification
from .building_serializers import BuildingSerializer
from .user_serializers import UserSerializer
from .finance_serializers import IncomeSerializer


class ComplaintSerializer(serializers.ModelSerializer):
    building = BuildingSerializer(read_only=True)
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Complaint
        fields = ['id', 'recipient', 'sender', 'subject', 'description', 'status', 'created_at', 'building']
        read_only_fields = ['id', 'created_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    building = BuildingSerializer(read_only=True)

    class Meta:
        model = Announcement
        fields = ['id', 'title', 'message', 'building', 'created_at']


class SocietyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocietyDocument
        fields = ['id', 'title', 'file', 'uploaded_at']


class NotificationSerializer(serializers.ModelSerializer):
    income = IncomeSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'income', 'seen', 'created_at']
