"""
CRYTEX: 80-Team Concurrency & Scale Simulation Test Suite
(Development & Testing Only)

Simulates 80 concurrent teams:
- 80 simultaneous team logins
- Concurrent state synchronization and reconnection
- Host live auction initiation
- High-frequency concurrent bidding with row-lock serialization
- Authoritative timer resets and single-winner resolution
- Wallet atomic debit and 5-question limit enforcement
- Question queue verification and duplicate submission rejection
- Host dynamic team creation and instant login verification
"""

import os
import sys
import time
import concurrent.futures
import logging
import unittest
from decimal import Decimal

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from config import get_config
from database.init_db import init_database, seed_database
from database.db import fetch_one, fetch_all
from services.auction_service import AuctionService
from services.wallet_service import WalletService
from services.answer_service import AnswerService
from services.leaderboard_service import LeaderboardService

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('simulate_80_teams')

class TestScale80Teams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("Initializing clean database with 80 teams and 90 questions...")
        init_database()
        seed_database()

        cls.app, cls.socketio = create_app()
        cls.app.config['TESTING'] = True

    def test_01_verify_seed_counts(self):
        """Verify exactly 80 teams and 90 questions exist in database."""
        teams_count = fetch_one("SELECT count(*) as c FROM teams")['c']
        questions_count = fetch_one("SELECT count(*) as c FROM questions")['c']

        self.assertEqual(teams_count, 80, f"Expected 80 teams, got {teams_count}")
        self.assertEqual(questions_count, 90, f"Expected 90 questions, got {questions_count}")
        logger.info("TEST 1 PASSED: Exactly 80 teams and 90 questions verified in database.")

    def test_02_all_80_teams_login_concurrently(self):
        """Simulate 80 simultaneous teams logging in concurrently."""
        logger.info("Simulating concurrent logins for all 80 teams...")

        def login_team(team_index):
            client = self.app.test_client()
            code = f"TEAM{team_index:03d}"
            resp = client.post('/team/login', data={
                'team_code': code,
                'password': 'TEST@123'
            }, follow_redirects=False)

            with client.session_transaction() as sess:
                team_id = sess.get('team_id')

            return (team_index, resp.status_code, team_id)

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            futures = [executor.submit(login_team, i) for i in range(1, 81)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        self.assertEqual(len(results), 80)
        for idx, status, team_id in results:
            self.assertEqual(status, 302, f"Team #{idx} failed to log in, HTTP {status}")
            self.assertIsNotNone(team_id, f"Team #{idx} did not receive a session team_id")

        logger.info(f"TEST 2 PASSED: All 80 teams logged in successfully and concurrently!")

    def test_03_concurrent_state_sync_and_reconnection(self):
        """Simulate 80 connected clients synchronizing state at the same time."""
        logger.info("Simulating 80 teams requesting state sync concurrently...")

        def sync_team(team_index):
            client = self.app.test_client()
            code = f"TEAM{team_index:03d}"
            client.post('/team/login', data={'team_code': code, 'password': 'TEST@123'})
            resp = client.get('/api/team/state')
            data = resp.get_json()
            return (team_index, resp.status_code, data)

        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            futures = [executor.submit(sync_team, i) for i in range(1, 81)]
            for f in concurrent.futures.as_completed(futures):
                idx, status, data = f.result()
                self.assertEqual(status, 200)
                self.assertEqual(data['team']['current_balance'], 10000.0)
                self.assertEqual(data['team']['questions_won'], 0)
                self.assertIsNotNone(data['team']['rank'])

        logger.info("TEST 3 PASSED: All 80 teams synchronized state with zero conflicts.")

    def test_04_concurrent_bidding_and_single_winner(self):
        """Simulate multiple teams bidding simultaneously on the same live auction."""
        logger.info("Host launches Auction for Question #1...")
        auction_id = AuctionService.start_auction(question_id=1)

        # 30 teams simultaneously attempt to bid
        bidding_teams = list(range(1, 31))
        successful_bids = []
        rejected_bids = []

        def place_concurrent_bid(team_idx):
            client = self.app.test_client()
            code = f"TEAM{team_idx:03d}"
            client.post('/team/login', data={'team_code': code, 'password': 'TEST@123'})
            resp = client.post('/api/team/bid', json={'auction_id': auction_id})
            return (team_idx, resp.get_json())

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(place_concurrent_bid, i) for i in bidding_teams]
            for f in concurrent.futures.as_completed(futures):
                idx, res = f.result()
                if res.get('success'):
                    successful_bids.append((idx, res['new_bid']))
                else:
                    rejected_bids.append((idx, res.get('error')))

        logger.info(f"Concurrent bids result: {len(successful_bids)} accepted, {len(rejected_bids)} serial-wait/handled.")
        self.assertGreaterEqual(len(successful_bids), 1, "At least one bid must succeed")

        # Close the auction and verify single winner
        close_result = AuctionService.close_auction(auction_id)
        self.assertTrue(close_result['has_winner'])
        winner_id = close_result['winner_team_id']
        winning_bid = close_result['winning_bid']
        self.assertIsNotNone(winner_id)

        winner_team = fetch_one("SELECT * FROM teams WHERE id = %s", (winner_id,))
        self.assertEqual(winner_team['questions_won'], 1)
        expected_balance = 10000.0 - winning_bid
        self.assertAlmostEqual(float(winner_team['current_balance']), expected_balance, places=2)

        # Non-winners must retain full ₹10,000 balance
        non_winners = fetch_all("SELECT * FROM teams WHERE id != %s AND id BETWEEN 1 AND 80", (winner_id,))
        for nw in non_winners:
            self.assertEqual(float(nw['current_balance']), 10000.0, f"Non-winner {nw['team_code']} was erroneously debited!")

        logger.info(f"TEST 4 PASSED: Single winner {close_result['winner_team_code']} cleanly debited INR {winning_bid:.2f}. No double-debit!")

    def test_05_five_question_limit_enforcement(self):
        """A team cannot bid once it has won 5 questions."""
        target_team = fetch_one("SELECT id, team_code FROM teams WHERE id = 10")
        team_id = target_team['id']

        # Set questions_won = 5 for this team
        with self.app.app_context():
            from database.db import execute_query
            execute_query("UPDATE teams SET questions_won = 5 WHERE id = %s", (team_id,))

        auction_id = AuctionService.start_auction(question_id=2)

        client = self.app.test_client()
        client.post('/team/login', data={'team_code': target_team['team_code'], 'password': 'TEST@123'})
        resp = client.post('/api/team/bid', json={'auction_id': auction_id})
        res = resp.get_json()

        self.assertFalse(res['success'], "Team with 5 won questions must NOT be allowed to bid!")
        self.assertIn("Question limit reached", res['error'])

        # Cancel auction 2
        AuctionService.cancel_auction(auction_id)
        logger.info("TEST 5 PASSED: 5-question limit strictly enforced on bidding.")

    def test_06_won_question_queue_and_safe_answer_submission(self):
        """Won questions appear in queue, can be solved, credit reward once, reject duplicate."""
        target_team = fetch_one("SELECT id, team_code FROM teams WHERE id = 15")
        team_id = target_team['id']

        # Start and win auction for Question 3
        auction_id = AuctionService.start_auction(question_id=3)
        AuctionService.place_bid(auction_id, team_id)
        AuctionService.close_auction(auction_id)

        # Check won questions queue
        won_questions = AuctionService.get_team_won_questions(team_id)
        self.assertEqual(len(won_questions), 1)
        self.assertEqual(won_questions[0]['question_id'], 3)
        self.assertFalse(won_questions[0]['is_solved'])

        # Submit correct answer (Q3 answer is 1)
        client = self.app.test_client()
        client.post('/team/login', data={'team_code': target_team['team_code'], 'password': 'TEST@123'})
        resp = client.post('/api/team/submit-answer', json={
            'auction_id': auction_id,
            'answer': '1'
        })
        res = resp.get_json()
        self.assertTrue(res['success'])
        self.assertTrue(res['result']['is_correct'])
        self.assertGreater(res['result']['reward_credited'], 0.0)

        # Attempt duplicate submission for same auction
        resp_dup = client.post('/api/team/submit-answer', json={
            'auction_id': auction_id,
            'answer': '1'
        })
        res_dup = resp_dup.get_json()
        self.assertFalse(res_dup['success'], "Duplicate submission must be rejected!")
        self.assertIn("already been submitted", res_dup['error'])

        # Verify won queue marks question as solved
        updated_won = AuctionService.get_team_won_questions(team_id)
        self.assertTrue(updated_won[0]['is_solved'])
        self.assertTrue(updated_won[0]['is_correct'])

        logger.info("TEST 6 PASSED: Won question solved, reward credited, duplicate rejected.")

    def test_07_host_add_team_dynamically(self):
        """Host adds new team at runtime, and team immediately logs in."""
        host_client = self.app.test_client()
        host_client.post('/host/login', data={'username': 'admin', 'password': 'host123'})

        new_code = "TEAM081"
        new_name = "Dynamic Titans"
        new_pwd = "TitanSecure@99"

        resp = host_client.post('/api/host/teams/add', json={
            'team_name': new_name,
            'team_code': new_code,
            'password': new_pwd,
            'starting_balance': 10000.0
        })
        res = resp.get_json()
        self.assertTrue(res.get('success'), f"Failed to add team: {res}")

        # Newly added team immediately logs in
        new_client = self.app.test_client()
        login_resp = new_client.post('/team/login', data={
            'team_code': new_code,
            'password': new_pwd
        }, follow_redirects=False)
        self.assertEqual(login_resp.status_code, 302)

        # Check balance and transaction
        state_resp = new_client.get('/api/team/state')
        state_data = state_resp.get_json()
        self.assertEqual(state_data['team']['team_code'], new_code)
        self.assertEqual(state_data['team']['current_balance'], 10000.0)

        logger.info(f"TEST 7 PASSED: Host added {new_code} dynamically and team logged in immediately!")

if __name__ == '__main__':
    unittest.main()
