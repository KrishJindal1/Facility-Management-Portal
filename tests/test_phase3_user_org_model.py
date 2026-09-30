"""
Phase 3 Verification Test Suite: User and Organization Model.
Verifies all 8 Phase 3 requirements and security constraints:
1. Normal user can submit Cook requirement.
2. Normal user can submit Driver requirement.
3. Normal user can submit Security requirement.
4. Cook organization only receives Cook requirements.
5. Driver organization only receives Driver requirements.
6. Security organization only receives Security requirements.
7. Organization cannot retrieve another category by manipulating UI state or request parameters.
8. Normal users cannot access organization functionality.
9. Category values must be controlled values rather than arbitrary user input.
10. Normal user cannot become an organization simply by changing client-side role value.
11. Admin has access to platform-wide management (all organizations, categories, and requirements).
"""
import unittest
from database.connection import get_db
from database.models import User, Organization, Category, Requirement
from database.repository import (
    init_database,
    save_requirement_to_db,
    get_requirements_for_organization,
    get_user_requirements,
    get_controlled_categories,
    resolve_controlled_category,
    get_all_organizations_with_categories,
    get_all_requirements_for_admin,
    CONTROLLED_CATEGORIES,
)
from services.auth_service import (
    register_user,
    authenticate_user,
    is_normal_user,
    is_organization_user,
    is_admin_user,
)


