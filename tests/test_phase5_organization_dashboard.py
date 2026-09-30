"""
Phase 5 Verification Test Suite: Organization Dashboard for Receiving and Managing Requirements.

Verifies all Phase 5 requirements:
1. Test each organization category (Cook, Driver, Security Guard)
2. Test empty result state
3. Test multiple requirements & status management actions
4. Test unauthorized access
5. Test category manipulation attempts (cross-category retrieval and cross-category status modification)
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
    update_requirement_status,
    VALID_REQUIREMENT_STATUSES,
    mask_contact_info,
)
from services.auth_service import (
    authenticate_user,
    require_organization_access,
    UnauthorizedAccessError,
    ForbiddenRoleError,
    CategoryTamperingError,
    ROLE_NORMAL_USER,
    ROLE_ORGANIZATION,
    normalize_role,
)


class TestPhase5OrganizationDashboard(unittest.TestCase):

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
    # 1. Test Each Organization Category (Cook, Driver, Security Guard)
    # -------------------------------------------------------------------------
    def test_01_each_organization_category_isolation(self):
        """1. Each org sees requirements matching its category ONLY (Cook sees Cook, Driver sees Driver, Security sees Security)."""
        # Seed fresh requirements
        cook_lead = save_requirement_to_db("Cook", {
            "Name": "Chef Request Alpha",
            "Mobile": "9812300001",
            "City": "Mumbai",
            "Budget": 15000,
            "Cuisine Type": "North Indian",
            "Meals Per Day": 2,
        })
        driver_lead = save_requirement_to_db("Driver", {
            "Name": "Chauffeur Request Beta",
            "Mobile": "9812300002",
            "City": "Bangalore",
            "Budget": 22000,
            "Vehicle Type": "Automatic Sedan",
            "License Required": "Yes",
        })
        sec_lead = save_requirement_to_db("Security Guard", {
            "Name": "Guard Request Gamma",
            "Mobile": "9812300003",
            "City": "Hyderabad",
            "Budget": 26000,
            "Day/Night Shift": "Day",
            "Residential/Commercial": "Residential",
        })

        # Cook Organization Dashboard
        cook_reqs = get_requirements_for_organization(self.cook_org_id)
        self.assertGreater(len(cook_reqs), 0)
        cook_ids = [r["Lead ID"] for r in cook_reqs]
        self.assertIn(cook_lead["Lead ID"], cook_ids)
        self.assertNotIn(driver_lead["Lead ID"], cook_ids)
        self.assertNotIn(sec_lead["Lead ID"], cook_ids)
        for r in cook_reqs:
            self.assertEqual(r["category_id"], self.cook_cat_id)
            self.assertEqual(r["Service Type"], "Cook")

        # Driver Organization Dashboard
        driver_reqs = get_requirements_for_organization(self.driver_org_id)
        self.assertGreater(len(driver_reqs), 0)
        driver_ids = [r["Lead ID"] for r in driver_reqs]
        self.assertIn(driver_lead["Lead ID"], driver_ids)
        self.assertNotIn(cook_lead["Lead ID"], driver_ids)
        self.assertNotIn(sec_lead["Lead ID"], driver_ids)
        for r in driver_reqs:
            self.assertEqual(r["category_id"], self.driver_cat_id)
            self.assertEqual(r["Service Type"], "Driver")

        # Security Guard Organization Dashboard
        sec_reqs = get_requirements_for_organization(self.sec_org_id)
        self.assertGreater(len(sec_reqs), 0)
        sec_ids = [r["Lead ID"] for r in sec_reqs]
        self.assertIn(sec_lead["Lead ID"], sec_ids)
        self.assertNotIn(cook_lead["Lead ID"], sec_ids)
        self.assertNotIn(driver_lead["Lead ID"], sec_ids)
        for r in sec_reqs:
            self.assertEqual(r["category_id"], self.sec_cat_id)
            self.assertEqual(r["Service Type"], "Security Guard")

    # -------------------------------------------------------------------------
    # 2. Test Empty Result State
    # -------------------------------------------------------------------------
    def test_02_empty_result_state(self):
        """2. Organization with zero requirements returns empty list gracefully without errors."""
        # Create a fresh category and organization with zero requirements
        import uuid
        unique_suffix = uuid.uuid4().hex[:6]
        with get_db() as db:
            empty_cat = Category(
                name=f"EMPTY_{unique_suffix.upper()}",
                display_name=f"Empty Service {unique_suffix}",
            )
            db.add(empty_cat)
            db.flush()

            fresh_org = Organization(
                organization_name=f"Empty State Cleaners {unique_suffix}",
                slug=f"empty-org-{unique_suffix}",
                category_id=empty_cat.id,
                email=f"empty_{unique_suffix}@cleaners.com",
                status="active",
            )
            db.add(fresh_org)
            db.flush()
            fresh_org_id = fresh_org.id

        # Querying an organization whose category has zero requirements returns empty list []
        fresh_reqs = get_requirements_for_organization(fresh_org_id)
        self.assertEqual(fresh_reqs, [])

        empty_reqs = get_requirements_for_organization(999999)
        self.assertEqual(empty_reqs, [])

        # Non-existent or empty result handling in masking helper
        masked_empty = mask_contact_info("")
        self.assertEqual(masked_empty, "—")
        masked_phone = mask_contact_info("9820099887")
        self.assertEqual(masked_phone, "98****9887")

    # -------------------------------------------------------------------------
    # 3. Test Multiple Requirements & Status Management Actions
    # -------------------------------------------------------------------------
    def test_03_multiple_requirements_and_status_actions(self):
        """3. Organization can view multiple requirements and update statuses (New -> Claimed -> In Progress -> Completed)."""
        lead1 = save_requirement_to_db("Cook", {
            "Name": "Multi Customer 1",
            "Mobile": "9822200001",
            "City": "Mumbai",
            "Budget": 14000,
            "Cuisine Type": "Continental",
            "Meals Per Day": 2,
        })
        lead2 = save_requirement_to_db("Cook", {
            "Name": "Multi Customer 2",
            "Mobile": "9822200002",
            "City": "Mumbai",
            "Budget": 18000,
            "Cuisine Type": "Bengali",
            "Meals Per Day": 3,
        })
        lead3 = save_requirement_to_db("Cook", {
            "Name": "Multi Customer 3",
            "Mobile": "9822200003",
            "City": "Mumbai",
            "Budget": 21000,
            "Cuisine Type": "Italian",
            "Meals Per Day": 1,
        })

        cook_reqs = get_requirements_for_organization(self.cook_org_id)
        self.assertGreaterEqual(len(cook_reqs), 3)

        # Action: Progress lead1 from New -> Claimed
        ok1, msg1, updated1 = update_requirement_status(
            lead_id=lead1["Lead ID"],
            new_status="Claimed",
            organization_id=self.cook_org_id,
        )
        self.assertTrue(ok1, f"Failed updating to Claimed: {msg1}")
        self.assertEqual(updated1["Status"], "Claimed")

        # Action: Progress lead2 from New -> In Progress
        ok2, msg2, updated2 = update_requirement_status(
            lead_id=lead2["Lead ID"],
            new_status="In Progress",
            organization_id=self.cook_org_id,
        )
        self.assertTrue(ok2, f"Failed updating to In Progress: {msg2}")
        self.assertEqual(updated2["Status"], "In Progress")

        # Action: Progress lead3 from New -> Completed
        ok3, msg3, updated3 = update_requirement_status(
            lead_id=lead3["Lead ID"],
            new_status="Completed",
            organization_id=self.cook_org_id,
        )
        self.assertTrue(ok3, f"Failed updating to Completed: {msg3}")
        self.assertEqual(updated3["Status"], "Completed")

        # Action: Reject invalid status
        ok_bad, msg_bad, _ = update_requirement_status(
            lead_id=lead1["Lead ID"],
            new_status="InvalidStatusXYZ",
            organization_id=self.cook_org_id,
        )
        self.assertFalse(ok_bad)
        self.assertIn("Invalid status", msg_bad)

        # Test status update via API endpoint
        _, _, cook_user = authenticate_user("cooks@homedesk.com", "Password123!")
        res_api = self.client.patch(
            f"/api/organizations/{self.cook_org_id}/requirements/{lead1['Lead ID']}/status",
            json={"status": "Completed"},
            headers={"Authorization": f"Bearer {cook_user['token']}"},
        )
        self.assertEqual(res_api.status_code, 200)
        self.assertEqual(res_api.json()["requirement"]["Status"], "Completed")

    # -------------------------------------------------------------------------
    # 4. Test Unauthorized Access
    # -------------------------------------------------------------------------
    def test_04_unauthorized_access(self):
        """4. Unauthenticated users and Normal users are forbidden from accessing organization dashboard functionality."""
        _, _, normal_user = authenticate_user("user@homedesk.com", "Password123!")
        normal_token = normal_user["token"]

        # Python RBAC Guard
        with self.assertRaises(ForbiddenRoleError):
            require_organization_access(normal_user)

        with self.assertRaises(ForbiddenRoleError):
            get_requirements_for_authenticated_user(normal_user)

        with self.assertRaises(UnauthorizedAccessError):
            require_organization_access(None)

        # API: Normal user attempting to access organization requirements
        res_norm = self.client.get(
            f"/api/organizations/{self.cook_org_id}/requirements",
            headers={"Authorization": f"Bearer {normal_token}"},
        )
        self.assertEqual(res_norm.status_code, 403)

        # API: Normal user attempting to patch requirement status
        res_patch_norm = self.client.patch(
            f"/api/organizations/{self.cook_org_id}/requirements/Cook-001/status",
            json={"status": "Claimed"},
            headers={"Authorization": f"Bearer {normal_token}"},
        )
        self.assertEqual(res_patch_norm.status_code, 403)

        # API: Unauthenticated request
        res_unauth = self.client.get(f"/api/organizations/{self.cook_org_id}/requirements")
        self.assertEqual(res_unauth.status_code, 401)

    # -------------------------------------------------------------------------
    # 5. Test Category Manipulation Attempts
    # -------------------------------------------------------------------------
    def test_05_category_manipulation_attempts(self):
        """5. Cross-category query tampering and cross-category status modification attempts are blocked."""
        _, _, cook_user = authenticate_user("cooks@homedesk.com", "Password123!")
        _, _, driver_user = authenticate_user("admin@acme.com", "Password123!")

        # Create a Driver requirement
        driver_req = save_requirement_to_db("Driver", {
            "Name": "Driver Protected Client",
            "Mobile": "9833300001",
            "City": "Pune",
            "Budget": 19000,
            "Vehicle Type": "Manual Sedan",
            "License Required": "Yes",
        })
        driver_lead_id = driver_req["Lead ID"]

        # A. Cook organization attempts to query Driver requirements via get_requirements_for_authenticated_user
        with self.assertRaises(CategoryTamperingError):
            get_requirements_for_authenticated_user(cook_user, requested_category=self.driver_cat_id)

        with self.assertRaises(CategoryTamperingError):
            get_requirements_for_authenticated_user(cook_user, requested_category="DRIVER")

        # B. Cook organization attempts to query Driver requirements via API parameter
        res_tamper_api = self.client.get(
            f"/api/organizations/{self.cook_org_id}/requirements?category_id={self.driver_cat_id}",
            headers={"Authorization": f"Bearer {cook_user['token']}"},
        )
        self.assertEqual(res_tamper_api.status_code, 403)
        self.assertIn("Attempted category manipulation detected", res_tamper_api.json()["detail"])

        # C. Cook organization attempts to modify the status of a Driver requirement
        ok_cross, msg_cross, _ = update_requirement_status(
            lead_id=driver_lead_id,
            new_status="Claimed",
            organization_id=self.cook_org_id,  # Cook org attempting to update Driver req
        )
        self.assertFalse(ok_cross)
        self.assertIn("Unauthorized", msg_cross)

        # D. Cook organization attempts cross-organization status update via API
        res_cross_api = self.client.patch(
            f"/api/organizations/{self.driver_org_id}/requirements/{driver_lead_id}/status",
            json={"status": "Claimed"},
            headers={"Authorization": f"Bearer {cook_user['token']}"},  # Cook token used on Driver org URL
        )
        self.assertEqual(res_cross_api.status_code, 403)


if __name__ == "__main__":
    unittest.main()
