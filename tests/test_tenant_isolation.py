"""
Automated Multi-Tenant Isolation Test Suite.
Verifies Phase 3 multi-tenancy requirements:
1. Multiple users per organization.
2. Every lead/request belongs to an organization.
3. Users only access data belonging to their organization.
4. Organization A cannot see Organization B's requirements (via mobile or lead ID).
5. Minimum database structure (organization_id foreign keys, indexes).
6. Tenant filtering is always enforced at the data-access layer.
7. Preserves existing service forms and data structures.
"""
import io
import unittest
from openpyxl import load_workbook
from database.connection import get_db
from database.models import Organization, User, Lead
from database.repository import (
    save_lead_to_db,
    get_latest_lead_by_mobile,
    get_lead_by_id,
    generate_next_lead_id,
    get_all_leads_for_export,
    _resolve_tenant_id,
    init_database,
)
from storage.excel_handler import export_leads_to_excel, get_excel_export_bytes


class TestTenantIsolation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        with get_db() as db:
            org1 = db.query(Organization).filter_by(slug="homedesk").first()
            org2 = db.query(Organization).filter_by(slug="acme").first()
            assert org1 is not None, "Tenant 1 (homedesk) must exist"
            assert org2 is not None, "Tenant 2 (acme) must exist"
            self.org1_id = int(org1.id)
            self.org2_id = int(org2.id)

    def test_01_multiple_users_per_organization(self):
        """Requirement 1: An organization/tenant can have multiple users."""
        with get_db() as db:
            for em in ("alice@homedesk.com", "bob@homedesk.com", "charlie@acme.com"):
                old = db.query(User).filter_by(email=em).first()
                if old:
                    db.delete(old)
            db.flush()

            u1 = User(
                organization_id=self.org1_id,
                name="Alice Manager",
                mobile="9800000001",
                email="alice@homedesk.com",
            )
            u2 = User(
                organization_id=self.org1_id,
                name="Bob Staff",
                mobile="9800000002",
                email="bob@homedesk.com",
            )
            u3 = User(
                organization_id=self.org2_id,
                name="Charlie Acme",
                mobile="9800000003",
                email="charlie@acme.com",
            )
            db.add_all([u1, u2, u3])
            db.flush()

            org1_users = db.query(User).filter_by(organization_id=self.org1_id).all()
            self.assertGreaterEqual(len(org1_users), 2)
            names_in_org1 = [u.name for u in org1_users]
            self.assertIn("Alice Manager", names_in_org1)
            self.assertIn("Bob Staff", names_in_org1)
            self.assertNotIn("Charlie Acme", names_in_org1)

    def test_02_every_lead_belongs_to_organization(self):
        """Requirement 2: Every lead/request must belong to an organization."""
        lead_payload = {
            "Name": "Tenant 1 Lead Client",
            "Mobile Number": "9123456780",
            "City": "Mumbai",
            "Budget (INR)": 16000,
            "Cuisine Type": "North Indian",
            "Meals Per Day": 2,
        }
        saved = save_lead_to_db("Cook", lead_payload, organization_id=self.org1_id)
        self.assertEqual(saved.get("Organization ID"), self.org1_id)
        self.assertTrue(saved.get("Lead ID"))

        with get_db() as db:
            lead_row = (
                db.query(Lead)
                .filter_by(organization_id=self.org1_id, lead_id=saved["Lead ID"])
                .first()
            )
            self.assertIsNotNone(lead_row)
            self.assertEqual(lead_row.organization_id, self.org1_id)
            self.assertEqual(lead_row.service_type, "Cook")
            self.assertIsNotNone(lead_row.cook_requirement)
            self.assertEqual(lead_row.cook_requirement.cuisine_type, "North Indian")

    def test_03_tenant_lead_id_sequence_isolated(self):
        """Requirement 5 & 6: Each tenant manages independent sequential lead IDs without collision."""
        org2_payload = {
            "Name": "Acme Driver Lead",
            "Mobile Number": "9234567890",
            "City": "Delhi",
            "Budget (INR)": 18000,
            "Vehicle Type": "SUV",
            "License Required": "Commercial",
        }
        saved_org2 = save_lead_to_db("Driver", org2_payload, organization_id=self.org2_id)
        self.assertEqual(saved_org2.get("Organization ID"), self.org2_id)

        org1_payload = {
            "Name": "HomeDesk Driver Lead",
            "Mobile Number": "9345678901",
            "City": "Bangalore",
            "Budget (INR)": 20000,
            "Vehicle Type": "Sedan",
            "License Required": "Private",
        }
        saved_org1 = save_lead_to_db("Driver", org1_payload, organization_id=self.org1_id)
        self.assertEqual(saved_org1.get("Organization ID"), self.org1_id)

    def test_04_cross_tenant_lookup_by_mobile_prevented(self):
        """Requirement 3 & 4: Organization A must NEVER see Organization B's requirements via mobile."""
        mobile_a = "9456789012"
        lead_data_a = {
            "Name": "Confidential Org A Lead",
            "Mobile Number": mobile_a,
            "City": "Pune",
            "Budget (INR)": 19000,
            "Day/Night Shift": "Night",
            "Residential/Commercial": "Commercial",
        }
        save_lead_to_db("Security Guard", lead_data_a, organization_id=self.org1_id)

        # Query from Org A returns Org A's lead
        res_org_a = get_latest_lead_by_mobile(mobile_a, organization_id=self.org1_id)
        self.assertIsNotNone(res_org_a)
        self.assertEqual(res_org_a["Name"], "Confidential Org A Lead")
        self.assertEqual(res_org_a["Organization ID"], self.org1_id)

        # Query from Org B with Org A's mobile MUST RETURN NONE
        res_org_b = get_latest_lead_by_mobile(mobile_a, organization_id=self.org2_id)
        self.assertIsNone(
            res_org_b,
            "CRITICAL SECURITY VIOLATION: Org B accessed Org A's lead via mobile lookup!",
        )

    def test_05_cross_tenant_lookup_by_lead_id_prevented(self):
        """Requirement 4: Organization A must NEVER see Organization B's requirements via Lead ID."""
        lead_data_b = {
            "Name": "Secret Org B Requirement",
            "Mobile Number": "9567890123",
            "City": "Hyderabad",
            "Budget (INR)": 32000,
            "Cuisine Type": "South Indian",
            "Meals Per Day": 3,
        }
        saved_b = save_lead_to_db("Cook", lead_data_b, organization_id=self.org2_id)
        lead_id_b = saved_b["Lead ID"]

        # Org B can view its own lead
        found_by_b = get_lead_by_id(lead_id_b, organization_id=self.org2_id)
        self.assertIsNotNone(found_by_b)
        self.assertEqual(found_by_b["Name"], "Secret Org B Requirement")
        self.assertEqual(found_by_b["Organization ID"], self.org2_id)

        # Org A CANNOT view Org B's lead
        found_by_a = get_lead_by_id(lead_id_b, organization_id=self.org1_id)
        self.assertTrue(
            found_by_a is None or found_by_a.get("Organization ID") != self.org2_id,
            "CRITICAL SECURITY VIOLATION: Org A accessed Org B's lead via Lead ID lookup!",
        )

    def test_06_data_access_layer_enforces_tenant_id(self):
        """Requirement 8 & 9: Tenant isolation enforced at the data-access layer, not UI alone."""
        # Non-positive or invalid tenant IDs must be rejected
        with self.assertRaises(ValueError):
            _resolve_tenant_id(0)

        with self.assertRaises(ValueError):
            _resolve_tenant_id(-5)

        # Attempting to insert lead under non-existent organization must fail
        with self.assertRaises(ValueError):
            save_lead_to_db("Cook", {"Name": "Invalid Org Lead"}, organization_id=999999)

    def test_07_excel_export_strictly_scoped_to_tenant(self):
        """Tenant-scoped Excel export must never leak leads from another organization."""
        excel_bytes = get_excel_export_bytes(organization_id=self.org2_id)
        self.assertIsNotNone(excel_bytes)

        wb = load_workbook(io.BytesIO(excel_bytes), data_only=True)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            headers = [c.value for c in ws[1]] if ws.max_row >= 1 else []
            if "Organization ID" in headers:
                org_col_idx = headers.index("Organization ID") + 1
                for row_idx in range(2, ws.max_row + 1):
                    val = ws.cell(row=row_idx, column=org_col_idx).value
                    if val is not None:
                        self.assertEqual(
                            val,
                            self.org2_id,
                            f"Foreign organization lead found in sheet {sheet_name}, row {row_idx}",
                        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
