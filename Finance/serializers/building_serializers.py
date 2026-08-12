"""
=============================================================================
🏢 BUILDING, FLAT, CATEGORY & SPECIAL CHARGE SERIALIZERS
=============================================================================
"""

import re
from rest_framework import serializers
from Finance.models import Building, Flat, Category, SpecialCharge


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ['id', 'name', 'address']


class FlatSerializer(serializers.ModelSerializer):
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(queryset=Building.objects.all(), write_only=True)

    class Meta:
        model = Flat
        fields = ['id', 'number', 'is_occupied', 'building', 'building_id']

    def create(self, validated_data):
        building = validated_data.pop('building_id')
        return Flat.objects.create(building=building, **validated_data)


class CategorySerializer(serializers.ModelSerializer):
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Category
        fields = ['id', 'name', 'building', 'building_id']

    def create(self, validated_data):
        building = validated_data.pop('building', None) or validated_data.pop('building_id', None)
        if not building:
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                user = request.user
                building = getattr(getattr(user, "flat", None), "building", None) or getattr(user, "building_admin_for", None)

        name = re.sub(r'\s+', ' ', validated_data.get('name', '').strip())
        if building and name:
            existing = Category.objects.filter(building=building, name__iexact=name).first()
            if existing:
                return existing

        validated_data['name'] = name
        return Category.objects.create(building=building, **validated_data)


class SpecialChargeSerializer(serializers.ModelSerializer):
    member = serializers.StringRelatedField(read_only=True)
    building = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = SpecialCharge
        fields = [
            'id', 'title', 'description', 'amount_expected',
            'due_date', 'building', 'member'
        ]

    def create(self, validated_data):
        return SpecialCharge.objects.create(**validated_data)
