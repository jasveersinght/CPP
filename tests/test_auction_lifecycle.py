import unittest
import sys
import os
import time
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import init_database, seed_database
from database.db import fetch_one, fetch_all, execute_query
from services.auction_service import AuctionService
from services.reconciliation_service import ReconciliationService

class TestAuctionLifecycle(unittest.TestCase):
    def setUp(self):
        init_database()
        seed_database()

    def test_01_single_live_auction_constraint(self):
        """Only one LIVE auction can exist at any given time."""
        q1 = fetch_one("SELECT id FROM questions WHERE id = 1")
        q2 = fetch_one("SELECT id FROM questions WHERE id = 2")

        auction_id = AuctionService.start_auction(q1['id'], reading_duration=0)
        self.assertIsNotNone(auction_id)

        # Attempting to start another live auction must fail
        with self.assertRaises(ValueError):
            AuctionService.start_auction(q2['id'], reading_duration=0)

    def test_02_section38_exact_auction_test(self):
        """
        Executes the exact workflow from Section 38:
        1. Start auction.
        2. Wait without bidding until expiry.
        3. Verify status = ENDED (NOT LIVE), question reset to AVAILABLE.
        4. Start another auction.
        5. Team A bids -> timer resets.
        6. Team B bids -> timer resets.
        7. No more bids.
        8. Auction ends after expiry.
        9. Winner = Team B.
        10. Team B wallet decreases by winning bid.
        11. Transaction created.
        12. Question becomes QUESTION_ACTIVE.
        """
        # Step 1: Start auction
        q1 = fetch_one("SELECT id, starting_bid FROM questions WHERE id = 1")
        a1_id = AuctionService.start_auction(q1['id'], reading_duration=0)

        # Fast-forward / simulate time expiry for a1
        execute_query("UPDATE auctions SET ends_at = DATE_SUB(NOW(6), INTERVAL 1 SECOND) WHERE id = %s", (a1_id,))
        ReconciliationService.reconcile_expired_auctions()

        a1_db = fetch_one("SELECT * FROM auctions WHERE id = %s", (a1_id,))
        self.assertEqual(a1_db['status'], 'ENDED')
        self.assertIsNone(a1_db['winner_team_id'])

        q1_db = fetch_one("SELECT * FROM questions WHERE id = %s", (q1['id'],))
        self.assertEqual(q1_db['status'], 'AVAILABLE')

        # Step 4: Start another auction (reading_duration=0 to test direct bidding)
        q2 = fetch_one("SELECT id, starting_bid FROM questions WHERE id = 2")
        a2_id = AuctionService.start_auction(q2['id'], reading_duration=0)

        team_a = fetch_one("SELECT id, team_code, current_balance FROM teams WHERE team_code = 'TEAM001'")
        team_b = fetch_one("SELECT id, team_code, current_balance FROM teams WHERE team_code = 'TEAM002'")

        # Step 5: Team A bids -> First bid is starting bid
        bid_a = AuctionService.place_bid(a2_id, team_a['id'])
        self.assertEqual(bid_a, float(q2['starting_bid']))

        a2_db = fetch_one("SELECT * FROM auctions WHERE id = %s", (a2_id,))
        self.assertEqual(a2_db['current_bidder_id'], team_a['id'])
        self.assertEqual(Decimal(str(a2_db['current_bid'])), Decimal(str(q2['starting_bid'])))

        # Step 6: Team B bids -> Increments by ₹10 and resets timer
        bid_b = AuctionService.place_bid(a2_id, team_b['id'])
        expected_bid_b = float(q2['starting_bid']) + 10.0
        self.assertEqual(bid_b, expected_bid_b)

        a2_db = fetch_one("SELECT * FROM auctions WHERE id = %s", (a2_id,))
        self.assertEqual(a2_db['current_bidder_id'], team_b['id'])
        self.assertEqual(Decimal(str(a2_db['current_bid'])), Decimal(str(expected_bid_b)))

        # Team B cannot outbid itself
        with self.assertRaises(ValueError):
            AuctionService.place_bid(a2_id, team_b['id'])

        # Step 7 & 8: Simulate expiry without more bids
        execute_query("UPDATE auctions SET ends_at = DATE_SUB(NOW(6), INTERVAL 1 SECOND) WHERE id = %s", (a2_id,))
        ReconciliationService.reconcile_expired_auctions(force=True)

        # Step 9: Verify winner = Team B
        a2_final = fetch_one("SELECT * FROM auctions WHERE id = %s", (a2_id,))
        self.assertEqual(a2_final['status'], 'ENDED')
        self.assertEqual(a2_final['winner_team_id'], team_b['id'])

        # Step 10: Team B wallet decreases by winning bid
        team_b_updated = fetch_one("SELECT * FROM teams WHERE id = %s", (team_b['id'],))
        expected_balance = Decimal(str(team_b['current_balance'])) - Decimal(str(expected_bid_b))
        self.assertEqual(Decimal(str(team_b_updated['current_balance'])), expected_balance)
        self.assertEqual(team_b_updated['questions_won'], 1)
        self.assertEqual(team_b_updated['status'], 'WAITING')

        # Step 11: Transaction created
        txs = fetch_all("SELECT * FROM transactions WHERE team_id = %s AND auction_id = %s", (team_b['id'], a2_id))
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]['transaction_type'], 'BID_PAYMENT')
        self.assertEqual(Decimal(str(txs[0]['amount'])), Decimal(str(-expected_bid_b)))
        self.assertEqual(Decimal(str(txs[0]['balance_after'])), expected_balance)

        # Step 12: Question becomes QUESTION_ACTIVE
        q2_final = fetch_one("SELECT * FROM questions WHERE id = %s", (q2['id'],))
        self.assertEqual(q2_final['status'], 'QUESTION_ACTIVE')

        # Host dashboard no longer shows auction as LIVE
        live_auction = AuctionService.get_active_auction()
        self.assertIsNone(live_auction)

if __name__ == '__main__':
    unittest.main()
