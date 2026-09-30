"""
Comprehensive Automated Test Suite for Phase 8: Cloud Platform Verification.

Exercises all 17 platform requirements with real business logic:
 1. Category validation
 2. Cook requirement creation
 3. Driver requirement creation
 4. Security requirement creation
 5. Requirement persistence
 6. Requirement lookup
 7. Organization registration
 8. Organization category assignment
 9. Cook organization sees only Cook requirements
10. Driver organization sees only Driver requirements
11. Security organization sees only Security requirements
12. Normal users cannot access organization data
13. Organizations cannot access other categories
14. Admin can access platform-wide data
15. Invalid authentication
16. Password handling
17. AI configuration and error handling

Uses an isolated test database to guarantee production data is never modified.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from database.connection import configure_test_database, reset_database_to_default, get_db
from database.models import Requirement, Category, Organization, User
from database.repository import (
    init_database,
    get_controlled_categories,
    resolve_controlled_category,
    normalize_category_name,
    save_requirement_to_db,
    get_lead_by_id,
    get_requirements_for_organization,
    get_all_requirements_for_admin,
    update_requirement_status,
)
from services.auth_service import (
    register_user,
    authenticate_user,
    hash_password,
    verify_password,
    verify_auth_token,
    validate_password_strength,
    is_organization_user,
    is_admin_user,
    ROLE_NORMAL_USER,
    ROLE_ORGANIZATION,
    ROLE_ADMIN,
)
from services.lead_lookup import find_lead_by_mobile
from storage.excel_handler import save_lead
from storage.serial_generator import generate_serial
from ai.providers.cloud_provider import CloudAIProvider
from ai.providers.ollama_provider import OllamaProvider


class TestPhase8ComprehensivePlatformSuite(unittest.TestCase):
    """Reliable automated test suite for cloud platform verification."""

    @classmethod
    def setUpClass(cls):
        # 1. Configure isolated test database fixture
        test_db_path = Path(__file__).resolve().parent.parent / "data" / "test_phase8_isolated.db"
        if test_db_path.exists():
            try:
                test_db_path.unlink()
            except Exception:
                pass

        cls.test_db_url = f"sqlite:///{test_db_path.resolve()}"
        configure_test_database(cls.test_db_url)

        # 2. Initialize database schema & seeds in the isolated database
        init_database()

        # 3. Initialize FastAPI test client
        cls.client = TestClient(app)

        # 4. Seed unique test users for RBAC testing
        # Admin User (seeded during init_database)
        _, _, admin_auth = authenticate_user("admin@homedesk.com", "Password123!")
        cls.admin_token = admin_auth["token"]
        cls.admin_user = admin_auth

        # Cook Organization & User
        _, _, cls.cook_user = register_user(
            name="Chef Admin",
            email="chef@cookorg.test",
            mobile="9899000002",
            password="Password123!",
            new_org_name="Delightful Chefs Org",
            category_name="Cook",
            role=ROLE_ORGANIZATION,
        )
        cls.cook_org_id = cls.cook_user["organization_id"]
        _, _, cook_auth = authenticate_user("chef@cookorg.test", "Password123!")
        cls.cook_token = cook_auth["token"]

        # Driver Organization & User
        _, _, cls.driver_user = register_user(
            name="Fleet Admin",
            email="fleet@driverorg.test",
            mobile="9899000003",
            password="Password123!",
            new_org_name="Express Chauffeurs Org",
            category_name="Driver",
            role=ROLE_ORGANIZATION,
        )
        cls.driver_org_id = cls.driver_user["organization_id"]
        _, _, driver_auth = authenticate_user("fleet@driverorg.test", "Password123!")
        cls.driver_token = driver_auth["token"]

        # Security Organization & User
        _, _, cls.sec_user = register_user(
            name="Shield Admin",
            email="shield@secorg.test",
            mobile="9899000004",
            password="Password123!",
            new_org_name="Apex Guardians Org",
            category_name="Security Guard",
            role=ROLE_ORGANIZATION,
        )
        cls.sec_org_id = cls.sec_user["organization_id"]
        _, _, sec_auth = authenticate_user("shield@secorg.test", "Password123!")
        cls.sec_token = sec_auth["token"]

        # Normal User
        _, _, cls.normal_user = register_user(
            name="Naveen Customer",
            email="naveen@customer.test",
            mobile="9899000005",
            password="Password123!",
            role=ROLE_NORMAL_USER,
        )
        _, _, normal_auth = authenticate_user("naveen@customer.test", "Password123!")
        cls.normal_token = normal_auth["token"]

    @classmethod
    def tearDownClass(cls):
        # Restore default database connection
        reset_database_to_default()
        test_db_path = Path(__file__).resolve().parent.parent / "data" / "test_phase8_isolated.db"
        if test_db_path.exists():
            try:
                test_db_path.unlink()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 1. Category validation
    # -------------------------------------------------------------------------
    def test_01_category_validation(self):
        """Controlled categories are strictly validated; arbitrary categories rejected."""
        controlled = get_controlled_categories()
        names = [c["name"] for c in controlled]
        self.assertEqual(set(names), {"COOK", "DRIVER", "SECURITY_GUARD"})

        # Valid resolutions
        self.assertEqual(resolve_controlled_category("Cook").name, "COOK")
        self.assertEqual(resolve_controlled_category("DRIVER").name, "DRIVER")
        self.assertEqual(resolve_controlled_category("Security Guard").name, "SECURITY_GUARD")

        # Invalid/unauthorized category resolution returns None
        self.assertIsNone(resolve_controlled_category("Plumber"))
        self.assertIsNone(resolve_controlled_category("Electrician"))
        self.assertIsNone(resolve_controlled_category(""))

        # Normalization mappings
        self.assertEqual(normalize_category_name("Cook"), "COOK")
        self.assertEqual(normalize_category_name("Driver"), "DRIVER")
        self.assertEqual(normalize_category_name("Security Guard"), "SECURITY_GUARD")

    # -------------------------------------------------------------------------
    # 2. Cook requirement creation
    # -------------------------------------------------------------------------
    def test_02_cook_requirement_creation(self):
        """Creates a Cook requirement with child attributes (cuisine, meals per day)."""
        lead_id = generate_serial("Cook")
        self.assertTrue(lead_id.startswith("Cook-"))

        cook_payload = {
            "Lead ID": lead_id,
            "Name": "Sunita Rao",
            "Mobile": "9899110001",
            "City": "Mumbai",
            "Address": "Andheri East",
            "Budget": 18000,
            "Cuisine Type": "South Indian, Continental",
            "Meals Per Day": 2,
            "Status": "New",
        }
        saved = save_lead("Cook", cook_payload)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["Lead ID"], lead_id)
        self.assertEqual(saved["Service Type"], "Cook")
        self.assertEqual(saved["category_id"], 1)

    # -------------------------------------------------------------------------
    # 3. Driver requirement creation
    # -------------------------------------------------------------------------
    def test_03_driver_requirement_creation(self):
        """Creates a Driver requirement with child attributes (vehicle type, license)."""
        lead_id = generate_serial("Driver")
        self.assertTrue(lead_id.startswith("Driver-"))

        driver_payload = {
            "Lead ID": lead_id,
            "Name": "Vikram Patel",
            "Mobile": "9899110002",
            "City": "Pune",
            "Address": "Koregaon Park",
            "Budget": 22000,
            "Vehicle Type": "Automatic Sedan",
            "License Required": "Commercial LMV",
            "Status": "New",
        }
        saved = save_lead("Driver", driver_payload)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["Lead ID"], lead_id)
        self.assertEqual(saved["Service Type"], "Driver")
        self.assertEqual(saved["category_id"], 2)

    # -------------------------------------------------------------------------
    # 4. Security requirement creation
    # -------------------------------------------------------------------------
    def test_04_security_requirement_creation(self):
        """Creates a Security Guard requirement with child attributes (shift, site type)."""
        lead_id = generate_serial("Security Guard")
        self.assertTrue(lead_id.startswith("Security-"))

        guard_payload = {
            "Lead ID": lead_id,
            "Name": "Deepak Verma",
            "Mobile": "9899110003",
            "City": "Delhi",
            "Address": "Saket",
            "Budget": 26000,
            "Day/Night Shift": "Night Shift (8 PM - 8 AM)",
            "Residential/Commercial": "Commercial Office",
            "Status": "New",
        }
        saved = save_lead("Security Guard", guard_payload)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["Lead ID"], lead_id)
        self.assertEqual(saved["Service Type"], "Security Guard")
        self.assertEqual(saved["category_id"], 3)

    # -------------------------------------------------------------------------
    # 5. Requirement persistence
    # -------------------------------------------------------------------------
    def test_05_requirement_persistence_in_database(self):
        """Persists records in relational schema with category and service child rows."""
        lead_id = generate_serial("Cook")
        save_lead("Cook", {
            "Lead ID": lead_id,
            "Name": "Persistence Tester",
            "Mobile": "9899110004",
            "City": "Bengaluru",
            "Budget": 19500,
            "Cuisine Type": "North Indian",
            "Meals Per Day": 3,
        })

        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=lead_id).first()
            self.assertIsNotNone(req)
            self.assertEqual(req.name, "Persistence Tester")
            self.assertEqual(req.city, "Bengaluru")
            self.assertEqual(req.budget, 19500.0)
            self.assertEqual(req.category.name, "COOK")

            # Verify relational child table
            self.assertIsNotNone(req.cook_requirement)
            self.assertEqual(req.cook_requirement.cuisine_type, "North Indian")
            self.assertEqual(req.cook_requirement.meals_per_day, 3)

    # -------------------------------------------------------------------------
    # 6. Requirement lookup
    # -------------------------------------------------------------------------
    def test_06_requirement_lookup_by_mobile_and_lead_id(self):
        """Lookups by mobile number and by Lead ID retrieve accurate records."""
        mobile = "9899110005"
        lead_id = generate_serial("Driver")
        save_lead("Driver", {
            "Lead ID": lead_id,
            "Name": "Lookup Tester",
            "Mobile": mobile,
            "City": "Chennai",
            "Budget": 20000,
            "Vehicle Type": "Hatchback",
            "License Required": "Valid LMV",
        })

        # Lookup by mobile
        found_by_mobile = find_lead_by_mobile(mobile)
        self.assertIsNotNone(found_by_mobile)
        self.assertEqual(found_by_mobile["Lead ID"], lead_id)
        self.assertEqual(found_by_mobile["Name"], "Lookup Tester")

        # Lookup by Lead ID
        found_by_id = get_lead_by_id(lead_id)
        self.assertIsNotNone(found_by_id)
        self.assertEqual(found_by_id["Mobile"], mobile)
        self.assertEqual(found_by_id["Service Type"], "Driver")

        # Non-existent lookup
        self.assertIsNone(find_lead_by_mobile("0000000000"))
        self.assertIsNone(get_lead_by_id("NonExistent-999"))

    # -------------------------------------------------------------------------
    # 7. Organization registration
    # -------------------------------------------------------------------------
    def test_07_organization_registration(self):
        """New service provider organization can register and receives active status."""
        ok, msg, user_data = register_user(
            name="New Org Manager",
            email="manager@neworg.test",
            mobile="9899110006",
            password="Password123!",
            new_org_name="Silverline Facilities",
            category_name="Cook",
            role=ROLE_ORGANIZATION,
        )
        self.assertTrue(ok)
        self.assertIsNotNone(user_data["organization_id"])
        self.assertEqual(user_data["role"], "organization")

        with get_db() as db:
            org = db.query(Organization).filter_by(id=user_data["organization_id"]).first()
            self.assertIsNotNone(org)
            self.assertEqual(org.organization_name, "Silverline Facilities")
            self.assertEqual(org.status, "active")

    # -------------------------------------------------------------------------
    # 8. Organization category assignment
    # -------------------------------------------------------------------------
    def test_08_organization_category_assignment(self):
        """Organization registration enforces single controlled category assignment."""
        with get_db() as db:
            cook_org = db.query(Organization).filter_by(id=self.cook_org_id).first()
            self.assertEqual(cook_org.category.name, "COOK")

            driver_org = db.query(Organization).filter_by(id=self.driver_org_id).first()
            self.assertEqual(driver_org.category.name, "DRIVER")

            sec_org = db.query(Organization).filter_by(id=self.sec_org_id).first()
            self.assertEqual(sec_org.category.name, "SECURITY_GUARD")

        # Attempt to register organization with invalid/uncontrolled category
        ok, err_msg, _ = register_user(
            name="Invalid Org",
            email="invalid@cat.test",
            mobile="9899110007",
            password="Password123!",
            new_org_name="Invalid Category Org",
            category_name="Carpentry",
            role=ROLE_ORGANIZATION,
        )
        self.assertFalse(ok)
        self.assertIn("valid service category", err_msg.lower())

    # -------------------------------------------------------------------------
    # 9. Cook organization sees only Cook requirements
    # -------------------------------------------------------------------------
    def test_09_cook_organization_sees_only_cook_requirements(self):
        """Cook organization retrieves only Cook requirements; Driver and Guard are isolated."""
        reqs = get_requirements_for_organization(self.cook_org_id)
        self.assertGreater(len(reqs), 0)
        for r in reqs:
            self.assertEqual(r["Service Type"], "Cook", "Cook Org must only see Cook requirements")
            self.assertFalse(r["Lead ID"].startswith("Driver-"))
            self.assertFalse(r["Lead ID"].startswith("Security-"))

    # -------------------------------------------------------------------------
    # 10. Driver organization sees only Driver requirements
    # -------------------------------------------------------------------------
    def test_10_driver_organization_sees_only_driver_requirements(self):
        """Driver organization retrieves only Driver requirements; Cook and Guard are isolated."""
        reqs = get_requirements_for_organization(self.driver_org_id)
        self.assertGreater(len(reqs), 0)
        for r in reqs:
            self.assertEqual(r["Service Type"], "Driver", "Driver Org must only see Driver requirements")
            self.assertFalse(r["Lead ID"].startswith("Cook-"))
            self.assertFalse(r["Lead ID"].startswith("Security-"))

    # -------------------------------------------------------------------------
    # 11. Security organization sees only Security requirements
    # -------------------------------------------------------------------------
    def test_11_security_organization_sees_only_security_requirements(self):
        """Security organization retrieves only Security requirements; Cook and Driver are isolated."""
        reqs = get_requirements_for_organization(self.sec_org_id)
        self.assertGreater(len(reqs), 0)
        for r in reqs:
            self.assertEqual(r["Service Type"], "Security Guard", "Security Org must only see Security requirements")
            self.assertFalse(r["Lead ID"].startswith("Cook-"))
            self.assertFalse(r["Lead ID"].startswith("Driver-"))

    # -------------------------------------------------------------------------
    # 12. Normal users cannot access organization data
    # -------------------------------------------------------------------------
    def test_12_normal_users_cannot_access_organization_data(self):
        """Normal users attempting to access organization endpoints receive 403 Forbidden."""
        self.assertFalse(is_organization_user(self.normal_user))

        # REST API check: Organization requirements list
        res_list = self.client.get(
            f"/api/organizations/{self.cook_org_id}/requirements",
            headers={"Authorization": f"Bearer {self.normal_token}"},
        )
        self.assertEqual(res_list.status_code, 403)
        self.assertIn("Forbidden", res_list.json()["detail"])

        # REST API check: Status update
        res_update = self.client.patch(
            f"/api/organizations/{self.cook_org_id}/requirements/Cook-001/status",
            headers={"Authorization": f"Bearer {self.normal_token}"},
            json={"status": "Claimed"},
        )
        self.assertEqual(res_update.status_code, 403)

    # -------------------------------------------------------------------------
    # 13. Organizations cannot access other categories
    # -------------------------------------------------------------------------
    def test_13_organizations_cannot_access_other_categories(self):
        """Organizations attempting to access another organization or category receive 403 Forbidden."""
        # Cook Org user tries to query Driver Org requirements
        res_cross_org = self.client.get(
            f"/api/organizations/{self.driver_org_id}/requirements",
            headers={"Authorization": f"Bearer {self.cook_token}"},
        )
        self.assertEqual(res_cross_org.status_code, 403)

        # Cook Org user attempts category manipulation via query parameter
        res_tamper = self.client.get(
            f"/api/organizations/{self.cook_org_id}/requirements?category_id=2",
            headers={"Authorization": f"Bearer {self.cook_token}"},
        )
        self.assertEqual(res_tamper.status_code, 403)
        self.assertIn("category manipulation", res_tamper.json()["detail"].lower())

    # -------------------------------------------------------------------------
    # 14. Admin can access platform-wide data
    # -------------------------------------------------------------------------
    def test_14_admin_can_access_platform_wide_data(self):
        """Platform administrator can view all categories, organizations, and requirements."""
        self.assertTrue(is_admin_user(self.admin_user))

        # Admin API endpoint
        res = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("categories", data)
        self.assertIn("organizations", data)
        self.assertIn("requirements", data)

        all_reqs = data["requirements"]
        services_seen = {r["Service Type"] for r in all_reqs}
        self.assertIn("Cook", services_seen)
        self.assertIn("Driver", services_seen)
        self.assertIn("Security Guard", services_seen)

    # -------------------------------------------------------------------------
    # 15. Invalid authentication
    # -------------------------------------------------------------------------
    def test_15_invalid_authentication(self):
        """Authentication rejects wrong credentials and invalid tokens."""
        # Non-existent email
        ok, msg, _ = authenticate_user("ghost@user.test", "Password123!")
        self.assertFalse(ok)
        self.assertIn("Invalid email or password", msg)

        # Incorrect password
        ok, msg, _ = authenticate_user("superadmin@homedesk.test", "WrongPassword!")
        self.assertFalse(ok)
        self.assertIn("Invalid email or password", msg)

        # API check: 401 Unauthorized for bad login
        res_login = self.client.post("/api/auth/login", json={
            "email": "superadmin@homedesk.test",
            "password": "IncorrectPassword999",
        })
        self.assertEqual(res_login.status_code, 401)

        # API check: 401 Unauthorized for forged or expired token
        res_token = self.client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer forged.token.value"},
        )
        self.assertEqual(res_token.status_code, 401)

    # -------------------------------------------------------------------------
    # 16. Password handling
    # -------------------------------------------------------------------------
    def test_16_password_handling_and_hashing(self):
        """Passwords use secure bcrypt hashing and enforce complexity requirements."""
        plain = "MySecretPassword123!"
        hashed = hash_password(plain)
        self.assertNotEqual(plain, hashed)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))

        # Verification succeeds with correct password and fails with wrong
        self.assertTrue(verify_password(plain, hashed))
        self.assertFalse(verify_password("DifferentPass123!", hashed))

        # Password complexity validation
        ok_weak, msg_weak = validate_password_strength("short")
        self.assertFalse(ok_weak)
        self.assertIn("at least 8 characters", msg_weak)

        ok_no_num, msg_no_num = validate_password_strength("lettersalltheway")
        self.assertFalse(ok_no_num)
        self.assertIn("at least one number", msg_no_num)

        # Database verification: password_hash never stored as plaintext
        with get_db() as db:
            user = db.query(User).filter_by(email=self.admin_user["email"]).first()
            self.assertIsNotNone(user)
            self.assertNotEqual(user.password_hash, "Password123!")
            self.assertTrue(verify_password("Password123!", user.password_hash))

    # -------------------------------------------------------------------------
    # 17. AI configuration and error handling
    # -------------------------------------------------------------------------
    def test_17_ai_configuration_and_error_handling(self):
        """AI provider handles missing keys, API failures, and offline Ollama gracefully."""
        # 1. Missing API Key
        unconfigured_cloud = CloudAIProvider(api_key="")
        is_ready, msg = unconfigured_cloud.is_configured()
        self.assertFalse(is_ready)
        response_missing = unconfigured_cloud.ask("Tell me about cooks")
        self.assertIn("AI Assistant Offline", response_missing)

        # 2. Simulated Success
        configured_cloud = CloudAIProvider(api_key="valid-dummy-key")
        mock_success = MagicMock(status_code=200)
        mock_success.json.return_value = {
            "choices": [{"message": {"content": "HomeDesk offers reliable background-checked cooks."}}]
        }
        with patch("requests.post", return_value=mock_success):
            response_ok = configured_cloud.ask("Tell me about cooks")
            self.assertIn("background-checked cooks", response_ok)

        # 3. HTTP 401 Authentication Failure (no key leakage)
        mock_401 = MagicMock(status_code=401, text="Invalid key")
        with patch("requests.post", return_value=mock_401):
            response_401 = configured_cloud.ask("Hello?")
            self.assertIn("Authentication Error", response_401)
            self.assertNotIn("valid-dummy-key", response_401)

        # 4. Malformed Response
        mock_malformed = MagicMock(status_code=200)
        mock_malformed.json.return_value = {"broken": []}
        with patch("requests.post", return_value=mock_malformed):
            response_malformed = configured_cloud.ask("Hello?")
            self.assertIn("Malformed AI Response", response_malformed)

        # 5. Offline Ollama returns cloud switch guidance without crashing
        ollama = OllamaProvider(host="http://localhost:11434")
        import requests
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Refused")):
            response_ollama = ollama.ask("Hello?")
            self.assertIn("Ollama Unavailable", response_ollama)
            self.assertIn("AI_PROVIDER=openai", response_ollama)


if __name__ == "__main__":
    unittest.main()
