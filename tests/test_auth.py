import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database.init_db import init_database, seed_database
from database.db import fetch_one

class TestAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()
        seed_database()
        cls.app, cls.socketio = create_app()
        cls.app.config['TESTING'] = True

    def setUp(self):
        self.client = self.app.test_client()

    def test_01_team_login_success(self):
        """Valid team login should set session and redirect to team dashboard."""
        resp = self.client.post('/team/login', data={
            'team_code': 'TEAM001',
            'password': 'TEST@123'
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/team/dashboard', resp.headers['Location'])

    def test_02_team_login_invalid_password(self):
        """Invalid password should fail and display error."""
        resp = self.client.post('/team/login', data={
            'team_code': 'TEAM001',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Invalid Team Code or Password', resp.data)

    def test_03_host_login_success(self):
        """Valid host login should set session and redirect to host dashboard."""
        resp = self.client.post('/host/login', data={
            'username': 'admin',
            'password': 'host123'
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/host/dashboard', resp.headers['Location'])

    def test_04_host_login_invalid_username(self):
        """Non-existent host username should fail."""
        resp = self.client.post('/host/login', data={
            'username': 'nonexistent',
            'password': 'any'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Invalid Host Username or Password', resp.data)

    def test_05_unauthorized_dashboard_access(self):
        """Anonymous user cannot access team or host dashboard."""
        anon_client = self.app.test_client()
        resp_team = anon_client.get('/team/dashboard', follow_redirects=False)
        self.assertEqual(resp_team.status_code, 302)
        self.assertIn('/team/login', resp_team.headers['Location'])

        resp_host = anon_client.get('/host/dashboard', follow_redirects=False)
        self.assertEqual(resp_host.status_code, 302)
        self.assertIn('/host/login', resp_host.headers['Location'])

    def test_06_team_cannot_access_host_dashboard(self):
        """Logged-in team cannot access host-only dashboard."""
        team_client = self.app.test_client()
        team_client.post('/team/login', data={'team_code': 'TEAM001', 'password': 'TEST@123'})
        resp = team_client.get('/host/dashboard', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/host/login', resp.headers['Location'])

if __name__ == '__main__':
    unittest.main()
