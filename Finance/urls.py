from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MemberViewSet,IncomeViewSet,ExpenseViewSet,CategoryViewSet
from .views import FinancialSummaryReport
from .views import (
    UserViewSet, MemberViewSet, IncomeViewSet, ExpenseViewSet, CategoryViewSet,
 AnnouncementViewSet, SocietyDocumentViewSet,
    FinancialSummaryReport,ComplainViewSet
)
from .views import SignupView,NotificationViewSet,FlatViewSet,BuildingViewSet,CurrentUserView,SpecialChargeViewSet,CurrentMemberView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import SuperAdminDetailView,BuildingAdminView
from .ai.views import AIChatView
router = DefaultRouter()
router.register('users', UserViewSet)
router.register('members', MemberViewSet,basename='members')
router.register('income', IncomeViewSet,basename='income')
router.register('expense', ExpenseViewSet)
router.register('notifications', NotificationViewSet, basename='notifications')
router.register('categories', CategoryViewSet,basename='categories')
router.register('announcements', AnnouncementViewSet,basename='announcements')
router.register('documents', SocietyDocumentViewSet,basename='documents')
router.register('complaints',ComplainViewSet,basename='complaints')
router.register('building',BuildingViewSet)
router.register('flat',FlatViewSet)
router.register('specialcharges', SpecialChargeViewSet,basename='specialcharges')




urlpatterns=[
    path('',include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='tokenObtainPair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='tokenRefresh'),
    path('financialSummary/',FinancialSummaryReport.as_view()),
    path("signup/", SignupView.as_view(), name="signup"),
    path('currentUser/',CurrentUserView.as_view(),name="currentUser"),
    path('currentMember/',CurrentMemberView.as_view(),name="currentMember"),
    path('superadmin/',SuperAdminDetailView.as_view(),name='superAdmin'),
    path('buildingadmin/',BuildingAdminView.as_view(),name='buildingAdmin'),
    path("ai/chat/", AIChatView.as_view()),





]

