"""
=============================================================================
💵 INCOME & EXPENSE SERIALIZERS
=============================================================================
"""

from rest_framework import serializers
from Finance.models import Income, Expense, Building, SpecialCharge, Category
from .building_serializers import BuildingSerializer, CategorySerializer
from .user_serializers import MemberSerializer


class IncomeSerializer(serializers.ModelSerializer):
    member = MemberSerializer(read_only=True)
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(queryset=Building.objects.all(), write_only=True)

    special_charge = serializers.StringRelatedField(read_only=True)
    special_charge_id = serializers.PrimaryKeyRelatedField(
        queryset=SpecialCharge.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Income
        fields = [
            'id', 'member', 'amount', 'date', 'description',
            'transaction_id', 'payment_proof', 'created_at', 'status',
            'building', 'building_id', 'special_charge', 'special_charge_id'
        ]

    def create(self, validated_data):
        building = validated_data.pop('building_id')
        special_charge = validated_data.pop('special_charge_id', None)
        return Income.objects.create(building=building, special_charge=special_charge, **validated_data)


class ExpenseSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), write_only=True)
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(queryset=Building.objects.all(), write_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_id', 'building', 'building_id',
            'amount', 'date', 'description', 'bill_number',
            'bill_attachment', 'created_at'
        ]

    def create(self, validated_data):
        category = validated_data.pop('category_id')
        building = validated_data.pop('building_id')
        return Expense.objects.create(category=category, building=building, **validated_data)
