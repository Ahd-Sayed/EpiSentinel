import unittest
import os
import sys

# Ensure project root is in system path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.scenario import ScenarioDim
from app.services.dashboard_service import DashboardService
from app.services.auth_service import AuthService

class TestEpiGuardApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize app with standard configuration
        cls.app = create_app()
        cls.app.config["LOGIN_DISABLED"] = False
        cls.app.config["WTF_CSRF_ENABLED"] = False
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()


    def setUp(self):
        self.client = self.app.test_client()
        self.client.get("/logout")

    def test_database_models(self):
        """Test database connection and scenario records count"""
        scenarios_count = ScenarioDim.query.count()
        self.assertEqual(scenarios_count, 12, "Should find exactly 12 validation scenarios in SQLite")

    def test_dashboard_service(self):
        """Test Dashboard Service aggregations"""
        metrics = DashboardService.get_overview_data()
        self.assertIn("kpis", metrics)
        self.assertIn("donut", metrics)
        self.assertIn("lead_time", metrics)
        self.assertIn("precision", metrics)
        self.assertEqual(metrics["kpis"]["scenarios_detected"], "12 / 12", "Sensitivity count must be 100%")

    def test_user_authentication(self):
        """Test password verification and role permissions"""
        admin_user = User.query.filter_by(username="admin").first()
        self.assertIsNotNone(admin_user, "Admin user must be seeded in database")
        self.assertTrue(admin_user.check_password("admin123"), "Verification of seeded admin password failed")
        self.assertTrue(admin_user.has_role("Admin"))
        self.assertTrue(admin_user.has_role("Researcher"))
        
        viewer_user = User.query.filter_by(username="viewer").first()
        self.assertTrue(viewer_user.check_password("viewer123"))
        self.assertFalse(viewer_user.has_role("Admin"), "Viewer must not have Admin rights")

    def test_unauthorized_endpoints(self):
        """Verify endpoints are protected by login_required redirecting to login"""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 302, "Home dashboard must require login session")
        self.assertTrue("login" in res.headers.get("Location", "").lower())
        
        # API endpoints return 401 JSON format on unauthorized calls
        api_res = self.client.get("/api/overview")
        self.assertEqual(api_res.status_code, 401, "API route must return 401 on unauthorized access")
        json_data = api_res.get_json()
        self.assertFalse(json_data["success"], "Unauthorized response must indicate failure")

    def test_explorer_alerts_format(self):
        """Verify /api/data/alerts structure"""
        self.client.post("/login", data={"username": "admin", "password": "admin123"})
        res = self.client.get("/api/data/alerts?page=1")
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data["success"])
        self.assertIn("data", json_data["data"])
        self.assertEqual(json_data["data"]["page"], 1)

    def test_models_summary_format(self):
        """Verify /api/models/summary structure"""
        self.client.post("/login", data={"username": "admin", "password": "admin123"})
        res = self.client.get("/api/models/summary")
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data["success"])
        self.assertIn("models", json_data["data"])
        self.assertIn("precision", json_data["data"])

    def test_heatmap_format(self):
        """Verify /api/alerts/heatmap structure"""
        self.client.post("/login", data={"username": "admin", "password": "admin123"})
        res = self.client.get("/api/alerts/heatmap?disease=all")
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data["success"])
        self.assertIn("cities", json_data["data"])
        self.assertIn("months", json_data["data"])

    def test_api_history_and_warnings(self):
        """Test API endpoints /api/history and check responses"""
        self.client.post("/login", data={"username": "admin", "password": "admin123"})
        res = self.client.get("/api/history")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["data"], list)

    def test_api_predict_missing_file(self):
        """Test API /api/predict handles missing file input"""
        self.client.post("/login", data={"username": "researcher", "password": "research123"})
        res = self.client.post("/api/predict")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("No file part", data["message"])

    def test_api_unauthorized_role(self):
        """Test user role authorization restrictions"""
        self.client.post("/login", data={"username": "viewer", "password": "viewer123"})
        res = self.client.post("/api/predict")
        self.assertEqual(res.status_code, 403)

if __name__ == "__main__":
    unittest.main()

