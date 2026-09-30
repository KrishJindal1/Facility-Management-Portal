"""
Automated Test Suite for FastAPI Backend Endpoints.
Verifies all REST API routes serving the React frontend.
"""
import unittest
from fastapi.testclient import TestClient
from api.main import app
from database.repository import init_database


class TestFastAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()
        cls.client = TestClient(app)

    def test_01_get_tenants(self):
        """Verifies listing tenants and fetching by slug."""
        res = self.client.get("/api/tenants")
        self.assertEqual(res.status_code, 200)
        tenants = res.json()
        self.assertGreaterEqual(len(tenants), 2)
        slugs = [t["slug"] for t in tenants]
        self.assertIn("homedesk", slugs)

        # Single tenant fetch
        res_single = self.client.get("/api/tenants/homedesk")
        self.assertEqual(res_single.status_code, 200)
        self.assertEqual(res_single.json()["slug"], "homedesk")

    def test_02_auth_login_valid_and_invalid(self):
        """Verifies login authentication endpoint."""
        # Valid login with seeded admin
        res_valid = self.client.post("/api/auth/login", json={
            "email": "admin@homedesk.com",
            "password": "Password123!",
        })
        self.assertEqual(res_valid.status_code, 200)
        self.assertIn("user", res_valid.json())
        self.assertEqual(res_valid.json()["user"]["email"], "admin@homedesk.com")

        # Invalid login
        res_invalid = self.client.post("/api/auth/login", json={
            "email": "admin@homedesk.com",
            "password": "WrongPassword999",
        })
        self.assertEqual(res_invalid.status_code, 401)

    def test_03_lead_submission_and_lookup(self):
        """Verifies requirement submission and tenant-scoped lookup."""
        mobile = "9820099887"
        payload = {
            "service_name": "Cook",
            "organization_id": 1,
            "data": {
                "Name": "API Test Client",
                "Mobile": mobile,
                "Email": "apitest@example.com",
                "City": "Mumbai",
                "Budget": 16000,
                "Cuisine Type": "North Indian",
                "Meals Per Day": 2,
            },
        }
        res_submit = self.client.post("/api/leads", json=payload)
        self.assertEqual(res_submit.status_code, 201)
        lead = res_submit.json()["lead"]
        self.assertTrue(lead["Lead ID"].startswith("Cook-"))

        # Lookup by mobile within Org 1
        res_lookup = self.client.get(f"/api/leads/lookup?mobile={mobile}&organization_id=1")
        self.assertEqual(res_lookup.status_code, 200)
        self.assertEqual(res_lookup.json()["Name"], "API Test Client")

        # Lookup in Org 2 returns 404 (tenant isolation)
        res_lookup_org2 = self.client.get(f"/api/leads/lookup?mobile={mobile}&organization_id=2")
        self.assertEqual(res_lookup_org2.status_code, 404)

    def test_04_chat_endpoint(self):
        """Verifies AI Chat endpoint responses."""
        res = self.client.post("/api/chat", json={"message": "hello"})
        self.assertEqual(res.status_code, 200)
        reply = res.json()["reply"]
        self.assertIn("HomeDesk", reply)

    def test_05_health_endpoint(self):
        """Verifies health endpoint returns system diagnostic report."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertIn("checks", data)

    def test_06_excel_export_endpoint(self):
        """Verifies binary Excel export endpoint."""
        res = self.client.get("/api/leads/export?organization_id=1")
        self.assertEqual(res.status_code, 200)
        self.assertIn("spreadsheetml", res.headers.get("content-type", ""))
        self.assertGreater(len(res.content), 100)

    def test_07_frontend_index_serving(self):
        """Verifies FastAPI serves the React index.html when dist exists."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("HomeDesk", res.text)
        self.assertIn("root", res.text)


if __name__ == "__main__":
    unittest.main()
