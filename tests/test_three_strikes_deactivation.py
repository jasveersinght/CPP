import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database.init_db import init_database, seed_database
from database.db import fetch_one, db_transaction
from services.anticheat_service import AntiCheatService
from services.auction_service import AuctionService
from services.answer_service import AnswerService

class TestThreeStrikesDeactivation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()
        seed_database()
        cls.app, cls.socketio = create_app()
        cls.app.config['TESTING'] = True

    def setUp(self):
        self.client = self.app.test_client()

    def _login_team(self, client, team_code='TEAM010', password='TEST@123'):
        resp = client.post('/team/login', data={
            'team_code': team_code,
            'password': password
        }, follow_redirects=False)
        return resp

    def _login_host(self, client, username='admin', password='host123'):
        resp = client.post('/host/login', data={
            'username': username,
            'password': password
        }, follow_redirects=False)
        return resp

    def _set_team_session(self, client, team):
        with client.session_transaction() as sess:
            sess['user_type'] = 'team'
            sess['team_id'] = team['id']
            sess['team_code'] = team['team_code']
            sess['team_name'] = team['team_name']

    def test_01_first_violation_strike_1_warning(self):
        """Scenario 1: First fullscreen exit -> Strike 1 warning, not disqualified."""
        client = self.app.test_client()
        self._login_team(client, 'TEAM010')

        resp = client.post('/api/team/violation', json={
            'violation_type': 'FULLSCREEN_EXIT',
            'details': 'Participant exited fullscreen mode'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        v = data['violation']
        self.assertEqual(v['strike_count'], 1)
        self.assertFalse(v['is_disqualified'])

        team = fetch_one("SELECT violation_count, is_disqualified FROM teams WHERE team_code = 'TEAM010'")
        self.assertEqual(team['violation_count'], 1)
        self.assertFalse(bool(team['is_disqualified']))

    def test_02_second_violation_strike_2_warning(self):
        """Scenario 2: Second fullscreen exit -> Strike 2 warning, not disqualified."""
        team = fetch_one("SELECT id, team_code, team_name FROM teams WHERE team_code = 'TEAM010'")
        client = self.app.test_client()
        self._set_team_session(client, team)

        resp = client.post('/api/team/violation', json={
            'violation_type': 'FULLSCREEN_EXIT',
            'details': 'Participant exited fullscreen mode again'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        v = data['violation']
        self.assertEqual(v['strike_count'], 2)
        self.assertFalse(v['is_disqualified'])

        team = fetch_one("SELECT violation_count, is_disqualified FROM teams WHERE team_code = 'TEAM010'")
        self.assertEqual(team['violation_count'], 2)
        self.assertFalse(bool(team['is_disqualified']))

    def test_03_third_violation_automatic_disqualification(self):
        """Scenario 3: Third fullscreen exit -> Automatic disqualification (is_disqualified=True)."""
        team = fetch_one("SELECT id, team_code, team_name FROM teams WHERE team_code = 'TEAM010'")
        client = self.app.test_client()
        self._set_team_session(client, team)

        resp = client.post('/api/team/violation', json={
            'violation_type': 'FULLSCREEN_EXIT',
            'details': 'Participant exited fullscreen 3rd time'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        v = data['violation']
        self.assertEqual(v['strike_count'], 3)
        self.assertTrue(v['is_disqualified'])

        team = fetch_one("SELECT violation_count, is_disqualified FROM teams WHERE team_code = 'TEAM010'")
        self.assertEqual(team['violation_count'], 3)
        self.assertTrue(bool(team['is_disqualified']))

    def test_04_disqualified_team_cannot_bid(self):
        """Scenario 4: Disqualified team cannot bid (HTTP API and Service both reject)."""
        # Start a live auction first
        active = AuctionService.get_active_auction()
        if not active:
            avail_q = fetch_one("SELECT id FROM questions WHERE status = 'AVAILABLE' LIMIT 1")
            auction_id = AuctionService.start_auction(avail_q['id'])
        else:
            auction_id = active['id']

        team = fetch_one("SELECT id, team_code, team_name FROM teams WHERE team_code = 'TEAM010'")
        client = self.app.test_client()
        self._set_team_session(client, team)

        resp = client.post('/api/team/bid', json={'auction_id': auction_id})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['success'])
        self.assertIn('disqualified', data['error'].lower())

        # Also direct service call must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            AuctionService.place_bid(auction_id, team['id'])
        self.assertIn('disqualified', str(ctx.exception).lower())

    def test_05_disqualified_team_cannot_submit_answers(self):
        """Scenario 5: Disqualified team cannot submit answers."""
        team = fetch_one("SELECT id, team_code, team_name FROM teams WHERE team_code = 'TEAM010'")
        avail_q = fetch_one("SELECT id, correct_answer FROM questions WHERE status = 'AVAILABLE' LIMIT 1")

        with db_transaction() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO auctions (question_id, starting_bid, current_bid, current_bidder_id,
                                      winner_team_id, status, started_at, ends_at)
                VALUES (%s, 500, 500, %s, %s, 'ENDED', NOW(), NOW())
                """,
                (avail_q['id'], team['id'], team['id'])
            )
            fake_auction_id = cursor.lastrowid

        client = self.app.test_client()
        self._set_team_session(client, team)

        resp = client.post('/api/team/submit-answer', json={
            'auction_id': fake_auction_id,
            'answer': str(avail_q['correct_answer'])
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['success'])
        self.assertIn('disqualified', data['error'].lower())

        # Direct service call must also fail
        with self.assertRaises(ValueError) as ctx:
            AnswerService.submit_answer(fake_auction_id, team['id'], str(avail_q['correct_answer']))
        self.assertIn('disqualified', str(ctx.exception).lower())

    def test_06_refresh_and_relogin_cannot_bypass_disqualification(self):
        """Scenario 6: Refreshing state or logging in again does not remove disqualification."""
        team = fetch_one("SELECT id, team_code, team_name FROM teams WHERE team_code = 'TEAM010'")
        client = self.app.test_client()
        self._set_team_session(client, team)

        # 1. State check reflects is_disqualified = True
        state_resp = client.get('/api/team/state')
        self.assertEqual(state_resp.status_code, 200)
        state_data = state_resp.get_json()
        self.assertTrue(state_data['team']['is_disqualified'])
        self.assertEqual(state_data['team']['violation_count'], 3)

        # 2. Re-login attempt is blocked
        client_new = self.app.test_client()
        login_resp = client_new.post('/team/login', data={
            'team_code': 'TEAM010',
            'password': 'TEST@123'
        }, follow_redirects=True)
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn(b'disqualified', login_resp.data.lower())

    def test_07_host_dashboard_displays_disqualified(self):
        """Scenario 7: Host dashboard API immediately displays DISQUALIFIED status and strike count."""
        host_client = self.app.test_client()
        self._login_host(host_client)

        resp = host_client.get('/api/host/state')
        self.assertEqual(resp.status_code, 200)
        host_data = resp.get_json()

        team_10 = next((t for t in host_data['teams'] if t['team_code'] == 'TEAM010'), None)
        self.assertIsNotNone(team_10)
        self.assertTrue(team_10['is_disqualified'])
        self.assertEqual(team_10['violation_count'], 3)
        self.assertGreaterEqual(host_data['system_stats']['disqualified_teams'], 1)

    def test_08_other_teams_continue_participating_normally(self):
        """Scenario 8: Non-disqualified teams continue bidding normally."""
        active_auction = AuctionService.get_active_auction()
        if not active_auction:
            avail_q = fetch_one("SELECT id FROM questions WHERE status = 'AVAILABLE' LIMIT 1")
            auction_id = AuctionService.start_auction(avail_q['id'])
        else:
            auction_id = active_auction['id']

        # Normal team (TEAM011) places a bid
        client_11 = self.app.test_client()
        self._login_team(client_11, 'TEAM011')

        resp = client_11.post('/api/team/bid', json={'auction_id': auction_id})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])

        team_11 = fetch_one("SELECT violation_count, is_disqualified FROM teams WHERE team_code = 'TEAM011'")
        self.assertEqual(team_11['violation_count'], 0)
        self.assertFalse(bool(team_11['is_disqualified']))

    def test_09_single_violation_counts_once(self):
        """Scenario 9: Each violation increments strike count strictly by 1."""
        client = self.app.test_client()
        self._login_team(client, 'TEAM012')

        resp1 = client.post('/api/team/violation', json={
            'violation_type': 'FULLSCREEN_EXIT',
            'details': 'First exit'
        })
        self.assertEqual(resp1.get_json()['violation']['strike_count'], 1)

        team = fetch_one("SELECT violation_count FROM teams WHERE team_code = 'TEAM012'")
        self.assertEqual(team['violation_count'], 1)

if __name__ == '__main__':
    unittest.main()
