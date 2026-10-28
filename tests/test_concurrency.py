import unittest
import sys
import os
import concurrent.futures
from decimal import Decimal
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import init_database, seed_database
from database.db import fetch_one, fetch_all, execute_query, db_transaction
from services.auction_service import AuctionService
from services.reconciliation_service import ReconciliationService

class TestConcurrency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()
        seed_database()

        # Seed additional teams up to 100 concurrent teams
        pwd_hash = generate_password_hash('team123')
        with db_transaction() as (conn, cursor):
            for i in range(6, 101):
                code = f"TEAM{i:03d}"
                name = f"Simulated Squad {i}"
                cursor.execute(
                    """
                    INSERT INTO teams (team_code, team_name, password_hash, starting_balance, current_balance, status)
                    VALUES (%s, %s, %s, 10000.00, 10000.00, 'WAITING')
                    ON DUPLICATE KEY UPDATE team_name=VALUES(team_name)
                    """,
                    (code, name, pwd_hash)
                )
                t_id = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT INTO transactions (team_id, transaction_type, amount, description, balance_after)
                    VALUES (%s, 'STARTING_BALANCE', 10000.00, 'Initial allocation', 10000.00)
                    """,
                    (t_id,)
                )

    def test_100_concurrent_teams_bidding(self):
        """
        Simulates 100 teams attempting to place bids simultaneously.
        Verifies row-level locking (SELECT ... FOR UPDATE):
        - Zero race conditions
        - Every accepted bid has a unique strictly increasing amount
        - Exactly one winner identified on auction close
        - Winning bid deducted exactly once
        - No other team balance modified
        """
        teams = fetch_all("SELECT id, team_code, current_balance FROM teams ORDER BY id ASC LIMIT 100")
        self.assertEqual(len(teams), 100)

        q = fetch_one("SELECT id, starting_bid FROM questions WHERE id = 1")
        auction_id = AuctionService.start_auction(q['id'], reading_duration=0)

        successful_bids = []
        rejected_bids = []

        def attempt_bid(team_info):
            try:
                # Each team tries to place a bid
                bid_val = AuctionService.place_bid(auction_id, team_info['id'])
                return (True, team_info['id'], bid_val, None)
            except Exception as e:
                return (False, team_info['id'], None, str(e))

        # Launch 100 concurrent threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(attempt_bid, t) for t in teams]
            for f in concurrent.futures.as_completed(futures):
                success, t_id, bid_val, err = f.result()
                if success:
                    successful_bids.append((t_id, bid_val))
                else:
                    rejected_bids.append((t_id, err))

        print(f"\n[Concurrency Test] 100 simultaneous bids -> {len(successful_bids)} accepted, {len(rejected_bids)} rejected/handled.")
        self.assertGreater(len(successful_bids), 0)

        # Verify all recorded bids in the database
        db_bids = fetch_all("SELECT * FROM bids WHERE auction_id = %s ORDER BY id ASC", (auction_id,))
        self.assertEqual(len(db_bids), len(successful_bids))

        # Verify strictly unique, increasing bid values
        bid_amounts = [float(b['bid_amount']) for b in db_bids]
        self.assertEqual(len(bid_amounts), len(set(bid_amounts)), "Bid amounts must be strictly unique!")

        # Verify each subsequent bid incremented by exactly 10.0
        starting_bid = float(q['starting_bid'])
        self.assertEqual(bid_amounts[0], starting_bid)
        for idx in range(1, len(bid_amounts)):
            self.assertAlmostEqual(bid_amounts[idx], bid_amounts[idx-1] + 10.0, places=2)

        # Verify auction current_bid matches highest bid
        auction_db = fetch_one("SELECT * FROM auctions WHERE id = %s", (auction_id,))
        self.assertEqual(float(auction_db['current_bid']), bid_amounts[-1])
        self.assertEqual(auction_db['current_bidder_id'], db_bids[-1]['team_id'])

        # Now simulate timer expiry and close auction
        execute_query("UPDATE auctions SET ends_at = DATE_SUB(NOW(6), INTERVAL 1 SECOND) WHERE id = %s", (auction_id,))
        closed_info = ReconciliationService.reconcile_expired_auctions()
        self.assertEqual(len(closed_info), 1)

        winner_team_id = db_bids[-1]['team_id']
        winning_bid = Decimal(str(bid_amounts[-1]))

        # Verify winner team balance deducted
        winner_db = fetch_one("SELECT * FROM teams WHERE id = %s", (winner_team_id,))
        expected_winner_bal = Decimal('10000.00') - winning_bid
        self.assertEqual(Decimal(str(winner_db['current_balance'])), expected_winner_bal)
        self.assertEqual(winner_db['questions_won'], 1)

        # Verify winning transaction
        txs = fetch_all("SELECT * FROM transactions WHERE team_id = %s AND auction_id = %s", (winner_team_id, auction_id))
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]['transaction_type'], 'BID_PAYMENT')
        self.assertEqual(Decimal(str(txs[0]['amount'])), -winning_bid)

        # Verify other 99 teams balances are intact (₹10,000.00)
        other_teams = fetch_all("SELECT current_balance FROM teams WHERE id != %s AND id <= 100", (winner_team_id,))
        for ot in other_teams:
            self.assertEqual(Decimal(str(ot['current_balance'])), Decimal('10000.00'))

if __name__ == '__main__':
    unittest.main()
