"""
=============================================================================
🏢 BUILDING, FLAT & CATEGORY URL ROUTING MODULE
=============================================================================
"""

from rest_framework.routers import DefaultRouter
from Finance.views import (
    BuildingViewSet, FlatViewSet, CategoryViewSet, SpecialChargeViewSet
)

router = DefaultRouter()
router.register('building', BuildingViewSet)
router.register('flat', FlatViewSet)
router.register('categories', CategoryViewSet, basename='categories')
router.register('category', CategoryViewSet, basename='category')
router.register('specialcharges', SpecialChargeViewSet, basename='specialcharges')

urlpatterns = []
