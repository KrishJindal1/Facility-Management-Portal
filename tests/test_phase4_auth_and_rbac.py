"""
Phase 4 Verification Test Suite: Secure Authentication & Role-Based Authorization.

Verifies all 8 Phase 4 evaluation criteria:
1. Normal user authentication
2. Organization authentication
3. Admin authentication
4. Invalid credentials
5. Logout & token revocation
6. Unauthorized role access
7. Category isolation
8. Attempted category manipulation
"""
import unittest
from fastapi.testclient import TestClient
from api.main import app
from database.connection import get_db
from database.models import User, Organization, Category, Requirement
from database.repository import (
    init_database,
    save_requirement_to_db,
    get_requirements_for_organization,
    get_requirements_for_authenticated_user,
    get_user_requirements,
    get_controlled_categories,
    get_all_requirements_for_admin,
)
from services.auth_service import (
    hash_password,
    verify_password,
    validate_password_strength,
    register_user,
    authenticate_user,
    generate_auth_token,
    verify_auth_token,
    revoke_auth_token,
    is_token_revoked,
    login_session,
    logout_session,
    is_authenticated,
    get_current_user,
    is_normal_user,
    is_organization_user,
    is_admin_user,
    require_authenticated,
    require_organization_access,
    require_admin_access,
    normalize_role,
    ROLE_NORMAL_USER,
    ROLE_ORGANIZATION,
    ROLE_ADMIN,
    AuthenticationError,
    UnauthorizedAccessError,
    ForbiddenRoleError,
    CategoryTamperingError,
)


