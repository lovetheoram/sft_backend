"""
=============================================================================
📦 FINANCE VIEWS PACKAGE — RE-EXPORTS ALL MODULAR VIEWS & PERMISSIONS
=============================================================================
Guarantees 100% backward compatibility for all existing imports across Django.
"""

from .permissions import (
    is_super_admin, is_building_admin,
    IsSuperAdmin, IsBuildingAdmin, IsAdminOrBuildingAdmin
)

from .auth_views import (
    SignupView, CurrentUserView, CurrentMemberView,
    SuperAdminDetailView, BuildingAdminView,
    UserViewSet, MemberViewSet
)

from .building_views import (
    BuildingViewSet, FlatViewSet, CategoryViewSet, SpecialChargeViewSet
)

from .finance_views import (
    IncomeViewSet, ExpenseViewSet, FinancialSummaryReport, ClearCacheView
)

from .society_views import (
    NotificationViewSet, AnnouncementViewSet,
    SocietyDocumentViewSet, ComplainViewSet, ComplaintCommentViewSet
)
