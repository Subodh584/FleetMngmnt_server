from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# ==========================================
# REST Framework Router Initialization
# ==========================================
router = DefaultRouter()

# Operational constraints and future repairs
router.register(r'maintenance-schedules', views.MaintenanceScheduleViewSet, basename='maintenance-schedule')

# Real-time shop execution and completed tasks
router.register(r'maintenance-records', views.MaintenanceRecordViewSet, basename='maintenance-record')

# Explicit decoupled accounting stock
router.register(r'spare-parts', views.SparePartViewSet, basename='spare-part')
router.register(r'spare-parts-used', views.SparePartUsedViewSet, basename='spare-part-used')

urlpatterns = [
    # Router Inclusion
    path('', include(router.urls)),
]
