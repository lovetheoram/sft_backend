"""
=============================================================================
📢 SOCIETY MANAGEMENT URL ROUTING MODULE
=============================================================================
"""

from rest_framework.routers import DefaultRouter
from Finance.views import (
    NotificationViewSet, AnnouncementViewSet, SocietyDocumentViewSet, ComplainViewSet
)

router = DefaultRouter()
router.register('notifications', NotificationViewSet, basename='notifications')
router.register('announcements', AnnouncementViewSet, basename='announcements')
router.register('documents', SocietyDocumentViewSet, basename='documents')
router.register('complaints', ComplainViewSet, basename='complaints')

urlpatterns = []
