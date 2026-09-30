"""
Automated Authentication & Multi-Tenant Security Test Suite.
Verifies Phase 4 requirements:
1. User registration (existing and new organizations).
2. User login with valid credentials.
3. Login failure on invalid credentials.
4. Secure password hashing (passwords never stored in plaintext).
5. Protection against credential exposure (never displayed or logged).
6. Authenticated user organization determines tenant context.
7. Manual tenant_id hijacking is strictly prevented.
8. Logout session clearing.
9. Cross-tenant isolation between users of different organizations.
"""
import unittest
from database.connection import get_db
from database.models import Organization, User, Lead
from services.auth_service import (
    hash_password,
    verify_password,
    register_user,
    authenticate_user,
    validate_password_strength,
)
from database.repository import (
    save_lead_to_db,
    get_latest_lead_by_mobile,
    get_lead_by_id,
    get_all_leads_for_export,
    init_database,
)
from storage.excel_handler import get_excel_export_bytes
from openpyxl import load_workbook
import io


class TestAuthenticationAndSecurity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        with get_db() as db:
            org1 = db.query(Organization).filter_by(slug="homedesk").first()
            org2 = db.query(Organization).filter_by(slug="acme").first()
            assert org1 is not None, "Seeded tenant 1 (homedesk) must exist"
            assert org2 is not None, "Seeded tenant 2 (acme) must exist"
            self.org1_id = int(org1.id)
            self.org2_id = int(org2.id)

    def test_01_password_hashing_security(self):
        """Requirements 3 & 4: Passwords must use secure hashing and never be stored in plaintext."""
        raw_password = "SuperSecretPassword123!"
        hashed = hash_password(raw_password)

        self.assertNotEqual(hashed, raw_password, "Password was not hashed!")
        self.assertTrue(
            hashed.startswith("$2b$") or hashed.startswith("pbkdf2_sha256$"),
            f"Unexpected hash format: {hashed}",
        )
        # Verify correct password succeeds
        self.assertTrue(verify_password(raw_password, hashed))
        # Verify incorrect password fails
        self.assertFalse(verify_password("WrongPassword123!", hashed))
        self.assertFalse(verify_password("", hashed))

    def test_02_user_registration(self):
        """Requirements 1 & 2: Users should be able to register and belong to an organization."""
        email = "newstaff@homedesk.com"
        # Ensure clean state if previously run
        with get_db() as db:
            old = db.query(User).filter_by(email=email).first()
            if old:
                db.delete(old)

        success, msg, user_data = register_user(
            name="New Staff Member",
            email=email,
            mobile="9811122233",
            password="StrongPassword2026!",
            organization_id=self.org1_id,
        )
        self.assertTrue(success, f"Registration failed: {msg}")
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data["email"], email)
        self.assertEqual(user_data["organization_id"], self.org1_id)

        # Check DB record
        with get_db() as db:
            user_db = db.query(User).filter_by(email=email).first()
            self.assertIsNotNone(user_db)
            self.assertNotEqual(user_db.password_hash, "StrongPassword2026!")
            self.assertTrue(verify_password("StrongPassword2026!", user_db.password_hash))

    def test_03_registration_validation_and_failures(self):
        """Validates password rules, invalid emails, and duplicate account rejection."""
        # Weak password (< 8 chars)
        is_strong, msg = validate_password_strength("weak")
        self.assertFalse(is_strong)

        # Weak password (no digits)
        is_strong, msg = validate_password_strength("allletterslong")
        self.assertFalse(is_strong)

        # Duplicate email
        success, msg, _ = register_user(
            name="Duplicate Test",
            email="admin@homedesk.com",  # Already exists
            mobile="9900000000",
            password="Password123!",
            organization_id=self.org1_id,
        )
        self.assertFalse(success)
        self.assertIn("already exists", msg)

        # Non-existent organization
        success, msg, _ = register_user(
            name="Ghost Org User",
            email="ghost@ghostcorp.com",
            mobile="9911111111",
            password="Password123!",
            organization_id=999999,
        )
        self.assertFalse(success)
        self.assertIn("does not exist", msg)

    def test_04_registration_with_new_organization(self):
        """User can create and register under a new organization."""
        org_name = "Zenith Facility Partners"
        user_email = "owner@zenithfacilities.com"

        with get_db() as db:
            old_user = db.query(User).filter_by(email=user_email).first()
            if old_user:
                db.delete(old_user)
            old_org = db.query(Organization).filter_by(organization_name=org_name).first()
            if old_org:
                db.delete(old_org)

        success, msg, user_data = register_user(
            name="Zenith Founder",
            email=user_email,
            mobile="9876543219",
            password="SecurePassword2026!",
            new_org_name=org_name,
            category_name="Cook",
        )
        self.assertTrue(success, f"Registration with new org failed: {msg}")
        self.assertEqual(user_data["organization_name"], org_name)
        self.assertTrue(user_data["organization_id"] > 0)

    def test_05_login_success(self):
        """Requirement 1: Seeded users can successfully log in."""
        # Tenant 1 Login
        success1, msg1, user1 = authenticate_user("admin@homedesk.com", "Password123!")
        self.assertTrue(success1, f"Tenant 1 login failed: {msg1}")
        self.assertEqual(user1["organization_id"], self.org1_id)
        self.assertEqual(user1["organization_name"], "HomeDesk Primary")

        # Tenant 2 Login
        success2, msg2, user2 = authenticate_user("admin@acme.com", "Password123!")
        self.assertTrue(success2, f"Tenant 2 login failed: {msg2}")
        self.assertEqual(user2["organization_id"], self.org2_id)
        self.assertEqual(user2["organization_name"], "Acme Facilities Group")

    def test_06_login_invalid_credentials(self):
        """Requirement 1 & 5: Invalid credentials must be securely rejected."""
        # Wrong password
        success, msg, user = authenticate_user("admin@homedesk.com", "WrongPassword!")
        self.assertFalse(success)
        self.assertIsNone(user)
        self.assertEqual(msg, "Invalid email or password.")

        # Non-existent email
        success, msg, user = authenticate_user("nonexistent@domain.com", "Password123!")
        self.assertFalse(success)
        self.assertIsNone(user)
        self.assertEqual(msg, "Invalid email or password.")

    def test_07_sensitive_credentials_not_exposed(self):
        """Requirements 3 & 4: Sensitive credentials are never displayed, exposed in dicts or __repr__."""
        with get_db() as db:
            user = db.query(User).filter_by(email="admin@homedesk.com").first()
            user_repr = repr(user)
            self.assertNotIn("Password123!", user_repr)
            self.assertNotIn(user.password_hash, user_repr)

        _, _, user_dict = authenticate_user("admin@homedesk.com", "Password123!")
        self.assertNotIn("password", user_dict)
        self.assertNotIn("password_hash", user_dict)

    def test_08_authenticated_tenant_isolation_enforcement(self):
        """Requirements 7 & 8: Authenticated user organization strictly dictates tenant context."""
        # User 1 belongs to HomeDesk (Tenant 1)
        _, _, user_a = authenticate_user("admin@homedesk.com", "Password123!")
        # User 2 belongs to Acme (Tenant 2)
        _, _, user_b = authenticate_user("admin@acme.com", "Password123!")

        # User A creates a lead in Org 1
        lead_data_a = {
            "Name": "Org A Client Auth Test",
            "Mobile Number": "9998887771",
            "City": "Mumbai",
            "Budget": 25000,
            "Cuisine Type": "Continental",
            "Meals Per Day": 2,
            "user_id": user_a["id"],
        }
        saved_a = save_lead_to_db("Cook", lead_data_a, organization_id=user_a["organization_id"])
        lead_id_a = saved_a["Lead ID"]

        # When queried with User A's organization_id -> lead is found
        found_a = get_lead_by_id(lead_id_a, organization_id=user_a["organization_id"])
        self.assertIsNotNone(found_a)
        self.assertEqual(found_a["Name"], "Org A Client Auth Test")

        # When User B (Org 2) attempts to query User A's lead by ID -> MUST BE NONE
        found_b_by_id = get_lead_by_id(lead_id_a, organization_id=user_b["organization_id"])
        self.assertIsNone(
            found_b_by_id,
            "Cross-tenant security breach: User B accessed User A's lead by Lead ID!",
        )

        # When User B attempts to query User A's lead by Mobile -> MUST BE NONE
        found_b_by_mobile = get_latest_lead_by_mobile("9998887771", organization_id=user_b["organization_id"])
        self.assertIsNone(
            found_b_by_mobile,
            "Cross-tenant security breach: User B accessed User A's lead by mobile lookup!",
        )

        # User B Excel export does NOT contain User A's lead
        excel_bytes = get_excel_export_bytes(organization_id=user_b["organization_id"])
        wb = load_workbook(io.BytesIO(excel_bytes), data_only=True)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row and len(row) > 0 and row[0]:
                    self.assertNotEqual(
                        row[0],
                        lead_id_a,
                        f"Lead {lead_id_a} from Org A leaked into Org B's export sheet {sheet_name}!",
                    )

    def test_09_logout_session_lifecycle(self):
        """Requirement 9: Add and verify logout functionality."""
        from services.auth_service import login_session, logout_session, is_authenticated

        sample_user = {
            "id": 99,
            "name": "Logout Tester",
            "email": "logout@test.com",
            "organization_id": self.org1_id,
            "organization_name": "HomeDesk Primary",
            "organization_slug": "homedesk",
        }
        login_session(sample_user)
        self.assertTrue(is_authenticated(), "User should be authenticated after login_session")

        logout_session()
        self.assertFalse(is_authenticated(), "User should NOT be authenticated after logout_session")

    def test_10_tenant_tampering_blocked_for_authenticated_users(self):
        """Requirement 8: Users must not be able to manually change tenant_id to access another organization."""
        from services.auth_service import login_session, logout_session
        from services.tenant_service import get_current_tenant, set_current_tenant

        # Log in as User bound to Org 1 (homedesk)
        user_org1 = {
            "id": 1,
            "name": "HomeDesk User",
            "email": "admin@homedesk.com",
            "organization_id": self.org1_id,
            "organization_name": "HomeDesk Primary",
            "organization_slug": "homedesk",
        }
        login_session(user_org1)

        # Confirm active tenant is Org 1
        curr = get_current_tenant()
        self.assertEqual(curr["id"], self.org1_id)

        # Attempt to maliciously switch to Org 2 (acme)
        result = set_current_tenant(self.org2_id)
        # Must be rejected and locked to Org 1
        self.assertEqual(
            result["id"],
            self.org1_id,
            "Security vulnerability: Authenticated user was able to switch active tenant!",
        )

        active = get_current_tenant()
        self.assertEqual(active["id"], self.org1_id, "Tenant context leaked away from authenticated organization!")

        logout_session()


if __name__ == "__main__":
    unittest.main(verbosity=2)

