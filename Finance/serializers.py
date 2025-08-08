from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Member, Income, Expense, Category, PreviousDue,
    Complaint, Announcement, SocietyDocument,Building,Flat
)

from rest_framework import serializers
from .models import Notification,SpecialCharge

User = get_user_model()


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


from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Building, Flat

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
        # Password match check
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match."})

        role = attrs.get('role')
        invite_code = attrs.get('invite_code', '').strip()
        building = attrs.get('building_id')
        flat = attrs.get('flat_id')

        if role == 'admin':
            if invite_code == 'SUPERADMIN123':
                # Superadmin – no building/flat required
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

        # Assign flat and building admin
        user.flat = flat
        # if user.role == 'admin' and invite_code == 'BUILDINGADMIN123':
        #     user.building_admin_for = building

        user.set_password(password)
        user.save()
        return user


# --- User ---
class UserSerializer(serializers.ModelSerializer):
    flat=FlatSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'flat', 'phone']

# --- Member ---
class MemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True)

    class Meta:
        model = Member
        fields = ['id', 'user', 'user_id', 'move_in_date']

    def update(self,instance,validated_data):
        user_data = self.initial_data.get("user",{})
        user = instance.user

        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        return super().update(instance,validated_data)
    
# --- Category ---
class CategorySerializer(serializers.ModelSerializer):
    building=BuildingSerializer(read_only=True)
    building_id=serializers.PrimaryKeyRelatedField(queryset=Building.objects.all(),write_only=True)
    class Meta:
        model = Category
        fields = ['id', 'name','building','building_id']
    
    def create(self,validated_data):
        building=validated_data.pop('building_id')
        return Category.objects.create(building=building,**validated_data)

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
    
# --- Income ---
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
             'id','member', 'amount', 'date', 'description',
            'transaction_id', 'payment_proof', 'created_at', 'status',
            'building','building_id','special_charge','special_charge_id'
        ]
    def create(self,validated_data):
        building=validated_data.pop('building_id')
        special_charge= validated_data.pop('special_charge_id',None)
        return Income.objects.create(building=building, special_charge=special_charge, **validated_data)

# --- Expense ---
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

# --- PreviousDue ---
class PreviousDueSerializer(serializers.ModelSerializer):
    member = MemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(queryset=Member.objects.all(), write_only=True)

    class Meta:
        model = PreviousDue
        fields = ['id', 'member', 'member_id', 'amount', 'reason', 'added_on']

    def create(self, validated_data):
        member = validated_data.pop('member_id')
        return PreviousDue.objects.create(member=member, **validated_data)

# --- Complaint ---
class ComplaintSerializer(serializers.ModelSerializer):
    building = BuildingSerializer(read_only=True)
    sender=UserSerializer(read_only=True)
    class Meta:
        model = Complaint
        fields = ['id', 'recipient', 'sender','subject', 'description', 'status', 'created_at','building']
        read_only_fields = ['id', 'created_at']

# --- Announcement ---
class AnnouncementSerializer(serializers.ModelSerializer):
    building = BuildingSerializer(read_only=True)
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'message', 'building','created_at']

# --- SocietyDocument ---
class SocietyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocietyDocument
        fields = ['id', 'title', 'file', 'uploaded_at']



class NotificationSerializer(serializers.ModelSerializer):
    income = IncomeSerializer(read_only=True)  # ✅ Nest full income data
    
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'income', 'seen', 'created_at']