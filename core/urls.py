from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

# ==========================================
# REST Framework Router Initialization
# ==========================================
router = DefaultRouter()

# Register core data viewsets via the automatic router
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'locations', views.LocationViewSet, basename='location')
router.register(r'geofences', views.GeofenceViewSet, basename='geofence')
router.register(r'driver-documents', views.DriverDocumentViewSet, basename='driver-document')
router.register(r'profile-images', views.ProfileImageViewSet, basename='profile-image')
router.register(r'leave-requests', views.LeaveRequestViewSet, basename='leave-request')


# ==========================================
# Application URL Patterns
# ==========================================
urlpatterns = [
    # ---- Authentication & Identity Flow ----
    path('auth/register/', views.RegisterView.as_view(), name='auth-register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # ---- Profile Management ----
    path('auth/me/', views.MeView.as_view(), name='auth-me'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='auth-change-password'),
    path('auth/send-credentials/', views.SendCredentialsEmailView.as_view(), name='auth-send-credentials'),
    
    # ---- Driver Operational Status ----
    path('auth/clock-in/', views.ClockInView.as_view(), name='auth-clock-in'),
    path('auth/clock-out/', views.ClockOutView.as_view(), name='auth-clock-out'),
    
    # ---- Router Inclusion ----
    path('', include(router.urls)),
]
