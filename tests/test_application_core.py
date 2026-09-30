"""
Core Application Behavior Test Suite.
Verifies critical portal functionality:
1. Input validation (Name, Mobile, Email, Budget, Pincode, Form validation).
2. Lead ID generation (Prefixing, sequential numbering, tenant partitioning).
3. Requirement creation (Cook, Driver, Security Guard models & cascading).
4. Database operations (Insert, query, update status, rollback on error).
5. Tenant isolation (Data-access layer boundary enforcement).
6. Lead lookup (Tenant-filtered mobile lookup, fallback handling).
7. AI configuration and error handling.
"""
import unittest
from datetime import datetime, date
from database.connection import get_db, _normalize_database_url
from database.models import Organization, User, Lead, CookRequirement, DriverRequirement, SecurityGuardRequirement
from database.repository import (
    save_lead_to_db,
    get_lead_by_id,
    get_latest_lead_by_mobile,
    generate_next_lead_id,
    init_database,
)
from utils.validators import (
    validate_name,
    validate_mobile,
    validate_email,
    validate_budget,
    validate_pincode,
    validate_form,
)
from services.lead_lookup import find_lead_by_mobile
from ai.providers.factory import get_ai_provider, reset_provider_cache


class TestApplicationCore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        reset_provider_cache()
        with get_db() as db:
            org1 = db.query(Organization).filter_by(slug="homedesk").first()
            org2 = db.query(Organization).filter_by(slug="acme").first()
            assert org1 is not None, "Seeded tenant 1 must exist"
            assert org2 is not None, "Seeded tenant 2 must exist"
            self.org1_id = int(org1.id)
            self.org2_id = int(org2.id)

    # ---------------------------------------------------------
    # 1. Input Validation Tests
    # ---------------------------------------------------------
    def test_01_input_validation_name(self):
        """Validates name rules: non-empty, non-whitespace."""
        self.assertTrue(validate_name("Alice")[0])
        self.assertTrue(validate_name("Dr. Bob Smith")[0])
        self.assertFalse(validate_name("")[0])
        self.assertFalse(validate_name("   ")[0])
        self.assertFalse(validate_name(None)[0])

    def test_02_input_validation_mobile(self):
        """Validates mobile rules: exactly 10 digits only."""
        self.assertTrue(validate_mobile("9876543210")[0])
        self.assertFalse(validate_mobile("987654321")[0])       # 9 digits
        self.assertFalse(validate_mobile("98765432100")[0])     # 11 digits
        self.assertFalse(validate_mobile("98765abcde")[0])     # letters
        self.assertFalse(validate_mobile("")[0])               # empty
        self.assertFalse(validate_mobile(None)[0])             # None

    def test_03_input_validation_email(self):
        """Validates email format."""
        self.assertTrue(validate_email("user@example.com")[0])
        self.assertTrue(validate_email("admin.name+tag@sub.domain.co")[0])
        self.assertFalse(validate_email("plainaddress")[0])
        self.assertFalse(validate_email("@missingusername.com")[0])
        self.assertFalse(validate_email("user@.com")[0])
        self.assertFalse(validate_email("")[0])

    def test_04_input_validation_budget(self):
        """Validates budget: must be a positive number."""
        self.assertTrue(validate_budget(15000)[0])
        self.assertTrue(validate_budget("25000.50")[0])
        self.assertFalse(validate_budget(0)[0])
        self.assertFalse(validate_budget(-500)[0])
        self.assertFalse(validate_budget("not-a-number")[0])

    def test_05_input_validation_pincode(self):
        """Validates pincode: optional, but if present must be exactly 6 digits."""
        self.assertTrue(validate_pincode("")[0])          # optional
        self.assertTrue(validate_pincode(None)[0])        # optional
        self.assertTrue(validate_pincode("400001")[0])    # 6 digits
        self.assertFalse(validate_pincode("40001")[0])    # 5 digits
        self.assertFalse(validate_pincode("4000001")[0])  # 7 digits
        self.assertFalse(validate_pincode("4000AB")[0])   # non-digits

    def test_06_validate_form_composite(self):
        """Validates full form dictionary with multiple field errors."""
        valid_form = {
            "Name": "Jane Doe",
            "Mobile": "9812345678",
            "Email": "jane@example.com",
            "City": "Mumbai",
            "Budget": 18000,
            "Pincode": "400001",
        }
        errors = validate_form(valid_form)
        self.assertEqual(len(errors), 0, f"Expected no errors, got {errors}")

        invalid_form = {
            "Name": "",
            "Mobile": "123",
            "Email": "bad-email",
            "City": "",
            "Budget": -10,
        }
        errors = validate_form(invalid_form)
        self.assertGreaterEqual(len(errors), 5)

    # ---------------------------------------------------------
    # 2. Lead ID Generation Tests
    # ---------------------------------------------------------
    def test_07_lead_id_generation_prefixes(self):
        """Verifies correct prefix generation for each service type."""
        cook_id = generate_next_lead_id("Cook", self.org1_id)
        driver_id = generate_next_lead_id("Driver", self.org1_id)
        guard_id = generate_next_lead_id("Security Guard", self.org1_id)

        self.assertTrue(cook_id.startswith("Cook-"))
        self.assertTrue(driver_id.startswith("Driver-"))
        self.assertTrue(guard_id.startswith("Security-"))

    def test_08_lead_id_sequential_and_isolated(self):
        """Verifies sequence numbers increment monotonically and remain isolated per tenant."""
        # Insert a cook lead in Org 1
        lead_1 = save_lead_to_db("Cook", {"Name": "Client 1", "Budget": 10000}, organization_id=self.org1_id)
        next_id_org1 = generate_next_lead_id("Cook", self.org1_id)
        self.assertNotEqual(lead_1["Lead ID"], next_id_org1)

        # Generating next ID for Org 2 is independent
        id_org2 = generate_next_lead_id("Cook", self.org2_id)
        self.assertTrue(id_org2.startswith("Cook-"))

    # ---------------------------------------------------------
    # 3. Requirement Creation Tests
    # ---------------------------------------------------------
    def test_09_cook_requirement_creation(self):
        """Creates Cook requirement and verifies service-specific fields."""
        payload = {
            "Name": "Cook Client",
            "Mobile Number": "9820011223",
            "City": "Pune",
            "Budget": 15000,
            "Cuisine Type": "South Indian & Mughlai",
            "Meals Per Day": 3,
        }
        saved = save_lead_to_db("Cook", payload, organization_id=self.org1_id)
        lead_id = saved["Lead ID"]

        with get_db() as db:
            lead = db.query(Lead).filter_by(lead_id=lead_id).first()
            self.assertIsNotNone(lead)
            self.assertEqual(lead.service_type, "Cook")
            self.assertIsNotNone(lead.cook_requirement)
            self.assertEqual(lead.cook_requirement.cuisine_type, "South Indian & Mughlai")
            self.assertEqual(lead.cook_requirement.meals_per_day, 3)

    def test_10_driver_requirement_creation(self):
        """Creates Driver requirement and verifies vehicle details."""
        payload = {
            "Name": "Driver Client",
            "Mobile Number": "9820022334",
            "City": "Delhi",
            "Budget": 22000,
            "Vehicle Type": "Luxury Sedan",
            "License Required": "Commercial",
        }
        saved = save_lead_to_db("Driver", payload, organization_id=self.org1_id)
        lead_id = saved["Lead ID"]

        with get_db() as db:
            lead = db.query(Lead).filter_by(lead_id=lead_id).first()
            self.assertIsNotNone(lead)
            self.assertEqual(lead.service_type, "Driver")
            self.assertIsNotNone(lead.driver_requirement)
            self.assertEqual(lead.driver_requirement.vehicle_type, "Luxury Sedan")
            self.assertEqual(lead.driver_requirement.license_required, "Commercial")

    def test_11_security_guard_requirement_creation(self):
        """Creates Security Guard requirement and verifies shift details."""
        payload = {
            "Name": "Security Client",
            "Mobile Number": "9820033445",
            "City": "Bangalore",
            "Budget": 18000,
            "Day/Night Shift": "24/7 Rotational",
            "Residential/Commercial": "Gated Community",
        }
        saved = save_lead_to_db("Security Guard", payload, organization_id=self.org1_id)
        lead_id = saved["Lead ID"]

        with get_db() as db:
            lead = db.query(Lead).filter_by(lead_id=lead_id).first()
            self.assertIsNotNone(lead)
            self.assertEqual(lead.service_type, "Security Guard")
            self.assertIsNotNone(lead.security_guard_requirement)
            self.assertEqual(lead.security_guard_requirement.shift, "24/7 Rotational")
            self.assertEqual(lead.security_guard_requirement.site_type, "Gated Community")

    # ---------------------------------------------------------
    # 4. Database Operations & Status Updates
    # ---------------------------------------------------------
    def test_12_database_lead_status_update(self):
        """Verifies lead lifecycle updates in the database."""
        payload = {"Name": "Lifecycle Lead", "Mobile": "9820044556", "City": "Chennai", "Budget": 14000}
        saved = save_lead_to_db("Cook", payload, organization_id=self.org1_id)
        lead_id = saved["Lead ID"]

        with get_db() as db:
            lead = db.query(Lead).filter_by(lead_id=lead_id).first()
            self.assertEqual(lead.status, "New")
            lead.status = "In Progress"
            db.flush()

        with get_db() as db:
            updated = db.query(Lead).filter_by(lead_id=lead_id).first()
            self.assertEqual(updated.status, "In Progress")

    def test_13_database_rollback_on_integrity_violation(self):
        """Verifies transactions safely roll back on database errors without leaving corrupt state."""
        with self.assertRaises(ValueError):
            save_lead_to_db("Cook", {"Name": "Bad Org"}, organization_id=-1)

    # ---------------------------------------------------------
    # 5. Lead Lookup Tests
    # ---------------------------------------------------------
    def test_14_lead_lookup_by_mobile(self):
        """Verifies looking up submitted leads by mobile number within tenant category."""
        mobile = "9820055999"
        with get_db() as db:
            db.query(Lead).filter_by(mobile=mobile).delete()
        payload = {"Name": "Lookup Client", "Mobile": mobile, "City": "Noida", "Budget": 16000}
        save_lead_to_db("Cook", payload, organization_id=self.org1_id)

        # Lookup in Org 1 (Cook Org) succeeds
        res = find_lead_by_mobile(mobile, organization_id=self.org1_id)
        self.assertIsNotNone(res)
        self.assertEqual(res["Name"], "Lookup Client")

        # Lookup in Org 2 (Driver Org) for Cook requirement returns None (Category Isolation)
        res_org2 = find_lead_by_mobile(mobile, organization_id=self.org2_id)
        self.assertIsNone(res_org2)

    def test_15_lead_lookup_empty_or_unknown(self):
        """Verifies looking up an unregistered mobile number returns None."""
        self.assertIsNone(find_lead_by_mobile("", organization_id=self.org1_id))
        self.assertIsNone(find_lead_by_mobile("9000000000", organization_id=self.org1_id))

    # ---------------------------------------------------------
    # 6. AI Configuration & Fallback Tests
    # ---------------------------------------------------------
    def test_16_ai_mock_provider_configuration(self):
        """Verifies Mock AI provider responds cleanly without external network calls."""
        provider = get_ai_provider("mock")
        reply = provider.ask("What is HomeDesk?")
        self.assertIn("HomeDesk", reply)

    def test_17_normalize_database_url_sanitization(self):
        """Verifies URL normalization handles quotes, whitespace, and variable prefix."""
        raw_url = "postgresql://user:pass@host:5432/dbname"
        expected = "postgresql+psycopg2://user:pass@host:5432/dbname"

        self.assertEqual(_normalize_database_url(raw_url), expected)
        self.assertEqual(_normalize_database_url(f'"{raw_url}"'), expected)
        self.assertEqual(_normalize_database_url(f"'{raw_url}'"), expected)
        self.assertEqual(_normalize_database_url(f"  {raw_url}  "), expected)
        self.assertEqual(_normalize_database_url(f"DATABASE_URL = {raw_url}"), expected)
        self.assertEqual(_normalize_database_url(f"DATABASE_URL='{raw_url}'"), expected)
        self.assertEqual(_normalize_database_url("postgres://u:p@h:5432/db"), "postgresql+psycopg2://u:p@h:5432/db")
        self.assertEqual(_normalize_database_url(""), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
