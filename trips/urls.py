from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'order-drop-points', views.OrderDropPointViewSet, basename='order-drop-point')
router.register(r'trips', views.TripViewSet, basename='trip')
router.register(r'routes', views.RouteViewSet, basename='route')
router.register(r'route-deviations', views.RouteDeviationViewSet, basename='route-deviation')
router.register(r'gps-logs', views.GpsLogViewSet, basename='gps-log')
router.register(r'geofence-events', views.GeofenceEventViewSet, basename='geofence-event')
router.register(r'trip-expenses', views.TripExpenseViewSet, basename='trip-expense')
router.register(r'fuel-logs', views.FuelLogViewSet, basename='fuel-log')
router.register(r'delivery-proofs', views.DeliveryProofViewSet, basename='delivery-proof')

urlpatterns = [
    path('', include(router.urls)),
]
