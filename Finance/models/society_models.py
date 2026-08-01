"""
=============================================================================
📢 ANNOUNCEMENT, COMPLAINT, DOCUMENT & NOTIFICATION MODELS
=============================================================================
"""

from django.db import models
from .building_models import Building
from .user_models import User
from .finance_models import Income


class Announcement(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, null=True, blank=True, default=1)
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Announcement: {self.title}"


class Complaint(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
    ]
    building = models.ForeignKey(Building, on_delete=models.CASCADE, null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints_made')
    recipient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints_received')
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} - from {self.sender.username} to {self.recipient.username if self.recipient else 'N/A'}"


class SocietyDocument(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, null=True, blank=True, default=1)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    income = models.ForeignKey(Income, on_delete=models.CASCADE, null=True, blank=True)
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"message {self.user.username}-{self.created_at}"
