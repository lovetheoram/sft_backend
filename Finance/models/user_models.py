"""
=============================================================================
👤 USER, MEMBER & PREVIOUS DUE MODELS
=============================================================================
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from .building_models import Flat, ROLE_CHOICES


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='resident')
    flat = models.OneToOneField(Flat, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.username} - {self.flat}"


class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    move_in_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.flat})"


class PreviousDue(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.IntegerField()
    reason = models.CharField(max_length=255)
    added_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Due - {self.member.user.get_full_name()}: ₹{self.amount} for {self.reason}"
