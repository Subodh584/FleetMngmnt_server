from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'maintenance-schedules', views.MaintenanceScheduleViewSet, basename='maintenance-schedule')
router.register(r'maintenance-records', views.MaintenanceRecordViewSet, basename='maintenance-record')
router.register(r'spare-parts', views.SparePartViewSet, basename='spare-part')
router.register(r'spare-parts-used', views.SparePartUsedViewSet, basename='spare-part-used')

urlpatterns = [
    path('', include(router.urls)),
]
