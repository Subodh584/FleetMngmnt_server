from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
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
        return Response({'detail': 'Password updated successfully.'})


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
