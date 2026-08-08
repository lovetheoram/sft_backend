"""
=============================================================================
👤 USER, MEMBER, SIGNUP & PREVIOUS DUE SERIALIZERS
=============================================================================
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from Finance.models import Member, PreviousDue, Building, Flat
from .building_serializers import FlatSerializer

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)
    invite_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    flat_id = serializers.PrimaryKeyRelatedField(
        queryset=Flat.objects.all(), write_only=True, required=False, allow_null=True
    )
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'phone', 'role',
            'building_id', 'flat_id', 'invite_code'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match."})

        role = attrs.get('role')
        invite_code = attrs.get('invite_code', '').strip()
        building = attrs.get('building_id')
        flat = attrs.get('flat_id')

        if role == 'admin':
            if invite_code == 'SUPERADMIN123':
                pass
            elif invite_code == 'BUILDINGADMIN123':
                if not building or not flat:
                    raise serializers.ValidationError({
                        "detail": "Building and Flat are required for building admin."
                    })
            else:
                raise serializers.ValidationError({
                    "invite_code": "Invalid invite code for admin signup."
                })

        elif role == 'resident':
            if not building or not flat:
                raise serializers.ValidationError({
                    "detail": "Building and Flat are required for residents."
                })

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        invite_code = validated_data.pop('invite_code', None)

        building = validated_data.pop('building_id', None)
        flat = validated_data.pop('flat_id', None)

        if flat:
            flat.is_occupied = True
            flat.save()

        password = validated_data.pop('password')
        user = User(**validated_data)
        user.flat = flat
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    flat = FlatSerializer(read_only=True)
    member_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'flat', 'phone', 'member_id']

    def get_member_id(self, obj):
        return obj.member.id if hasattr(obj, 'member') and obj.member else None


class MemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True)

    class Meta:
        model = Member
        fields = ['id', 'user', 'user_id', 'move_in_date']

    def update(self, instance, validated_data):
        user_data = self.initial_data.get("user", {})
        user = instance.user

        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        return super().update(instance, validated_data)


class PreviousDueSerializer(serializers.ModelSerializer):
    member = MemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(queryset=Member.objects.all(), write_only=True)

    class Meta:
        model = PreviousDue
        fields = ['id', 'member', 'member_id', 'amount', 'reason', 'added_on']

    def create(self, validated_data):
        member = validated_data.pop('member_id')
        return PreviousDue.objects.create(member=member, **validated_data)
