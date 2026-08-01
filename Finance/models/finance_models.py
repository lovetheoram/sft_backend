"""
=============================================================================
💵 INCOME & EXPENSE MODELS
=============================================================================
"""

from django.db import models
from .building_models import Building, Category, SpecialCharge
from .user_models import Member


class Income(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('fraud', 'Fraud'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    special_charge = models.ForeignKey(SpecialCharge, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.IntegerField()
    date = models.DateField()
    description = models.TextField(blank=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_proof = models.FileField(upload_to='payment_proofs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        base = f"{self.member.user.get_full_name()}: ₹{self.amount} ({self.date.strftime('%b-%Y')})"
        return f"Income - {base}" if not self.special_charge else f"Special - {self.special_charge.title} - {base}"


class Expense(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    amount = models.IntegerField()
    date = models.DateField()
    description = models.TextField(blank=True)
    bill_number = models.CharField(max_length=100, blank=True, null=True)
    bill_attachment = models.FileField(upload_to='expense_bills/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def month(self):
        return self.date.strftime("%b")

    @property
    def year(self):
        return self.date.year

    def __str__(self):
        return f"Expense - {self.category.name}: ₹{self.amount} ({self.month}-{self.year})"
