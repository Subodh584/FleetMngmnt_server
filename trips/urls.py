from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# ==========================================
# REST Framework Router Initialization
# ==========================================
router = DefaultRouter()

# High-level Logistics and Trip Entities
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'order-drop-points', views.OrderDropPointViewSet, basename='order-drop-point')
router.register(r'trips', views.TripViewSet, basename='trip')

# Routing Geometries and Constraints
router.register(r'routes', views.RouteViewSet, basename='route')
router.register(r'route-deviations', views.RouteDeviationViewSet, basename='route-deviation')
router.register(r'geofence-events', views.GeofenceEventViewSet, basename='geofence-event')

# Telemetry and Execution Audits
router.register(r'driver-locations', views.DriverLocationViewSet, basename='driver-location')
router.register(r'gps-logs', views.GpsLogViewSet, basename='gps-log')
router.register(r'delivery-proofs', views.DeliveryProofViewSet, basename='delivery-proof')
router.register(r'odometer-images', views.OdometerImageViewSet, basename='odometer-image')

# Accounting and Financials
router.register(r'trip-expenses', views.TripExpenseViewSet, basename='trip-expense')
router.register(r'fuel-logs', views.FuelLogViewSet, basename='fuel-log')

urlpatterns = [
    # Router Inclusion
    path('', include(router.urls)),
]