class TestPhase4AuthAndRBAC(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()
        cls.client = TestClient(app)

    def setUp(self):
        with get_db() as db:
            cook_org = db.query(Organization).filter_by(slug="homedesk").first()
            driver_org = db.query(Organization).filter_by(slug="acme").first()
            sec_org = db.query(Organization).filter_by(slug="ironshield").first()

            assert cook_org and driver_org and sec_org, "Seed organizations must exist"

            self.cook_org_id = int(cook_org.id)
            self.driver_org_id = int(driver_org.id)
            self.sec_org_id = int(sec_org.id)

            self.cook_cat_id = int(cook_org.category_id)
            self.driver_cat_id = int(driver_org.category_id)
            self.sec_cat_id = int(sec_org.category_id)

    # -------------------------------------------------------------------------
    # 1. Normal User Authentication
    # -------------------------------------------------------------------------
    def test_01_normal_user_authentication(self):
        """1. Normal user authenticates securely, role is NORMAL_USER, not bound to an org."""
        success, msg, user_data = authenticate_user("user@homedesk.com", "Password123!")
        self.assertTrue(success, f"Authentication failed: {msg}")
        self.assertIsNotNone(user_data)
        self.assertEqual(normalize_role(user_data["role"]), ROLE_NORMAL_USER)
        self.assertIsNone(user_data["organization_id"])
        self.assertIsNone(user_data["category_id"])
        self.assertIn("token", user_data)

        # Verify password is not plaintext in database
        with get_db() as db:
            db_user = db.query(User).filter_by(email="user@homedesk.com").first()
            self.assertNotEqual(db_user.password_hash, "Password123!")
            self.assertTrue(
                db_user.password_hash.startswith("$2b$") or db_user.password_hash.startswith("pbkdf2_sha256$")
            )

        # Verify API login
        res = self.client.post("/api/auth/login", json={
            "email": "user@homedesk.com",
            "password": "Password123!",
        })
        self.assertEqual(res.status_code, 200)
        json_body = res.json()
        self.assertIn("token", json_body)
        self.assertEqual(json_body["user"]["email"], "user@homedesk.com")

    # -------------------------------------------------------------------------
    # 2. Organization Authentication
    # -------------------------------------------------------------------------
    def test_02_organization_authentication(self):
        """2. Cook, Driver, and Security organizations authenticate with their category bound."""
        # Cook Org
        c_ok, c_msg, c_user = authenticate_user("cooks@homedesk.com", "Password123!")
        self.assertTrue(c_ok, f"Cook login failed: {c_msg}")
        self.assertEqual(normalize_role(c_user["role"]), ROLE_ORGANIZATION)
        self.assertEqual(c_user["category_id"], self.cook_cat_id)
        self.assertEqual(c_user["category_name"], "COOK")
        self.assertIsNotNone(c_user["token"])

        # Driver Org
        d_ok, d_msg, d_user = authenticate_user("admin@acme.com", "Password123!")
        self.assertTrue(d_ok, f"Driver login failed: {d_msg}")
        self.assertEqual(normalize_role(d_user["role"]), ROLE_ORGANIZATION)
        self.assertEqual(d_user["category_id"], self.driver_cat_id)
        self.assertEqual(d_user["category_name"], "DRIVER")

        # Security Org
        s_ok, s_msg, s_user = authenticate_user("guards@ironshield.com", "Password123!")
        self.assertTrue(s_ok, f"Security login failed: {s_msg}")
        self.assertEqual(normalize_role(s_user["role"]), ROLE_ORGANIZATION)
        self.assertEqual(s_user["category_id"], self.sec_cat_id)
        self.assertEqual(s_user["category_name"], "SECURITY_GUARD")

        # Token payload verification
        valid, payload, _ = verify_auth_token(c_user["token"])
        self.assertTrue(valid)
        self.assertEqual(payload["role"], ROLE_ORGANIZATION)
        self.assertEqual(payload["category_id"], self.cook_cat_id)

    # -------------------------------------------------------------------------
    # 3. Admin Authentication
    # -------------------------------------------------------------------------
    def test_03_admin_authentication(self):
        """3. Admin authenticates securely with role ADMIN and platform-wide access."""
        ok, msg, admin_user = authenticate_user("admin@homedesk.com", "Password123!")
        self.assertTrue(ok, f"Admin login failed: {msg}")
        self.assertEqual(normalize_role(admin_user["role"]), ROLE_ADMIN)
        self.assertTrue(is_admin_user(admin_user))
        self.assertFalse(is_normal_user(admin_user))

        # Admin can access protected admin area via API
        admin_token = admin_user["token"]
        res = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        overview = res.json()
        self.assertIn("categories", overview)
        self.assertIn("organizations", overview)
        self.assertIn("requirements", overview)
        self.assertEqual(len(overview["categories"]), 3)

    # -------------------------------------------------------------------------
    # 4. Invalid Credentials
    # -------------------------------------------------------------------------
    def test_04_invalid_credentials(self):
        """4. Invalid password, unknown email, and empty credentials are rejected."""
        # Wrong password
        ok1, msg1, user1 = authenticate_user("admin@homedesk.com", "WrongPassword!99")
        self.assertFalse(ok1)
        self.assertIsNone(user1)
        self.assertIn("Invalid email or password", msg1)

        # Unknown email
        ok2, msg2, user2 = authenticate_user("nonexistent_user_999@test.com", "Password123!")
        self.assertFalse(ok2)
        self.assertIsNone(user2)

        # Empty credentials
        ok3, _, _ = authenticate_user("", "Password123!")
        self.assertFalse(ok3)

        # API invalid login returns 401 Unauthorized
        res = self.client.post("/api/auth/login", json={
            "email": "admin@homedesk.com",
            "password": "WrongPassword!99",
        })
        self.assertEqual(res.status_code, 401)

    # -------------------------------------------------------------------------
    # 5. Logout & Token Revocation
    # -------------------------------------------------------------------------
    def test_05_logout_and_token_revocation(self):
        """5. Logout securely clears session state and revokes authentication token."""
        ok, _, user_data = authenticate_user("user@homedesk.com", "Password123!")
        self.assertTrue(ok)
        token = user_data["token"]

        # Token is initially valid
        is_val, payload, _ = verify_auth_token(token)
        self.assertTrue(is_val)

        # Revoke token upon logout
        revoke_auth_token(token)
        self.assertTrue(is_token_revoked(token))

        # Revoked token fails verification
        is_val_after, _, err_msg = verify_auth_token(token)
        self.assertFalse(is_val_after)
        self.assertIn("revoked", err_msg)

        # Calling protected endpoint with revoked token returns 401
        res = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 401)

        # Test API logout endpoint
        _, _, admin_user = authenticate_user("admin@homedesk.com", "Password123!")
        adm_token = admin_user["token"]
        res_logout = self.client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {adm_token}"},
        )
        self.assertEqual(res_logout.status_code, 200)

        # Admin overview now rejects the revoked token
        res_overview = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {adm_token}"},
        )
        self.assertEqual(res_overview.status_code, 401)

    # -------------------------------------------------------------------------
    # 6. Unauthorized Role Access
    # -------------------------------------------------------------------------
    def test_06_unauthorized_role_access(self):
        """6. Normal users cannot access org/admin functionality; Org cannot access admin."""
        _, _, normal_user = authenticate_user("user@homedesk.com", "Password123!")
        _, _, cook_org_user = authenticate_user("cooks@homedesk.com", "Password123!")
        _, _, driver_org_user = authenticate_user("admin@acme.com", "Password123!")

        normal_token = normal_user["token"]
        cook_token = cook_org_user["token"]

        # A. Normal user cannot access organization requirements via service guard
        with self.assertRaises(ForbiddenRoleError):
            require_organization_access(normal_user)

        with self.assertRaises(ForbiddenRoleError):
            get_requirements_for_authenticated_user(normal_user)

        # B. Normal user cannot access admin area
        with self.assertRaises(ForbiddenRoleError):
            require_admin_access(normal_user)

        # C. Organization user cannot access admin area
        with self.assertRaises(ForbiddenRoleError):
            require_admin_access(cook_org_user)

        # D. API: Normal user calling organization endpoint -> 403 Forbidden
        res_norm_org = self.client.get(
            f"/api/organizations/{self.cook_org_id}/requirements",
            headers={"Authorization": f"Bearer {normal_token}"},
        )
        self.assertEqual(res_norm_org.status_code, 403)

        # E. API: Normal user calling admin overview -> 403 Forbidden
        res_norm_admin = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {normal_token}"},
        )
        self.assertEqual(res_norm_admin.status_code, 403)

        # F. API: Organization calling admin overview -> 403 Forbidden
        res_org_admin = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {cook_token}"},
        )
        self.assertEqual(res_org_admin.status_code, 403)

        # G. API: Organization 1 (Cook) calling Organization 2 (Driver) workspace -> 403 Forbidden
        res_cross_org = self.client.get(
            f"/api/organizations/{self.driver_org_id}/requirements",
            headers={"Authorization": f"Bearer {cook_token}"},
        )
        self.assertEqual(res_cross_org.status_code, 403)

        # H. API: Unauthenticated caller calling protected endpoints -> 401 Unauthorized
        res_unauth1 = self.client.get(f"/api/organizations/{self.cook_org_id}/requirements")
        self.assertEqual(res_unauth1.status_code, 401)

        res_unauth2 = self.client.get("/api/admin/overview")
        self.assertEqual(res_unauth2.status_code, 401)

    # -------------------------------------------------------------------------
    # 7. Category Isolation
    # -------------------------------------------------------------------------
    def test_07_category_isolation(self):
        """7. Authenticated organizations only receive requirements matching their PostgreSQL category."""
        # Submit requirements across all 3 categories
        save_requirement_to_db("Cook", {
            "Name": "Phase 4 Cook Customer",
            "Mobile": "9811122233",
            "City": "Mumbai",
            "Budget": 18000,
            "Cuisine Type": "South Indian",
            "Meals Per Day": 3,
        })
        save_requirement_to_db("Driver", {
            "Name": "Phase 4 Driver Customer",
            "Mobile": "9811122244",
            "City": "Pune",
            "Budget": 22000,
            "Vehicle Type": "Manual SUV",
            "License Required": "Yes",
        })
        save_requirement_to_db("Security Guard", {
            "Name": "Phase 4 Security Customer",
            "Mobile": "9811122255",
            "City": "Delhi",
            "Budget": 28000,
            "Day/Night Shift": "Night",
            "Residential/Commercial": "Commercial",
        })

        _, _, cook_user = authenticate_user("cooks@homedesk.com", "Password123!")
        _, _, driver_user = authenticate_user("admin@acme.com", "Password123!")
        _, _, sec_user = authenticate_user("guards@ironshield.com", "Password123!")

        # Cook organization receives ONLY Cook requirements
        cook_reqs = get_requirements_for_authenticated_user(cook_user)
        self.assertGreater(len(cook_reqs), 0)
        for r in cook_reqs:
            self.assertEqual(r["category_id"], self.cook_cat_id)
            self.assertEqual(r["Service Type"], "Cook")

        # Driver organization receives ONLY Driver requirements
        driver_reqs = get_requirements_for_authenticated_user(driver_user)
        self.assertGreater(len(driver_reqs), 0)
        for r in driver_reqs:
            self.assertEqual(r["category_id"], self.driver_cat_id)
            self.assertEqual(r["Service Type"], "Driver")

        # Security organization receives ONLY Security requirements
        sec_reqs = get_requirements_for_authenticated_user(sec_user)
        self.assertGreater(len(sec_reqs), 0)
        for r in sec_reqs:
            self.assertEqual(r["category_id"], self.sec_cat_id)
            self.assertEqual(r["Service Type"], "Security Guard")

    # -------------------------------------------------------------------------
    # 8. Attempted Category Manipulation
    # -------------------------------------------------------------------------
    def test_08_attempted_category_manipulation(self):
        """8. Cross-category manipulation via UI state or query params is strictly intercepted & blocked."""
        _, _, cook_user = authenticate_user("cooks@homedesk.com", "Password123!")
        cook_token = cook_user["token"]

        # A. Python Data-Access Layer: Passing manipulated category to get_requirements_for_authenticated_user raises CategoryTamperingError
        with self.assertRaises(CategoryTamperingError):
            get_requirements_for_authenticated_user(
                cook_user,
                requested_category=self.driver_cat_id,  # Cook trying to request Driver
            )

        with self.assertRaises(CategoryTamperingError):
            get_requirements_for_authenticated_user(
                cook_user,
                requested_category="DRIVER",  # Cook trying to request DRIVER by name
            )

        # B. repository.get_requirements_for_organization intercepts and returns empty list
        tampered_reqs = get_requirements_for_organization(
            self.cook_org_id,
            requested_category=self.driver_cat_id,
        )
        self.assertEqual(tampered_reqs, [])

        # C. API: Attempting to supply conflicting category_id returns 403 Forbidden
        res_tampered_api = self.client.get(
            f"/api/organizations/{self.cook_org_id}/requirements?category_id={self.driver_cat_id}",
            headers={"Authorization": f"Bearer {cook_token}"},
        )
        self.assertEqual(res_tampered_api.status_code, 403)
        self.assertIn("Attempted category manipulation detected", res_tampered_api.json()["detail"])

        # Legitimate query with matching category (or omitted parameter) succeeds
        res_legit_api = self.client.get(
            f"/api/organizations/{self.cook_org_id}/requirements",
            headers={"Authorization": f"Bearer {cook_token}"},
        )
        self.assertEqual(res_legit_api.status_code, 200)
        reqs = res_legit_api.json()
        for r in reqs:
            self.assertEqual(r["category_id"], self.cook_cat_id)


if __name__ == "__main__":
    unittest.main()
