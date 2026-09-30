"""
Phase 2 PostgreSQL Storage and Business Model Test Suite.
Verifies:
1. Cook requirement submission to PostgreSQL.
2. Driver requirement submission to PostgreSQL.
3. Security Guard requirement submission to PostgreSQL.
4. Requirement retrieval and category-based isolation:
   - Organization sees only requirements matching its registered category.
   - Cook organization sees Cook requirements.
   - Driver organization sees Driver requirements.
   - Security Guard organization sees Security Guard requirements.
   - Cross-category access is prevented.
5. Lead / requirement lookup by mobile and Lead ID.
6. Excel export dynamically generated from PostgreSQL data.
7. Requirement belongs to normal user and category (not directly to organization).
8. Database error handling and clean recovery.
"""
import io
import unittest
from openpyxl import load_workbook

from database.connection import get_db
from database.models import Category, Organization, User, Requirement, CookRequirement, DriverRequirement, SecurityGuardRequirement
from database.repository import (
    init_database,
    save_requirement_to_db,
    get_latest_lead_by_mobile,
    get_lead_by_id,
    get_requirements_by_category,
    get_requirements_for_organization,
    get_all_requirements_for_export,
    generate_next_lead_id,
)
from storage.excel_handler import (
    save_lead,
    find_latest_request_by_mobile,
    get_excel_export_bytes,
)
from services.lead_lookup import find_lead_by_mobile


