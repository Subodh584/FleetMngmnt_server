import secrets
import string

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from django.utils import timezone

from .models import DriverDocument, Geofence, LeaveRequest, Location, ProfileImage, UserProfile
from .permissions import IsFleetManager, IsFleetManagerOrReadOnly
from .serializers import (
    ChangePasswordSerializer,
    DriverDocumentSerializer,
    GeofenceSerializer,
    LeaveRequestSerializer,
    LocationSerializer,
    ProfileImageSerializer,
    UserProfileUpdateSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

class RegisterView(generics.CreateAPIView):
    """Register a new user (open endpoint)."""

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': UserSerializer(user, context={'request': request}).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """Retrieve / update the authenticated user's profile."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserProfileUpdateSerializer
        return UserSerializer

    def get_object(self):
        user = self.request.user
        if hasattr(user, 'profile'):
            user.profile.resolve_rest_status()
        return user

    def update(self, request, *args, **kwargs):
        serializer = UserProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        return Response(UserSerializer(request.user, context={'request': request}).data)


class ChangePasswordView(generics.GenericAPIView):
    """Change the authenticated user's password."""

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        
        # Automatically mark first_time_login as False on password change
        profile = request.user.profile
        if profile.first_time_login:
            profile.first_time_login = False
            profile.save(update_fields=['first_time_login'])
            
        return Response({'detail': 'Password updated successfully.'})


class SendCredentialsEmailView(APIView):
    """Send user credentials (userid & password) to the given email address."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        userid = request.data.get('userid')
        password = request.data.get('password')

        # Validate required fields
        errors = {}
        if not email:
            errors['email'] = 'This field is required.'
        if not userid:
            errors['userid'] = 'This field is required.'
        if not password:
            errors['password'] = 'This field is required.'
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Build the email
        subject = 'Your Ochima Login Credentials'
        plain_message = (
            f'Hello,\n\n'
            f'Here are your login credentials for Ochima:\n\n'
            f'Username: {userid}\n'
            f'Password: {password}\n\n'
            f'Please change your password after your first login.\n\n'
            f'Regards,\n'
            f'Ochima Team'
        )
        html_message = (
            f'<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;'
            f'padding:24px;border:1px solid #e0e0e0;border-radius:8px;">'
            f'<h2 style="color:#1a73e8;">Ochima</h2>'
            f'<p>Hello,</p>'
            f'<p>Here are your login credentials:</p>'
            f'<table style="width:100%;border-collapse:collapse;margin:16px 0;">'
            f'<tr><td style="padding:8px;font-weight:bold;">Username</td>'
            f'<td style="padding:8px;">{userid}</td></tr>'
            f'<tr style="background:#f5f5f5;"><td style="padding:8px;font-weight:bold;">Password</td>'
            f'<td style="padding:8px;">{password}</td></tr>'
            f'</table>'
            f'<p style="color:#d32f2f;font-size:14px;">'
            f'Please change your password after your first login.</p>'
            f'<hr style="border:none;border-top:1px solid #e0e0e0;margin:16px 0;">'
            f'<p style="font-size:12px;color:#888;">Ochima Team</p>'
            f'</div>'
        )

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {'detail': f'Failed to send email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({'detail': f'Credentials sent successfully to {email}.'})


class ClockInView(APIView):
    """Driver clocks in — sets driver_status to 'available'."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
        if profile.driver_status == 'in_trip':
            return Response(
                {'detail': 'Cannot clock in while on an active trip. Complete the trip first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if profile.driver_status == 'on_leave':
            return Response(
                {'detail': 'Cannot clock in while on approved leave.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile.driver_status = 'available'
        profile.rest_ends_at = None
        profile.save(update_fields=['driver_status', 'rest_ends_at', 'updated_at'])
        return Response({'driver_status': profile.driver_status, 'detail': 'Clocked in successfully. You are now available.'})


class ClockOutView(APIView):
    """Driver clocks out — sets driver_status to 'clocked_out'."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
        if profile.driver_status == 'in_trip':
            return Response(
                {'detail': 'Cannot clock out while on an active trip. Complete the trip first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile.driver_status = 'clocked_out'
        profile.save(update_fields=['driver_status', 'updated_at'])
        return Response({'driver_status': profile.driver_status, 'detail': 'Clocked out successfully. You are now unavailable.'})


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """List / retrieve users (fleet managers can see all)."""

    queryset = User.objects.select_related('profile').all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['profile__role', 'is_active', 'profile__first_time_login']
    search_fields = ['username', 'first_name', 'last_name', 'email']

    @action(detail=True, methods=['post'])
    def reset_credentials(self, request, pk=None):
        """Fleet manager resets a user's password and returns the new one."""
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'fleet_manager':
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        chars = string.ascii_letters + string.digits + '!@#$%'
        new_password = ''.join(secrets.choice(chars) for _ in range(12))
        user.set_password(new_password)
        user.save()
        return Response({'username': user.username, 'password': new_password})


# ---------------------------------------------------------------------------
# Driver document views
# ---------------------------------------------------------------------------

class DriverDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DriverDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['document_type', 'user']

    def get_queryset(self):
        user = self.request.user
        # Drivers see only their own documents; fleet managers see all
        if hasattr(user, 'profile') and user.profile.role == 'fleet_manager':
            return DriverDocument.objects.select_related('user').all()
        return DriverDocument.objects.select_related('user').filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------------------------------------------------------------------------
# Profile image views
# ---------------------------------------------------------------------------

class ProfileImageViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'fleet_manager':
            return ProfileImage.objects.select_related('user').all()
        return ProfileImage.objects.select_related('user').filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------------------------------------------------------------------------
# Location views
# ---------------------------------------------------------------------------

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsFleetManagerOrReadOnly]
    filterset_fields = ['is_warehouse']
    search_fields = ['name', 'address']


# ---------------------------------------------------------------------------
# Geofence views
# ---------------------------------------------------------------------------

class GeofenceViewSet(viewsets.ModelViewSet):
    queryset = Geofence.objects.select_related('location', 'created_by').all()
    serializer_class = GeofenceSerializer
    permission_classes = [IsFleetManagerOrReadOnly]
    search_fields = ['name']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------------------------------------------------------------------
# Leave request views
# ---------------------------------------------------------------------------

class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'driver']

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'fleet_manager':
            return LeaveRequest.objects.select_related('driver', 'reviewed_by').all()
        return LeaveRequest.objects.select_related('driver', 'reviewed_by').filter(driver=user)

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)
        # Notify all fleet managers of the new leave request
        from comms.models import Notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        leave = serializer.instance
        driver_name = self.request.user.get_full_name() or self.request.user.username
        managers = User.objects.filter(profile__role='fleet_manager')
        Notification.objects.bulk_create([
            Notification(
                user=mgr,
                alert_type='leave_request',
                title='New Leave Request',
                body=f'{driver_name} has requested leave from {leave.start_date} to {leave.end_date}.',
                reference_id=leave.pk,
                reference_type='leave_request',
            )
            for mgr in managers
        ])

    @action(detail=True, methods=['post'], permission_classes=[IsFleetManager])
    def approve(self, request, pk=None):
        leave = self.get_object()
        if leave.status != 'pending':
            return Response({'detail': 'Only pending requests can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        leave.status = 'approved'
        leave.reviewed_by = request.user
        leave.reviewed_at = timezone.now()
        leave.save()
        # Set driver status to on_leave
        profile = leave.driver.profile
        profile.driver_status = 'on_leave'
        profile.save(update_fields=['driver_status', 'updated_at'])
        # Notify driver
        from comms.models import Notification
        Notification.objects.create(
            user=leave.driver,
            alert_type='leave_approved',
            title='Leave Approved',
            body=f'Your leave from {leave.start_date} to {leave.end_date} has been approved.',
            reference_id=leave.pk,
            reference_type='leave_request',
        )
        return Response(LeaveRequestSerializer(leave).data)

    @action(detail=True, methods=['post'], permission_classes=[IsFleetManager])
    def reject(self, request, pk=None):
        leave = self.get_object()
        if leave.status != 'pending':
            return Response({'detail': 'Only pending requests can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)
        leave.status = 'rejected'
        leave.reviewed_by = request.user
        leave.reviewed_at = timezone.now()
        leave.rejection_reason = request.data.get('reason', '')
        leave.save()
        # Notify driver
        from comms.models import Notification
        Notification.objects.create(
            user=leave.driver,
            alert_type='leave_rejected',
            title='Leave Rejected',
            body=f'Your leave request from {leave.start_date} to {leave.end_date} was not approved.',
            reference_id=leave.pk,
            reference_type='leave_request',
        )
        return Response(LeaveRequestSerializer(leave).data)

