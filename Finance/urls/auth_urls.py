"""
=============================================================================
🔐 AUTH & USER URL ROUTING MODULE
=============================================================================
"""

from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from Finance.views import (
    UserViewSet, MemberViewSet, SignupView, CurrentUserView,
    CurrentMemberView, SuperAdminDetailView, BuildingAdminView
)

router = DefaultRouter()
router.register('users', UserViewSet)
router.register('members', MemberViewSet, basename='members')

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='tokenObtainPair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='tokenRefresh'),
    path('signup/', SignupView.as_view(), name="signup"),
    path('currentUser/', CurrentUserView.as_view(), name="currentUser"),
    path('currentMember/', CurrentMemberView.as_view(), name="currentMember"),
    path('superadmin/', SuperAdminDetailView.as_view(), name='superAdmin'),
    path('buildingadmin/', BuildingAdminView.as_view(), name='buildingAdmin'),
]
