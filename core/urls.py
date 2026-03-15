from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'locations', views.LocationViewSet, basename='location')
router.register(r'geofences', views.GeofenceViewSet, basename='geofence')

urlpatterns = [
    # JWT auth
    path('auth/register/', views.RegisterView.as_view(), name='auth-register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', views.MeView.as_view(), name='auth-me'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='auth-change-password'),
    path('auth/send-credentials/', views.SendCredentialsEmailView.as_view(), name='auth-send-credentials'),
    # Router URLs
    path('', include(router.urls)),
]
