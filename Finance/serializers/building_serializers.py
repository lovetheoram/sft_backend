"""
=============================================================================
🏢 BUILDING, FLAT, CATEGORY & SPECIAL CHARGE SERIALIZERS
=============================================================================
"""

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
    building_id = serializers.PrimaryKeyRelatedField(queryset=Building.objects.all(), write_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'building', 'building_id']

    def create(self, validated_data):
        building = validated_data.pop('building_id')
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