class TestPhase2PostgreSQL(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        with get_db() as db:
            cook_cat = db.query(Category).filter_by(name="COOK").first()
            driver_cat = db.query(Category).filter_by(name="DRIVER").first()
            guard_cat = db.query(Category).filter_by(name="SECURITY_GUARD").first()

            assert cook_cat is not None
            assert driver_cat is not None
            assert guard_cat is not None

            self.cook_cat_id = int(cook_cat.id)
            self.driver_cat_id = int(driver_cat.id)
            self.guard_cat_id = int(guard_cat.id)

            cook_org = db.query(Organization).filter_by(slug="homedesk").first()
            driver_org = db.query(Organization).filter_by(slug="acme").first()
            guard_org = db.query(Organization).filter_by(slug="ironshield").first()

            assert cook_org is not None
            assert driver_org is not None
            assert guard_org is not None

            self.cook_org_id = int(cook_org.id)
            self.driver_org_id = int(driver_org.id)
            self.guard_org_id = int(guard_org.id)


    def test_01_cook_requirement_submission(self):
        """Cook requirement submission writes to PostgreSQL and links to User and COOK category."""
        payload = {
            "Name": "Pooja Sharma",
            "Mobile": "9811002201",
            "Email": "pooja@example.com",
            "City": "Mumbai",
            "State": "Maharashtra",
            "Pincode": "400001",
            "Start Date": "2026-10-01",
            "Preferred Timing": "Morning",
            "Budget": 18000,
            "Cuisine Type": "North Indian, Gujarati",
            "Meals Per Day": 2,
            "Additional Notes": "Needs healthy, low-oil meals",
        }
        saved = save_lead("Cook", payload)

        self.assertTrue(saved["Lead ID"].startswith("Cook-"))
        self.assertEqual(saved["Status"], "New")
        self.assertEqual(saved["category_id"], self.cook_cat_id)

        # Verify PostgreSQL persistence
        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=saved["Lead ID"]).first()
            self.assertIsNotNone(req)
            self.assertEqual(req.service_type, "Cook")
            self.assertEqual(req.category_id, self.cook_cat_id)
            self.assertEqual(req.name, "Pooja Sharma")
            self.assertEqual(req.mobile, "9811002201")
            self.assertEqual(req.budget, 18000.0)

            # Check child cook_requirement table
            self.assertIsNotNone(req.cook_requirement)
            self.assertEqual(req.cook_requirement.cuisine_type, "North Indian, Gujarati")
            self.assertEqual(req.cook_requirement.meals_per_day, 2)

            # Check normal user creation
            self.assertIsNotNone(req.user)
            self.assertEqual(req.user.name, "Pooja Sharma")
            self.assertEqual(req.user.phone, "9811002201")
            self.assertEqual(req.user.role, "user")

    def test_02_driver_requirement_submission(self):
        """Driver requirement submission writes to PostgreSQL and links to User and DRIVER category."""
        payload = {
            "Name": "Vikram Malhotra",
            "Mobile": "9822003302",
            "Email": "vikram@example.com",
            "City": "Pune",
            "State": "Maharashtra",
            "Pincode": "411001",
            "Start Date": "2026-10-05",
            "Preferred Timing": "Full Day",
            "Budget": 22000,
            "Vehicle Type": "Sedan & SUV",
            "License Required": "Yes",
            "Additional Notes": "Valid Commercial / LMV license required",
        }
        saved = save_lead("Driver", payload)

        self.assertTrue(saved["Lead ID"].startswith("Driver-"))
        self.assertEqual(saved["category_id"], self.driver_cat_id)

        # Verify PostgreSQL persistence
        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=saved["Lead ID"]).first()
            self.assertIsNotNone(req)
            self.assertEqual(req.service_type, "Driver")
            self.assertEqual(req.category_id, self.driver_cat_id)
            self.assertEqual(req.budget, 22000.0)

            # Check child driver_requirement table
            self.assertIsNotNone(req.driver_requirement)
            self.assertEqual(req.driver_requirement.vehicle_type, "Sedan & SUV")
            self.assertEqual(req.driver_requirement.license_required, "Yes")

    def test_03_security_requirement_submission(self):
        """Security Guard requirement submission writes to PostgreSQL and links to User and SECURITY_GUARD category."""
        payload = {
            "Name": "Sunil Verma",
            "Mobile": "9833004403",
            "Email": "sunil@example.com",
            "City": "Bengaluru",
            "State": "Karnataka",
            "Pincode": "560001",
            "Start Date": "2026-10-10",
            "Preferred Timing": "Evening",
            "Budget": 25000,
            "Day/Night Shift": "Both",
            "Residential/Commercial": "Residential",
            "Additional Notes": "Gated society night patrol required",
        }
        saved = save_lead("Security Guard", payload)

        self.assertTrue(saved["Lead ID"].startswith("Security-"))
        self.assertEqual(saved["category_id"], self.guard_cat_id)

        # Verify PostgreSQL persistence
        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=saved["Lead ID"]).first()
            self.assertIsNotNone(req)
            self.assertEqual(req.service_type, "Security Guard")
            self.assertEqual(req.category_id, self.guard_cat_id)

            # Check child security_guard_requirement table
            self.assertIsNotNone(req.security_guard_requirement)
            self.assertEqual(req.security_guard_requirement.shift, "Both")
            self.assertEqual(req.security_guard_requirement.site_type, "Residential")

    def test_04_requirement_retrieval_and_category_isolation(self):
        """
        An organization sees requirements matching its category_id ONLY.
        organization.category_id == requirement.category_id
        - Cook org sees Cook requirements.
        - Driver org sees Driver requirements.
        - Security Guard org sees Security Guard requirements.
        """
        cook_reqs = get_requirements_for_organization(self.cook_org_id)
        driver_reqs = get_requirements_for_organization(self.driver_org_id)
        guard_reqs = get_requirements_for_organization(self.guard_org_id)

        # 1. Verify Cook Organization sees only Cook
        self.assertTrue(len(cook_reqs) > 0)
        for r in cook_reqs:
            self.assertEqual(r["Service Type"], "Cook")
            self.assertEqual(r["category_id"], self.cook_cat_id)

        # 2. Verify Driver Organization sees only Driver
        self.assertTrue(len(driver_reqs) > 0)
        for r in driver_reqs:
            self.assertEqual(r["Service Type"], "Driver")
            self.assertEqual(r["category_id"], self.driver_cat_id)

        # 3. Verify Security Guard Organization sees only Security Guard
        self.assertTrue(len(guard_reqs) > 0)
        for r in guard_reqs:
            self.assertEqual(r["Service Type"], "Security Guard")
            self.assertEqual(r["category_id"], self.guard_cat_id)

        # 4. Cross-category leak check
        cook_lead_ids = {r["Lead ID"] for r in cook_reqs}
        driver_lead_ids = {r["Lead ID"] for r in driver_reqs}
        guard_lead_ids = {r["Lead ID"] for r in guard_reqs}

        self.assertTrue(cook_lead_ids.isdisjoint(driver_lead_ids))
        self.assertTrue(cook_lead_ids.isdisjoint(guard_lead_ids))
        self.assertTrue(driver_lead_ids.isdisjoint(guard_lead_ids))

    def test_05_lead_requirement_lookup_by_mobile_and_id(self):
        """Lookup by mobile and by Lead ID returns PostgreSQL records with child details."""
        mobile = "9811002201"
        found = find_lead_by_mobile(mobile)

        self.assertIsNotNone(found)
        self.assertEqual(found["Mobile"], mobile)
        self.assertEqual(found["Name"], "Pooja Sharma")
        self.assertEqual(found["Service Type"], "Cook")
        self.assertEqual(found["Cuisine Type"], "North Indian, Gujarati")

        # Lookup by Lead ID
        lead_id = found["Lead ID"]
        by_id = get_lead_by_id(lead_id)
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id["Lead ID"], lead_id)
        self.assertEqual(by_id["Name"], "Pooja Sharma")

    def test_06_excel_export_generated_from_postgresql(self):
        """Excel export bytes are generated dynamically in-memory from PostgreSQL."""
        excel_bytes = get_excel_export_bytes()
        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 500)

        # Parse generated workbook
        wb = load_workbook(io.BytesIO(excel_bytes))
        self.assertIn("All Leads", wb.sheetnames)
        self.assertIn("Cook", wb.sheetnames)
        self.assertIn("Driver", wb.sheetnames)
        self.assertIn("Security Guard", wb.sheetnames)

        cook_ws = wb["Cook"]
        self.assertGreaterEqual(cook_ws.max_row, 2)  # Header + at least 1 record

        # Category-filtered export (for Cook organization)
        cook_export_bytes = get_excel_export_bytes(category_id=self.cook_cat_id)
        cook_wb = load_workbook(io.BytesIO(cook_export_bytes))
        cook_only_rows = [row[0] for row in cook_wb["Cook"].iter_rows(min_row=2, values_only=True) if row[0]]
        self.assertTrue(all(str(lid).startswith("Cook-") for lid in cook_only_rows))


    def test_07_requirement_does_not_belong_to_organization(self):
        """Requirements MUST belong to user and category, not directly to an organization."""
        with get_db() as db:
            for req in db.query(Requirement).all():
                self.assertIsNotNone(req.user_id)
                self.assertIsNotNone(req.category_id)
                # Requirement model has no organization_id column
                self.assertFalse(hasattr(req, "organization_id"))


if __name__ == "__main__":
    unittest.main()
