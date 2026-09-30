"""
Unit and Integration Tests for Phase 6: Normal User Experience and Separation
from Organization Functionality.

Verifies:
1. Normal user can open platform, select service (Cook, Driver, Security Guard).
2. Cook form submission persists to PostgreSQL with category = COOK and returns Lead ID.
3. Driver form submission persists to PostgreSQL with category = DRIVER and returns Lead ID.
4. Security Guard form submission persists to PostgreSQL with category = SECURITY_GUARD and returns Lead ID.
5. Normal user receives tracked requirement identifier and can track own submission.
6. Normal user CANNOT see other users' requirements.
7. Normal user CANNOT see organization dashboard (403 Forbidden).
8. Normal user CANNOT access platform administrator functionality (403 Forbidden).
9. Requirement category is immutable post-submission (client-side category tampering blocked).
"""

import unittest
from datetime import datetime
from fastapi.testclient import TestClient

from api.main import app
from database.connection import get_db
from database.models import Requirement
from database.repository import (
    init_database,
    save_requirement_to_db,
    get_user_requirements,
    get_lead_by_id,
    normalize_category_name,
)
from services.auth_service import (
    register_user,
    authenticate_user,
    is_organization_user,
    is_admin_user,
    ROLE_NORMAL_USER,
    ROLE_ORGANIZATION,
    ROLE_ADMIN,
)
from services.lead_lookup import find_lead_by_mobile
from storage.excel_handler import save_lead
from storage.serial_generator import generate_serial


