from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Geofence, Location, UserProfile
from .permissions import IsFleetManagerOrReadOnly
from .serializers import (
    ChangePasswordSerializer,
    GeofenceSerializer,
    LocationSerializer,
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
                'user': UserSerializer(user).data,
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
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = UserProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        return Response(UserSerializer(request.user).data)


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
        profile.driver_status = 'available'
        profile.save(update_fields=['driver_status', 'updated_at'])
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
    filterset_fields = ['profile__role', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email']


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

