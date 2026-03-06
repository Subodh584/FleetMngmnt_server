from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'vehicles', views.VehicleViewSet, basename='vehicle')
router.register(r'inspection-checklists', views.InspectionChecklistViewSet, basename='inspection-checklist')
router.register(r'inspection-checklist-items', views.InspectionChecklistItemViewSet, basename='inspection-checklist-item')
router.register(r'inspections', views.InspectionViewSet, basename='inspection')
router.register(r'vehicle-issues', views.VehicleIssueViewSet, basename='vehicle-issue')

urlpatterns = [
    path('', include(router.urls)),
]