class TestPhase3UserOrganizationModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        with get_db() as db:
            # Seeded Organizations
            cook_org = db.query(Organization).filter_by(slug="homedesk").first()
            driver_org = db.query(Organization).filter_by(slug="acme").first()
            sec_org = db.query(Organization).filter_by(slug="ironshield").first()

            assert cook_org is not None, "Cook org must exist"
            assert driver_org is not None, "Driver org must exist"
            assert sec_org is not None, "Security Guard org must exist"

            self.cook_org_id = int(cook_org.id)
            self.driver_org_id = int(driver_org.id)
            self.sec_org_id = int(sec_org.id)

            self.cook_cat_id = int(cook_org.category_id)
            self.driver_cat_id = int(driver_org.category_id)
            self.sec_cat_id = int(sec_org.category_id)

    # -------------------------------------------------------------
    # 1, 2, 3: Normal User Submissions
    # -------------------------------------------------------------
    def test_01_normal_user_submit_cook_requirement(self):
        """1. Normal user can submit Cook requirement."""
        mobile = "9900000001"
        payload = {
            "Name": "Normal User Alice",
            "Mobile": mobile,
            "City": "Mumbai",
            "Budget": 15000,
            "Cuisine Type": "North Indian",
            "Meals Per Day": 2,
        }
        saved = save_requirement_to_db("Cook", payload)
        self.assertIsNotNone(saved)
        self.assertTrue(saved["Lead ID"].startswith("Cook-"))
        self.assertEqual(saved["category_id"], self.cook_cat_id)

        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=saved["Lead ID"]).first()
            self.assertIsNotNone(req)
            self.assertEqual(req.service_type, "Cook")
            self.assertEqual(req.category_id, self.cook_cat_id)
            self.assertIsNotNone(req.user_id)
            # Must NOT belong directly to an organization
            self.assertFalse(hasattr(req, "organization_id"))

    def test_02_normal_user_submit_driver_requirement(self):
        """2. Normal user can submit Driver requirement."""
        mobile = "9900000002"
        payload = {
            "Name": "Normal User Bob",
            "Mobile": mobile,
            "City": "Bangalore",
            "Budget": 22000,
            "Vehicle Type": "SUV",
            "License Required": "Commercial",
        }
        saved = save_requirement_to_db("Driver", payload)
        self.assertIsNotNone(saved)
        self.assertTrue(saved["Lead ID"].startswith("Driver-"))
        self.assertEqual(saved["category_id"], self.driver_cat_id)

        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=saved["Lead ID"]).first()
            self.assertIsNotNone(req)
            self.assertEqual(req.service_type, "Driver")
            self.assertEqual(req.category_id, self.driver_cat_id)

    def test_03_normal_user_submit_security_requirement(self):
        """3. Normal user can submit Security Guard requirement."""
        mobile = "9900000003"
        payload = {
            "Name": "Normal User Charlie",
            "Mobile": mobile,
            "City": "Delhi",
            "Budget": 18000,
            "Day/Night Shift": "24/7 Rotational",
            "Residential/Commercial": "Gated Society",
        }
        saved = save_requirement_to_db("Security Guard", payload)
        self.assertIsNotNone(saved)
        self.assertTrue(saved["Lead ID"].startswith("Security-"))
        self.assertEqual(saved["category_id"], self.sec_cat_id)

        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=saved["Lead ID"]).first()
            self.assertIsNotNone(req)
            self.assertEqual(req.service_type, "Security Guard")
            self.assertEqual(req.category_id, self.sec_cat_id)

    # -------------------------------------------------------------
    # 4, 5, 6: Category Isolation per Organization
    # -------------------------------------------------------------
    def test_04_cook_organization_only_receives_cook_requirements(self):
        """4. Cook organization only receives Cook requirements."""
        reqs = get_requirements_for_organization(self.cook_org_id)
        self.assertGreater(len(reqs), 0, "Cook org must receive submitted Cook requirements")
        for r in reqs:
            self.assertEqual(
                r.get("category_id"),
                self.cook_cat_id,
                f"Cook org received non-cook requirement: {r}",
            )
            self.assertEqual(r.get("Service Type"), "Cook")

    def test_05_driver_organization_only_receives_driver_requirements(self):
        """5. Driver organization only receives Driver requirements."""
        reqs = get_requirements_for_organization(self.driver_org_id)
        self.assertGreater(len(reqs), 0, "Driver org must receive submitted Driver requirements")
        for r in reqs:
            self.assertEqual(
                r.get("category_id"),
                self.driver_cat_id,
                f"Driver org received non-driver requirement: {r}",
            )
            self.assertEqual(r.get("Service Type"), "Driver")

    def test_06_security_organization_only_receives_security_requirements(self):
        """6. Security organization only receives Security requirements."""
        reqs = get_requirements_for_organization(self.sec_org_id)
        self.assertGreater(len(reqs), 0, "Security org must receive submitted Security requirements")
        for r in reqs:
            self.assertEqual(
                r.get("category_id"),
                self.sec_cat_id,
                f"Security org received non-security requirement: {r}",
            )
            self.assertEqual(r.get("Service Type"), "Security Guard")

    # -------------------------------------------------------------
    # 7. Anti-Tampering: Organization cannot retrieve another category
    # -------------------------------------------------------------
    def test_07_organization_cannot_retrieve_another_category_by_parameter_tampering(self):
        """
        7. Organization cannot retrieve another category by manipulating UI state
        or request parameters (e.g. passing category_id or service_name in request).
        """
        # Acme is a Driver organization (category_id = 2).
        # Suppose a client tampers with request parameters and asks for Cook (category_id = 1)
        # or Security (category_id = 3).
        tampered_cook = get_requirements_for_organization(self.driver_org_id, requested_category=self.cook_cat_id)
        self.assertEqual(
            tampered_cook,
            [],
            "SECURITY VIOLATION: Driver organization successfully accessed Cook requirements via parameter tampering!",
        )

        tampered_sec = get_requirements_for_organization(self.driver_org_id, requested_category="Security Guard")
        self.assertEqual(
            tampered_sec,
            [],
            "SECURITY VIOLATION: Driver organization accessed Security requirements via parameter tampering!",
        )

        # Cook organization attempting to pass Driver category
        tampered_driver = get_requirements_for_organization(self.cook_org_id, requested_category="DRIVER")
        self.assertEqual(
            tampered_driver,
            [],
            "SECURITY VIOLATION: Cook organization accessed Driver requirements via parameter tampering!",
        )

    # -------------------------------------------------------------
    # 8. Normal Users Cannot Access Organization Functionality
    # -------------------------------------------------------------
    def test_08_normal_user_cannot_access_organization_functionality(self):
        """
        8. Normal users cannot access organization functionality:
        - Cannot access organization requirements endpoint / query.
        - Cannot view other users' submissions.
        - Cannot access organization dashboard.
        """
        # Register a normal user
        email = "normal_client@example.com"
        with get_db() as db:
            old = db.query(User).filter_by(email=email).first()
            if old:
                db.delete(old)

        success, msg, user_data = register_user(
            name="Normal Client User",
            email=email,
            mobile="9811122233",
            password="StrongPassword123!",
            role="user",
        )
        self.assertTrue(success)
        self.assertEqual(user_data["role"], "user")
        self.assertIsNone(user_data["organization_id"])

        # Attempt to call get_requirements_for_organization with normal user ID (not an org)
        res = get_requirements_for_organization(user_data["id"])
        self.assertEqual(res, [], "Normal user ID should not resolve to an organization")

        # Normal user only sees their own requirements
        user_reqs = get_user_requirements(user_id=user_data["id"])
        # Should be empty or only Alice's, Bob's, etc.
        for r in user_reqs:
            self.assertEqual(r["user_id"], user_data["id"])

    # -------------------------------------------------------------
    # 9. Controlled Categories Enforcement
    # -------------------------------------------------------------
    def test_09_category_values_must_be_controlled_values(self):
        """Controlled categories must be strictly COOK, DRIVER, SECURITY_GUARD."""
        controlled = get_controlled_categories()
        codes = [c["name"] for c in controlled]
        self.assertEqual(set(codes), {"COOK", "DRIVER", "SECURITY_GUARD"})

        # Arbitrary categories must NOT resolve
        self.assertIsNone(resolve_controlled_category("Plumber"))
        self.assertIsNone(resolve_controlled_category("Carpenter"))
        self.assertIsNone(resolve_controlled_category(99999))

        # Registering an organization with arbitrary category must fail
        success, msg, _ = register_user(
            name="Plumbing Corp Owner",
            email="plumber@test.com",
            mobile="9822233344",
            password="StrongPassword123!",
            new_org_name="Super Plumbers Ltd",
            category_name="Plumbing",
        )
        self.assertFalse(success)
        self.assertIn("select one valid service category", msg)

    # -------------------------------------------------------------
    # 10. Normal User Cannot Become Organization via Client Value
    # -------------------------------------------------------------
    def test_10_normal_user_cannot_become_organization_via_client_value(self):
        """A normal user cannot become an organization simply by passing client-side role."""
        email = "sneaky_user@test.com"
        with get_db() as db:
            old = db.query(User).filter_by(email=email).first()
            if old:
                db.delete(old)

        # Passing role="organization" without an organization registration defaults to user
        success, msg, user_data = register_user(
            name="Sneaky Client",
            email=email,
            mobile="9833344455",
            password="StrongPassword123!",
            role="organization",  # Client tries to claim organization role without org
        )
        self.assertTrue(success)
        self.assertEqual(user_data["role"], "user", "Role must be user when no organization is bound")
        self.assertIsNone(user_data["organization_id"])

        # Also client cannot self-assign "admin"
        email_admin = "sneaky_admin@test.com"
        success_admin, msg_admin, _ = register_user(
            name="Sneaky Admin",
            email=email_admin,
            mobile="9844455566",
            password="StrongPassword123!",
            role="admin",
        )
        self.assertFalse(success_admin)
        self.assertIn("Administrator accounts cannot be created via public registration", msg_admin)

    # -------------------------------------------------------------
    # 11. Admin Global Management Access
    # -------------------------------------------------------------
    def test_11_admin_has_platform_wide_access(self):
        """Admin can see all organizations, all categories, and all requirements."""
        all_cats = get_controlled_categories()
        all_orgs = get_all_organizations_with_categories()
        all_reqs = get_all_requirements_for_admin()

        self.assertEqual(len(all_cats), 3)
        self.assertGreaterEqual(len(all_orgs), 3)
        self.assertGreaterEqual(len(all_reqs), 3)

        # Verify organizations carry their category information
        org_names = [o["organization_name"] for o in all_orgs]
        self.assertIn("HomeDesk Primary", org_names)
        self.assertIn("Acme Facilities Group", org_names)
        self.assertIn("IronShield Security", org_names)

        # Requirements contain Cook, Driver, and Security
        services = {r.get("Service Type") for r in all_reqs}
        self.assertIn("Cook", services)
        self.assertIn("Driver", services)
        self.assertIn("Security Guard", services)


if __name__ == "__main__":
    unittest.main(verbosity=2)
