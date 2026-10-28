import unittest
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import init_database, seed_database
from database.db import fetch_one, fetch_all, execute_query
from services.auction_service import AuctionService
from services.reconciliation_service import ReconciliationService
from app import create_app

class TestRestartRecovery(unittest.TestCase):
    def setUp(self):
        init_database()
        seed_database()

    def test_section39_exact_restart_recovery_test(self):
        """
        Executes the exact restart test from Section 39:
        1. Start an auction with bids.
        2. Record ends_at.
        3. Simulate app shutdown while timer is running.
        4. Advance time past ends_at while server is down.
        5. Restart Flask application (invoking startup reconciliation).
        6. Verify application detects expired auction.
        7. Auction becomes ENDED.
        8. Winner/payment processing occurs correctly.
        9. Run reconciliation again to verify idempotence: NO duplicate transaction, NO duplicate deduction!
        """
        q = fetch_one("SELECT id, starting_bid FROM questions WHERE id = 1")
        auction_id = AuctionService.start_auction(q['id'])

        team = fetch_one("SELECT id, team_code, current_balance FROM teams WHERE team_code = 'TEAM003'")
        bid_amount = AuctionService.place_bid(auction_id, team['id'])

        auction_before = fetch_one("SELECT * FROM auctions WHERE id = %s", (auction_id,))
        self.assertEqual(auction_before['status'], 'LIVE')
        ends_at_recorded = auction_before['ends_at']

        # Simulate time passing past ends_at while application is down
        execute_query(
            "UPDATE auctions SET ends_at = DATE_SUB(NOW(6), INTERVAL 5 SECOND) WHERE id = %s",
            (auction_id,)
        )

        # Restart Flask application: create_app() executes startup reconciliation
        app, socketio = create_app()

        # Check auction state after startup reconciliation
        auction_after = fetch_one("SELECT * FROM auctions WHERE id = %s", (auction_id,))
        self.assertEqual(auction_after['status'], 'ENDED')
        self.assertEqual(auction_after['winner_team_id'], team['id'])

        # Verify payment processing occurred correctly
        team_after = fetch_one("SELECT * FROM teams WHERE id = %s", (team['id'],))
        expected_balance = Decimal(str(team['current_balance'])) - Decimal(str(bid_amount))
        self.assertEqual(Decimal(str(team_after['current_balance'])), expected_balance)
        self.assertEqual(team_after['questions_won'], 1)

        # Verify transaction created
        txs = fetch_all("SELECT * FROM transactions WHERE team_id = %s AND auction_id = %s", (team['id'], auction_id))
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]['transaction_type'], 'BID_PAYMENT')

        # Run reconciliation AGAIN to ensure idempotence
        ReconciliationService.reconcile_expired_auctions()

        # Verify NO duplicate deductions or transactions occurred
        team_check = fetch_one("SELECT * FROM teams WHERE id = %s", (team['id'],))
        self.assertEqual(Decimal(str(team_check['current_balance'])), expected_balance)
        txs_check = fetch_all("SELECT * FROM transactions WHERE team_id = %s AND auction_id = %s", (team['id'], auction_id))
        self.assertEqual(len(txs_check), 1)

if __name__ == '__main__':
    unittest.main()
