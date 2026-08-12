"""
=============================================================================
🏢 BUILDING, FLAT, CATEGORY & SPECIAL CHARGE MODELS
=============================================================================
"""

from django.db import models

MONTH_CHOICES = [
    ("Jan", "January"), ("Feb", "February"), ("Mar", "March"),
    ("Apr", "April"), ("May", "May"), ("Jun", "June"),
    ("Jul", "July"), ("Aug", "August"), ("Sep", "September"),
    ("Oct", "October"), ("Nov", "November"), ("Dec", "December"),
]

ROLE_CHOICES = [
    ("admin", "Admin"),
    ("resident", "Resident"),
    ("staff", "Staff"),
]


class Building(models.Model):
    name = models.CharField(max_length=100, unique=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Flat(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='flats')
    number = models.CharField(max_length=10)
    is_occupied = models.BooleanField(default=False)

    class Meta:
        unique_together = ('building', 'number')

    def __str__(self):
        return f"{self.building.name} - {self.number}"


class Category(models.Model):
    name = models.CharField(max_length=100)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('building', 'name')
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.name} ({self.building.name})" if self.building else self.name


class SpecialCharge(models.Model):
    member = models.ForeignKey('Finance.Member', on_delete=models.CASCADE)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    amount_expected = models.IntegerField()
    due_date = models.DateField()

    def __str__(self):
        return f"{self.title} ({self.building.name})"
