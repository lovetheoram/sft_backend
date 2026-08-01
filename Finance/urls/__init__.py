"""
=============================================================================
📦 FINANCE URLS PACKAGE — COMPILES ALL MODULAR ROUTERS & URLPATTERNS
=============================================================================
Combines DRF router routes and explicit path endpoints into a single urlpatterns list.
Guarantees 100% backward compatibility for include('Finance.urls').
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .auth_urls import router as auth_router, urlpatterns as auth_patterns
from .building_urls import router as building_router, urlpatterns as building_patterns
from .finance_urls import router as finance_router, urlpatterns as finance_patterns
from .society_urls import router as society_router, urlpatterns as society_patterns
from .ai_urls import urlpatterns as ai_patterns

# Main DRF Router aggregator
router = DefaultRouter()
router.registry.extend(auth_router.registry)
router.registry.extend(building_router.registry)
router.registry.extend(finance_router.registry)
router.registry.extend(society_router.registry)

urlpatterns = [
    path('', include(router.urls)),
] + auth_patterns + building_patterns + finance_patterns + society_patterns + ai_patterns
