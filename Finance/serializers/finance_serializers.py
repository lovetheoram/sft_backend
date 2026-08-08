"""
=============================================================================
💵 INCOME & EXPENSE SERIALIZERS
=============================================================================
"""

from rest_framework import serializers
from Finance.models import Income, Expense, Building, SpecialCharge, Category, Member
from .building_serializers import BuildingSerializer, CategorySerializer
from .user_serializers import MemberSerializer


class IncomeSerializer(serializers.ModelSerializer):
    member = MemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )
    user_id = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True
    )
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

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
            'id', 'member', 'member_id', 'user_id', 'amount', 'date', 'description',
            'transaction_id', 'payment_proof', 'created_at', 'status',
            'building', 'building_id', 'special_charge', 'special_charge_id'
        ]

    def create(self, validated_data):
        member = validated_data.pop('member', None)
        member_id = validated_data.pop('member_id', None)
        user_id = validated_data.pop('user_id', None)

        final_member = member or member_id
        if final_member is None and user_id is not None:
            final_member, _ = Member.objects.get_or_create(user_id=user_id)

        building = validated_data.pop('building', None)
        building_id = validated_data.pop('building_id', None)
        final_building = building or building_id

        special_charge = validated_data.pop('special_charge', None)
        special_charge_id = validated_data.pop('special_charge_id', None)
        final_special_charge = special_charge or special_charge_id

        if final_member is not None:
            validated_data['member'] = final_member
        if final_building is not None:
            validated_data['building'] = final_building
        if final_special_charge is not None:
            validated_data['special_charge'] = final_special_charge

        return Income.objects.create(**validated_data)

    def update(self, instance, validated_data):
        member_id = validated_data.pop('member_id', None)
        user_id = validated_data.pop('user_id', None)
        if member_id is not None:
            instance.member = member_id
        elif user_id is not None:
            instance.member, _ = Member.objects.get_or_create(user_id=user_id)

        building_id = validated_data.pop('building_id', None)
        if building_id is not None:
            instance.building = building_id

        if 'special_charge_id' in self.initial_data:
            special_charge_id = validated_data.pop('special_charge_id', None)
            instance.special_charge = special_charge_id

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class ExpenseSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_id', 'building', 'building_id',
            'amount', 'date', 'description', 'bill_number',
            'bill_attachment', 'created_at'
        ]

    def to_internal_value(self, data):
        mutable_data = data.copy() if hasattr(data, 'copy') else dict(data)
        if 'category' in mutable_data and 'category_id' not in mutable_data:
            mutable_data['category_id'] = mutable_data['category']
        if 'building' in mutable_data and 'building_id' not in mutable_data:
            mutable_data['building_id'] = mutable_data['building']
        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        category = attrs.get('category_id') or attrs.get('category')
        if not category and not self.instance:
            raise serializers.ValidationError({'category_id': 'Expense category is required.'})
        return attrs

    def create(self, validated_data):
        category = validated_data.pop('category', None)
        category_id = validated_data.pop('category_id', None)
        final_category = category or category_id

        building = validated_data.pop('building', None)
        building_id = validated_data.pop('building_id', None)
        final_building = building or building_id

        if final_category is not None:
            validated_data['category'] = final_category
        if final_building is not None:
            validated_data['building'] = final_building

        return Expense.objects.create(**validated_data)