class TestPhase6NormalUserExperience(unittest.TestCase):
    """Test suite for Phase 6 Normal User Experience and Organization Separation."""

    @classmethod
    def setUpClass(cls):
        init_database()
        cls.client = TestClient(app)

        # Register normal user A
        cls.user_a_email = f"user_a_{int(datetime.now().timestamp())}@test.com"
        ok_a, _, cls.user_a_data = register_user(
            name="Alice Normal User",
            email=cls.user_a_email,
            mobile="9812000001",
            password="Password123!",
            role=ROLE_NORMAL_USER,
        )
        assert ok_a, "Failed to register User A"

        # Register normal user B
        cls.user_b_email = f"user_b_{int(datetime.now().timestamp())}@test.com"
        ok_b, _, cls.user_b_data = register_user(
            name="Bob Normal User",
            email=cls.user_b_email,
            mobile="9812000002",
            password="Password123!",
            role=ROLE_NORMAL_USER,
        )
        assert ok_b, "Failed to register User B"

        # Authenticate users to get tokens
        _, _, auth_a = authenticate_user(cls.user_a_email, "Password123!")
        cls.token_a = auth_a["token"]

        _, _, auth_b = authenticate_user(cls.user_b_email, "Password123!")
        cls.token_b = auth_b["token"]

        # Authenticate Admin and Org for baseline checks
        _, _, admin_auth = authenticate_user("admin@homedesk.com", "Password123!")
        cls.admin_token = admin_auth["token"]

        _, _, org_auth = authenticate_user("cooks@homedesk.com", "Password123!")
        cls.org_token = org_auth["token"]

    def test_01_cook_form_submission_persists_as_cook_category(self):
        """Cook form submission -> category = COOK, Lead ID prefix = Cook-, persisted in PostgreSQL."""
        lead_id = generate_serial("Cook")
        self.assertTrue(lead_id.startswith("Cook-"))

        cook_payload = {
            "Lead ID": lead_id,
            "Name": "Kavita Customer",
            "Mobile": "9812000010",
            "City": "Mumbai",
            "Address": "Bandra West",
            "Pincode": "400050",
            "Budget": 18000,
            "Cuisine Type": "North Indian, South Indian",
            "Meals Per Day": 2,
            "Start Date": "2026-10-05",
            "Preferred Timing": "Morning",
            "Status": "New",
        }

        saved = save_lead("Cook", cook_payload)

        self.assertIsNotNone(saved)
        self.assertEqual(saved["Lead ID"], lead_id)
        self.assertEqual(saved["Service Type"], "Cook")
        self.assertEqual(saved["category_id"], 1)

        # Verify in PostgreSQL
        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=lead_id).first()
            self.assertIsNotNone(req, "Requirement must be persisted in PostgreSQL")
            self.assertEqual(req.service_type, "Cook")
            self.assertEqual(req.category.name, "COOK")
            self.assertEqual(req.budget, 18000.0)

            # Child detail table verification
            self.assertIsNotNone(req.cook_requirement)
            self.assertEqual(req.cook_requirement.cuisine_type, "North Indian, South Indian")
            self.assertEqual(req.cook_requirement.meals_per_day, 2)

    def test_02_driver_form_submission_persists_as_driver_category(self):
        """Driver form submission -> category = DRIVER, Lead ID prefix = Driver-, persisted in PostgreSQL."""
        lead_id = generate_serial("Driver")
        self.assertTrue(lead_id.startswith("Driver-"))

        driver_payload = {
            "Lead ID": lead_id,
            "Name": "Rohit Customer",
            "Mobile": "9812000020",
            "City": "Delhi",
            "Address": "Connaught Place",
            "Pincode": "110001",
            "Budget": 22000,
            "Vehicle Type": "SUV / Manual",
            "License Required": "Commercial",
            "Start Date": "2026-10-10",
            "Preferred Timing": "Full Day (8 AM - 6 PM)",
            "Status": "New",
        }

        saved = save_lead("Driver", driver_payload)

        self.assertIsNotNone(saved)
        self.assertEqual(saved["Lead ID"], lead_id)
        self.assertEqual(saved["Service Type"], "Driver")
        self.assertEqual(saved["category_id"], 2)

        # Verify in PostgreSQL
        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=lead_id).first()
            self.assertIsNotNone(req, "Requirement must be persisted in PostgreSQL")
            self.assertEqual(req.service_type, "Driver")
            self.assertEqual(req.category.name, "DRIVER")
            self.assertEqual(req.budget, 22000.0)

            # Child detail table verification
            self.assertIsNotNone(req.driver_requirement)
            self.assertEqual(req.driver_requirement.vehicle_type, "SUV / Manual")
            self.assertEqual(req.driver_requirement.license_required, "Commercial")

    def test_03_security_guard_form_submission_persists_as_security_guard_category(self):
        """Security Guard form submission -> category = SECURITY_GUARD, Lead ID prefix = Security-, persisted in PostgreSQL."""
        lead_id = generate_serial("Security Guard")
        self.assertTrue(lead_id.startswith("Security-"))

        guard_payload = {
            "Lead ID": lead_id,
            "Name": "Meera Customer",
            "Mobile": "9812000030",
            "City": "Bengaluru",
            "Address": "Indiranagar",
            "Pincode": "560038",
            "Budget": 25000,
            "Day/Night Shift": "24/7 Rotational",
            "Residential/Commercial": "Residential Villa",
            "Start Date": "2026-10-15",
            "Preferred Timing": "Night Shift (8 PM - 8 AM)",
            "Status": "New",
        }

        saved = save_lead("Security Guard", guard_payload)

        self.assertIsNotNone(saved)
        self.assertEqual(saved["Lead ID"], lead_id)
        self.assertEqual(saved["Service Type"], "Security Guard")
        self.assertEqual(saved["category_id"], 3)

        # Verify in PostgreSQL
        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=lead_id).first()
            self.assertIsNotNone(req, "Requirement must be persisted in PostgreSQL")
            self.assertEqual(req.service_type, "Security Guard")
            self.assertEqual(req.category.name, "SECURITY_GUARD")
            self.assertEqual(req.budget, 25000.0)

            # Child detail table verification
            self.assertIsNotNone(req.security_guard_requirement)
            self.assertEqual(req.security_guard_requirement.shift, "24/7 Rotational")
            self.assertEqual(req.security_guard_requirement.site_type, "Residential Villa")

    def test_04_normal_user_receives_identifier_and_can_track_submission(self):
        """Normal user receives lead identifier and can track via mobile or identifier lookup."""
        mobile = "9812000040"
        lead_id = generate_serial("Cook")

        payload = {
            "Lead ID": lead_id,
            "Name": "Tracking Test User",
            "Mobile": mobile,
            "City": "Pune",
            "Budget": 16000,
            "Cuisine Type": "Maharashtrian",
            "Meals Per Day": 3,
            "Status": "New",
        }
        save_lead("Cook", payload)

        # 1. Lookup by Mobile
        found_by_mobile = find_lead_by_mobile(mobile)
        self.assertIsNotNone(found_by_mobile)
        self.assertEqual(found_by_mobile["Lead ID"], lead_id)
        self.assertEqual(found_by_mobile["Service Type"], "Cook")
        self.assertEqual(found_by_mobile["Status"], "New")

        # 2. Lookup by Lead ID
        found_by_id = get_lead_by_id(lead_id)
        self.assertIsNotNone(found_by_id)
        self.assertEqual(found_by_id["Lead ID"], lead_id)
        self.assertEqual(found_by_id["Mobile"], mobile)
        self.assertEqual(found_by_id["Budget"], 16000.0)

    def test_05_normal_user_cannot_see_other_users_requirements(self):
        """Normal user A can only view their own submissions; cannot view User B's submissions."""
        user_a_id = self.user_a_data["id"]
        user_b_id = self.user_b_data["id"]

        # User A submits a requirement
        lead_a = generate_serial("Cook")
        save_requirement_to_db(
            "Cook",
            {"Lead ID": lead_a, "Name": "Alice", "Mobile": "9812000001", "City": "Delhi", "Budget": 12000},
            user_id=user_a_id,
        )

        # User B submits a requirement
        lead_b = generate_serial("Driver")
        save_requirement_to_db(
            "Driver",
            {"Lead ID": lead_b, "Name": "Bob", "Mobile": "9812000002", "City": "Noida", "Budget": 20000},
            user_id=user_b_id,
        )

        # User A tracking through repository
        reqs_a = get_user_requirements(user_id=user_a_id)
        lead_ids_a = [r["Lead ID"] for r in reqs_a]
        self.assertIn(lead_a, lead_ids_a)
        self.assertNotIn(lead_b, lead_ids_a, "User A must NOT see User B's requirement")

        # User B tracking through repository
        reqs_b = get_user_requirements(user_id=user_b_id)
        lead_ids_b = [r["Lead ID"] for r in reqs_b]
        self.assertIn(lead_b, lead_ids_b)
        self.assertNotIn(lead_a, lead_ids_b, "User B must NOT see User A's requirement")

        # API Level Authorization: User A attempts to view User B's requirements
        res_tamper = self.client.get(
            f"/api/users/{user_b_id}/requirements",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        self.assertEqual(res_tamper.status_code, 403, "User A must receive 403 Forbidden when requesting User B's data")

        # API Level Authorization: User A accesses their own requirements
        res_own = self.client.get(
            f"/api/users/{user_a_id}/requirements",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        self.assertEqual(res_own.status_code, 200)
        own_lead_ids = [item["Lead ID"] for item in res_own.json()]
        self.assertIn(lead_a, own_lead_ids)
        self.assertNotIn(lead_b, own_lead_ids)

    def test_06_normal_user_cannot_access_organization_dashboard(self):
        """Normal user role is forbidden from accessing organization dashboard endpoints."""
        normal_user = self.user_a_data
        self.assertFalse(is_organization_user(normal_user))

        # Attempt to access organization requirements endpoint
        res = self.client.get(
            "/api/organizations/1/requirements",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        self.assertEqual(res.status_code, 403, "Normal user must be forbidden from organization requirements")
        self.assertIn("Forbidden", res.json()["detail"])

        # Attempt to update status via organization endpoint
        res_status = self.client.patch(
            "/api/organizations/1/requirements/Cook-001/status",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"status": "Completed"},
        )
        self.assertEqual(res_status.status_code, 403, "Normal user cannot update requirement status")

    def test_07_normal_user_cannot_access_admin_functionality(self):
        """Normal user is forbidden from accessing platform administrator overview."""
        normal_user = self.user_a_data
        self.assertFalse(is_admin_user(normal_user))

        res = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        self.assertEqual(res.status_code, 403, "Normal user must be forbidden from admin overview")
        self.assertIn("Forbidden", res.json()["detail"])

    def test_08_requirement_category_cannot_be_changed_after_submission(self):
        """Requirement category is immutable once submitted; client tampering is blocked with ValueError."""
        lead_id = generate_serial("Cook")
        payload = {
            "Lead ID": lead_id,
            "Name": "Category Security Test",
            "Mobile": "9812000088",
            "City": "Delhi",
            "Budget": 15000,
            "Cuisine Type": "North Indian",
        }
        # First submission as Cook
        save_lead("Cook", payload)

        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=lead_id).first()
            self.assertEqual(req.category_id, 1)

        # Attempt to mutate category to Driver with the same Lead ID
        tampered_payload = dict(payload)
        tampered_payload["Budget"] = 20000

        with self.assertRaises(ValueError) as ctx:
            save_requirement_to_db("Driver", tampered_payload)

        self.assertIn("Category tampering blocked", str(ctx.exception))

        # Verify that category in PostgreSQL remains untouched
        with get_db() as db:
            req_after = db.query(Requirement).filter_by(lead_id=lead_id).first()
            self.assertEqual(req_after.category_id, 1, "Category in database must remain COOK (1)")
            self.assertEqual(req_after.category.name, "COOK")


if __name__ == "__main__":
    unittest.main()
