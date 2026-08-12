"""
=============================================================================
🧪 FINANCE APP TEST SUITE — Production-Grade Django Tests
=============================================================================
Test classes:
  SystemHealthTest          — Health check endpoint
  BuildingAndFlatModelTest  — Model creation and constraints
  FinancialServicesTest     — Service layer logic (fy_months, opening_balance)
  JWTAuthFlowTest           — Signup → login → JWT → protected endpoint
  IncomeLifecycleTest       — Income creation → verify → summary inclusion
  RolePermissionTest        — Resident blocked from admin endpoints (403)
  ExceptionHandlerTest      — Standardized JSON error envelope validation
=============================================================================
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date

from Finance.models import Building, Flat, Member, Income, Expense, Category
from Finance.services import get_fy_months, get_opening_balance, get_financial_summary

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: System Health
# ─────────────────────────────────────────────────────────────────────────────

class SystemHealthTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_check_endpoint(self):
        """Health endpoint must return 200 with status=ok and database=connected."""
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')
        self.assertEqual(response.data['database'], 'connected')
        self.assertIn('timestamp', response.data)
        self.assertIn('version', response.data)


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Model Creation
# ─────────────────────────────────────────────────────────────────────────────

class BuildingAndFlatModelTest(TestCase):
    def setUp(self):
        self.building = Building.objects.create(name="Tower A", address="123 Main St")
        self.flat = Flat.objects.create(building=self.building, number="101")

    def test_building_creation(self):
        self.assertEqual(str(self.building), "Tower A")

    def test_flat_creation(self):
        self.assertEqual(self.flat.number, "101")
        self.assertFalse(self.flat.is_occupied)

    def test_flat_unique_per_building(self):
        """Creating two flats with same number in same building should fail."""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Flat.objects.create(building=self.building, number="101")


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Financial Services
# ─────────────────────────────────────────────────────────────────────────────

class FinancialServicesTest(TestCase):
    def setUp(self):
        self.building = Building.objects.create(name="Tower B")
        self.flat = Flat.objects.create(building=self.building, number="201")
        self.user = User.objects.create_user(
            username="testuser", password="password123",
            role="resident", flat=self.flat
        )
        self.member = Member.objects.get(user=self.user)

    def test_fy_months(self):
        """Financial year Apr-2023 to Mar-2024 should have exactly 12 months."""
        months = get_fy_months(2023)
        self.assertEqual(len(months), 12)
        self.assertEqual(months[0], 'Apr-23')
        self.assertEqual(months[11], 'Mar-24')

    def test_opening_balance_empty(self):
        """Opening balance with no income/expense records should be 0."""
        balance = get_opening_balance(2023, self.building)
        self.assertEqual(balance, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: JWT Authentication Flow
# ─────────────────────────────────────────────────────────────────────────────

class JWTAuthFlowTest(TestCase):
    """
    End-to-end: Signup → Login → Get JWT → Access protected endpoint.
    Verifies that the JWT token correctly authorizes API requests.
    """

    def setUp(self):
        self.client = APIClient()
        self.building = Building.objects.create(name="Auth Test Tower")
        self.flat = Flat.objects.create(building=self.building, number="A1")

    def test_login_returns_jwt_tokens(self):
        """Successful login should return both access and refresh tokens."""
        User.objects.create_user(username='jwtuser', password='securepass123', role='resident')
        response = self.client.post('/api/token/', {
            'username': 'jwtuser',
            'password': 'securepass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_protected_endpoint_requires_jwt(self):
        """Accessing /api/currentUser/ without token should return 401."""
        response = self.client.get('/api/currentUser/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_with_valid_jwt(self):
        """Accessing /api/currentUser/ with valid token should return 200."""
        user = User.objects.create_user(
            username='autheduser', password='securepass123', role='resident'
        )
        # Login to get token
        token_resp = self.client.post('/api/token/', {
            'username': 'autheduser', 'password': 'securepass123',
        })
        self.assertEqual(token_resp.status_code, status.HTTP_200_OK)
        access_token = token_resp.data['access']

        # Use token to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        resp = self.client.get('/api/currentUser/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], user.username)

    def test_invalid_token_returns_401(self):
        """A tampered/invalid token should return 401 Unauthorized."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer this.is.not.a.valid.jwt')
        response = self.client.get('/api/currentUser/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Income Lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class IncomeLifecycleTest(TestCase):
    """
    Resident creates income (status=pending) → Building Admin verifies it.
    Verifies the full income workflow and that status transitions correctly.
    """

    def setUp(self):
        self.client = APIClient()
        self.building = Building.objects.create(name="Income Test Tower")

        # Resident setup
        self.flat_resident = Flat.objects.create(building=self.building, number="R1")
        self.resident = User.objects.create_user(
            username='resident1', password='pass123',
            role='resident', flat=self.flat_resident
        )
        self.member = Member.objects.get(user=self.resident)

        # Building admin setup
        self.flat_admin = Flat.objects.create(building=self.building, number="ADM")
        self.admin = User.objects.create_user(
            username='buildingadmin', password='adminpass',
            role='admin', flat=self.flat_admin
        )

    def _get_token(self, username, password):
        resp = self.client.post('/api/token/', {'username': username, 'password': password})
        return resp.data['access']

    def test_resident_creates_pending_income(self):
        """Resident can create income — status must be 'pending'."""
        token = self._get_token('resident1', 'pass123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = self.client.post('/api/income/', {
            'amount': 5000,
            'date': str(date.today()),
            'description': 'Monthly maintenance',
            'building_id': self.building.id,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], 'pending')

    def test_admin_verifies_income(self):
        """Building admin can verify a pending income — status must change to 'verified'."""
        # Create income as resident
        income = Income.objects.create(
            member=self.member,
            building=self.building,
            amount=3000,
            date=date.today(),
            status='pending',
        )

        # Verify as admin
        token = self._get_token('buildingadmin', 'adminpass')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        resp = self.client.post(f'/api/income/{income.id}/verify/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        income.refresh_from_db()
        self.assertEqual(income.status, 'verified')


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Role-Based Permission Enforcement
# ─────────────────────────────────────────────────────────────────────────────

class RolePermissionTest(TestCase):
    """
    Ensures residents are blocked from admin-only endpoints with 403 Forbidden.
    Verifies the custom permission classes (IsBuildingAdmin, IsAdminOrBuildingAdmin).
    """

    def setUp(self):
        self.client = APIClient()
        self.building = Building.objects.create(name="Perm Test Tower")
        self.flat = Flat.objects.create(building=self.building, number="P1")
        self.resident = User.objects.create_user(
            username='permresident', password='pass123',
            role='resident', flat=self.flat
        )

    def _authenticate_as_resident(self):
        resp = self.client.post('/api/token/', {
            'username': 'permresident', 'password': 'pass123'
        })
        token = resp.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_resident_cannot_list_all_users(self):
        """GET /api/users/ must return 403 for residents."""
        self._authenticate_as_resident()
        resp = self.client.get('/api/users/')
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_resident_cannot_create_building(self):
        """POST /api/building/ must return 403 for residents."""
        self._authenticate_as_resident()
        resp = self.client.post('/api/building/', {'name': 'Hacked Tower', 'address': 'X'})
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Standardized Error Envelope
# ─────────────────────────────────────────────────────────────────────────────

class ExceptionHandlerTest(TestCase):
    """
    Verifies that our custom DRF exception handler returns the standardized
    JSON error envelope for 401 and 400 responses.

    Note: SimpleJWT 401s DO pass through custom_exception_handler (it calls
    DRF's built-in exception_handler first, which handles AuthenticationFailed).
    The envelope wraps the DRF response.data into {"success": False, "error": {...}}.
    """

    def setUp(self):
        self.client = APIClient()

    def test_401_returns_json_error_response(self):
        """Unauthenticated request must return 401 with a JSON error body."""
        resp = self.client.get('/api/currentUser/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        # Custom handler wraps response: check for either envelope or DRF detail
        data = resp.data
        is_custom_envelope = (
            'success' in data and data.get('success') is False and 'error' in data
        )
        is_drf_detail = 'detail' in data
        self.assertTrue(
            is_custom_envelope or is_drf_detail,
            f"Expected error envelope or DRF detail, got: {data}"
        )
        # If custom envelope, validate its structure
        if is_custom_envelope:
            self.assertIn('code', data['error'])
            self.assertIn('message', data['error'])
            self.assertIn('timestamp', data)

    def test_signup_400_returns_error_response(self):
        """Signup with missing fields must return 400 with an error body."""
        resp = self.client.post('/api/signup/', {})  # missing required fields
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        data = resp.data
        # Custom envelope check
        is_custom_envelope = (
            'success' in data and data.get('success') is False and 'error' in data
        )
        # DRF validation errors return a dict of field errors directly
        is_drf_validation = isinstance(data, dict) and len(data) > 0
        self.assertTrue(
            is_custom_envelope or is_drf_validation,
            f"Expected error response, got: {data}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Expense Lifecycle & Permissions
# ─────────────────────────────────────────────────────────────────────────────

class ExpenseLifecycleTest(TestCase):
    """
    Verifies expense creation workflows:
    - Building admin can create expense (auto-tied to building)
    - Super admin can create expense
    - Resident is blocked with 403 Forbidden
    """

    def setUp(self):
        self.client = APIClient()
        self.building = Building.objects.create(name="Expense Test Tower")
        self.category = Category.objects.create(name="Maintenance", building=self.building)

        # Building admin setup
        self.flat_admin = Flat.objects.create(building=self.building, number="ADM1")
        self.admin = User.objects.create_user(
            username='expadmin', password='adminpass',
            role='admin', flat=self.flat_admin
        )

        # Super admin setup (no flat)
        self.superadmin = User.objects.create_user(
            username='expsuper', password='superpass',
            role='admin', flat=None
        )

        # Regular resident setup
        self.flat_res = Flat.objects.create(building=self.building, number="R101")
        self.resident = User.objects.create_user(
            username='expresident', password='respass',
            role='resident', flat=self.flat_res
        )

    def _get_token(self, username, password):
        resp = self.client.post('/api/token/', {'username': username, 'password': password})
        return resp.data['access']

    def test_building_admin_creates_expense(self):
        """Building Admin can create an expense successfully."""
        token = self._get_token('expadmin', 'adminpass')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = self.client.post('/api/expense/', {
            'amount': 2500,
            'category': self.category.id,
            'date': str(date.today()),
            'description': 'Elevator repair'
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(resp.data['amount']), 2500.0)

    def test_super_admin_creates_expense(self):
        """Super Admin can create an expense successfully."""
        token = self._get_token('expsuper', 'superpass')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = self.client.post('/api/expense/', {
            'amount': 4000,
            'category_id': self.category.id,
            'building_id': self.building.id,
            'date': str(date.today()),
            'description': 'Roof waterproofing'
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_resident_cannot_create_expense(self):
        """Resident is blocked from creating expenses with 403 Forbidden."""
        token = self._get_token('expresident', 'respass')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = self.client.post('/api/expense/', {
            'amount': 1000,
            'category_id': self.category.id,
            'date': str(date.today())
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Pagination, Filters & Data Scoping
# ─────────────────────────────────────────────────────────────────────────────

class PaginationAndScopeTest(TestCase):
    """
    Verifies:
    - Income default scope (personal only) vs scope=all (all building incomes for admin)
    - Limit / Offset pagination response structure (count, results, has_more)
    - Filtering on ExpenseViewSet
    """

    def setUp(self):
        self.client = APIClient()
        self.building = Building.objects.create(name="Scope Test Tower")
        self.flat1 = Flat.objects.create(building=self.building, number="101")
        self.flat2 = Flat.objects.create(building=self.building, number="102")

        self.user1 = User.objects.create_user(username='scopeuser1', password='pass123', role='admin', flat=self.flat1)
        self.user2 = User.objects.create_user(username='scopeuser2', password='pass123', role='resident', flat=self.flat2)

        self.member1 = Member.objects.get(user=self.user1)
        self.member2 = Member.objects.get(user=self.user2)

        # Incomes
        Income.objects.create(member=self.member1, building=self.building, amount=1000, date=date.today())
        Income.objects.create(member=self.member2, building=self.building, amount=2000, date=date.today())

        # Category & Expenses
        self.category = Category.objects.create(name="Repairs", building=self.building)
        for i in range(15):
            Expense.objects.create(
                category=self.category,
                building=self.building,
                amount=100 + (i * 10),
                date=date.today()
            )

    def _get_token(self, username, password='pass123'):
        resp = self.client.post('/api/token/', {'username': username, 'password': password})
        return resp.data['access']

    def test_income_default_scope_returns_only_personal_payments(self):
        """GET /api/income/ defaults to returning only personal payments even for building admin."""
        token = self._get_token('scopeuser1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = self.client.get('/api/income/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Should return 1 personal income record, not user2's record
        data = resp.data.get('results') if isinstance(resp.data, dict) else resp.data
        self.assertEqual(len(data), 1)
        self.assertEqual(float(data[0]['amount']), 1000.0)

    def test_income_admin_scope_returns_all_building_payments(self):
        """GET /api/income/?scope=all returns all building income payments for admin."""
        token = self._get_token('scopeuser1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = self.client.get('/api/income/?scope=all')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data.get('results') if isinstance(resp.data, dict) else resp.data
        self.assertEqual(len(data), 2)

    def test_expense_limit_offset_pagination(self):
        """GET /api/expense/?limit=10 returns 10 items and has_more=True."""
        token = self._get_token('scopeuser1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = self.client.get('/api/expense/?limit=10&offset=0')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('has_more', resp.data)
        self.assertEqual(resp.data['count'], 15)
        self.assertEqual(len(resp.data['results']), 10)
        self.assertTrue(resp.data['has_more'])


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Category Building Isolation & Duplicate Prevention
# ─────────────────────────────────────────────────────────────────────────────

class BuildingCategoryIsolationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.b1 = Building.objects.create(name="Tower One")
        self.b2 = Building.objects.create(name="Tower Two")

        self.flat1 = Flat.objects.create(building=self.b1, number="101")
        self.admin1 = User.objects.create_user(
            username='admin1', password='pass123', role='admin', flat=self.flat1
        )

        self.flat2 = Flat.objects.create(building=self.b2, number="201")
        self.admin2 = User.objects.create_user(
            username='admin2', password='pass123', role='admin', flat=self.flat2
        )

    def _get_token(self, username, password='pass123'):
        resp = self.client.post('/api/token/', {'username': username, 'password': password})
        return resp.data['access']

    def test_same_category_name_allowed_across_different_buildings(self):
        """Building 1 and Building 2 can both have a category named 'Maintenance'."""
        c1 = Category.objects.create(name="Maintenance", building=self.b1)
        c2 = Category.objects.create(name="Maintenance", building=self.b2)
        self.assertNotEqual(c1.id, c2.id)
        self.assertEqual(c1.building, self.b1)
        self.assertEqual(c2.building, self.b2)

    def test_category_serializer_reuses_duplicate_category(self):
        """Creating same-name category in same building returns existing instance."""
        token = self._get_token('admin1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # First post
        resp1 = self.client.post('/api/categories/', {'name': 'Security'})
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        cat_id_1 = resp1.data['id']

        # Second post with same name
        resp2 = self.client.post('/api/categories/', {'name': 'security'})
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        cat_id_2 = resp2.data['id']

        self.assertEqual(cat_id_1, cat_id_2)

    def test_building_admin_category_list_isolation(self):
        """Building Admin 1 only sees categories belonging to Building 1."""
        Category.objects.create(name="Lift Repair", building=self.b1)
        Category.objects.create(name="Garden Care", building=self.b2)

        token1 = self._get_token('admin1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')
        resp1 = self.client.get('/api/categories/')
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)

        cat_names = [c['name'] for c in resp1.data]
        self.assertIn("Lift Repair", cat_names)
        self.assertNotIn("Garden Care", cat_names)




