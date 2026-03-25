from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import DriverDocument, Geofence, LeaveRequest, Location, ProfileImage, UserProfile

User = get_user_model()


# ---------------------------------------------------------------------------
# User / Auth serializers
# ---------------------------------------------------------------------------

class UserProfileSerializer(serializers.ModelSerializer):
    driving_licence = serializers.SerializerMethodField()
    aadhaar_card = serializers.SerializerMethodField()

    def get_driving_licence(self, obj):
        doc = obj.user.documents.filter(document_type='driving_license').order_by('-uploaded_at').first()
        if doc and doc.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(doc.file.url)
            return doc.file.url
        return None

    def get_aadhaar_card(self, obj):
        doc = obj.user.documents.filter(document_type='aadhar').order_by('-uploaded_at').first()
        if doc and doc.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(doc.file.url)
            return doc.file.url
        return None

    class Meta:
        model = UserProfile
        fields = [
            'role', 'phone', 'profile_photo', 'is_active', 'first_time_login',
            'driver_status', 'rest_ends_at', 'driving_licence', 'aadhaar_card',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'rest_ends_at']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']
        read_only_fields = ['id']


class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, default='')
    last_name = serializers.CharField(max_length=150, required=False, default='')
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    phone = serializers.CharField(max_length=20, required=False, default='')

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists.')
        return value

    def create(self, validated_data):
        role = validated_data.pop('role')
        phone = validated_data.pop('phone', '')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        # The post_save signal auto-creates a profile, so update it
        # instead of creating a duplicate.
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.phone = phone
        profile.save(update_fields=['role', 'phone'])
        return user


class UserProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False)
    profile_photo = serializers.ImageField(required=False)
    first_time_login = serializers.BooleanField(required=False)

    def update(self, user, validated_data):
        user.first_name = validated_data.get('first_name', user.first_name)
        user.last_name = validated_data.get('last_name', user.last_name)
        user.email = validated_data.get('email', user.email)
        user.save()
        profile = user.profile
        if 'phone' in validated_data:
            profile.phone = validated_data['phone']
        if 'profile_photo' in validated_data:
            profile.profile_photo = validated_data['profile_photo']
        if 'first_time_login' in validated_data:
            profile.first_time_login = validated_data['first_time_login']
        profile.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value


# ---------------------------------------------------------------------------
# Location serializers
# ---------------------------------------------------------------------------

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'
        read_only_fields = ['created_at']


# ---------------------------------------------------------------------------
# Driver document serializers
# ---------------------------------------------------------------------------

class DriverDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverDocument
        fields = '__all__'
        read_only_fields = ['user', 'uploaded_at', 'updated_at']


# ---------------------------------------------------------------------------
# Profile image serializers
# ---------------------------------------------------------------------------

class ProfileImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileImage
        fields = '__all__'
        read_only_fields = ['user', 'uploaded_at', 'updated_at']


# ---------------------------------------------------------------------------
# Geofence serializers
# ---------------------------------------------------------------------------

class GeofenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Geofence
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']


# ---------------------------------------------------------------------------
# Leave request serializers
# ---------------------------------------------------------------------------

class LeaveRequestSerializer(serializers.ModelSerializer):
    driver_name = serializers.SerializerMethodField()

    def get_driver_name(self, obj):
        return obj.driver.get_full_name() or obj.driver.username

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'driver', 'driver_name', 'start_date', 'end_date', 'reason',
            'status', 'reviewed_by', 'reviewed_at', 'rejection_reason',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['driver', 'status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'created_at', 'updated_at']
