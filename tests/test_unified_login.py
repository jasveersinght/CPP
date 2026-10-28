import unittest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from werkzeug.security import generate_password_hash

class TestUnifiedLogin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create app without starting external dependencies
        with patch('database.db.ensure_schema_compatibility'), \
             patch('services.reconciliation_service.ReconciliationService.reconcile_expired_auctions'), \
             patch('services.reconciliation_service.AuctionWatchdog.start_watchdog'):
            cls.app, cls.socketio = create_app()
            cls.app.config['TESTING'] = True

    def setUp(self):
        self.client = self.app.test_client()

    def test_root_redirects_to_login(self):
        """Root / should redirect unauthenticated users to /login."""
        resp = self.client.get('/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.headers['Location'])

    def test_login_page_renders_both_tabs(self):
        """GET /login should display the unified portal with both Team and Admin options."""
        resp = self.client.get('/login')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Team Login', resp.data)
        self.assertIn(b'Admin Login', resp.data)
        self.assertIn(b'tab-btn-team', resp.data)
        self.assertIn(b'tab-btn-host', resp.data)
        self.assertIn(b'section-team-login', resp.data)
        self.assertIn(b'section-host-login', resp.data)

    def test_login_page_with_host_role(self):
        """GET /login?role=host should render with host tab active."""
        resp = self.client.get('/login?role=host')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Admin Control Room', resp.data)

    @patch('routes.auth.fetch_one')
    def test_unified_login_team_success(self, mock_fetch):
        """Submitting team credentials to /login should authenticate and redirect to team dashboard."""
        mock_fetch.return_value = {
            'id': 1,
            'team_code': 'TEAM001',
            'team_name': 'Alpha Squad',
            'password_hash': generate_password_hash('Secret123'),
            'is_active': 1,
            'is_disqualified': 0
        }
        resp = self.client.post('/login', data={
            'role': 'team',
            'team_code': 'TEAM001',
            'password': 'Secret123'
        }, follow_redirects=False)

        self.assertEqual(resp.status_code, 302)
        self.assertIn('/team/dashboard', resp.headers['Location'])

    @patch('routes.auth.fetch_one')
    def test_unified_login_host_success(self, mock_fetch):
        """Submitting host credentials to /login should authenticate and redirect to host dashboard."""
        mock_fetch.return_value = {
            'id': 1,
            'username': 'admin',
            'password_hash': generate_password_hash('AdminPass!'),
            'role': 'superadmin'
        }
        resp = self.client.post('/login', data={
            'role': 'host',
            'username': 'admin',
            'password': 'AdminPass!'
        }, follow_redirects=False)

        self.assertEqual(resp.status_code, 302)
        self.assertIn('/host/dashboard', resp.headers['Location'])

    @patch('routes.auth.fetch_one')
    def test_unified_login_auto_infer_role(self, mock_fetch):
        """If role is omitted, username field infers host role."""
        mock_fetch.return_value = {
            'id': 1,
            'username': 'admin',
            'password_hash': generate_password_hash('AdminPass!')
        }
        resp = self.client.post('/login', data={
            'username': 'admin',
            'password': 'AdminPass!'
        }, follow_redirects=False)

        self.assertEqual(resp.status_code, 302)
        self.assertIn('/host/dashboard', resp.headers['Location'])

    @patch('routes.auth.fetch_one')
    def test_unified_login_invalid_password(self, mock_fetch):
        """Invalid credentials on /login should render error message."""
        mock_fetch.return_value = {
            'id': 1,
            'team_code': 'TEAM001',
            'team_name': 'Alpha Squad',
            'password_hash': generate_password_hash('RealPass'),
            'is_active': 1,
            'is_disqualified': 0
        }
        resp = self.client.post('/login', data={
            'role': 'team',
            'team_code': 'TEAM001',
            'password': 'WrongPassword'
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Invalid Team Code or Password', resp.data)

    def test_logout_redirects_to_login(self):
        """Logout should clear session and redirect to /login."""
        with self.client.session_transaction() as sess:
            sess['user_type'] = 'team'
            sess['team_id'] = 1
        resp = self.client.get('/logout', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.headers['Location'])

if __name__ == '__main__':
    unittest.main()
