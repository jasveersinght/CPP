import unittest
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import init_database, seed_database
from database.db import db_transaction, fetch_one, fetch_all
from services.wallet_service import WalletService

class TestWallet(unittest.TestCase):
    def setUp(self):
        init_database()
        seed_database()
        # Create an auction row to satisfy transactions foreign key
        from database.db import execute_query
        self.auction_id = execute_query(
            "INSERT INTO auctions (question_id, starting_bid, current_bid, status) VALUES (1, 500.0, 500.0, 'LIVE')"
        )

    def test_01_initial_balance_and_transaction(self):
        """Every team starts with 10,000 purse and a STARTING_BALANCE transaction."""
        teams = fetch_all("SELECT * FROM teams LIMIT 10")  # Check a sample of teams
        self.assertGreater(len(teams), 0, "No teams found in database")
        for t in teams:
            self.assertEqual(Decimal(str(t['starting_balance'])), Decimal('10000.00'))
            self.assertEqual(Decimal(str(t['current_balance'])), Decimal('10000.00'))
            tx = fetch_all("SELECT * FROM transactions WHERE team_id = %s", (t['id'],))
            self.assertEqual(len(tx), 1)
            self.assertEqual(tx[0]['transaction_type'], 'STARTING_BALANCE')
            self.assertEqual(Decimal(str(tx[0]['amount'])), Decimal('10000.00'))

    def test_02_deduct_winning_bid(self):
        """Winning bid payment deducts balance and creates BID_PAYMENT transaction with negative amount."""
        team = fetch_one("SELECT * FROM teams WHERE team_code = 'TEAM001'")
        with db_transaction() as (conn, cursor):
            new_bal = WalletService.deduct_winning_bid(team['id'], auction_id=self.auction_id, amount=750.00, cursor=cursor)

        self.assertEqual(new_bal, Decimal('9250.00'))
        updated_team = fetch_one("SELECT * FROM teams WHERE id = %s", (team['id'],))
        self.assertEqual(Decimal(str(updated_team['current_balance'])), Decimal('9250.00'))

        txs = fetch_all("SELECT * FROM transactions WHERE team_id = %s ORDER BY id DESC", (team['id'],))
        self.assertEqual(len(txs), 2)
        latest_tx = txs[0]
        self.assertEqual(latest_tx['transaction_type'], 'BID_PAYMENT')
        self.assertEqual(Decimal(str(latest_tx['amount'])), Decimal('-750.00'))
        self.assertEqual(Decimal(str(latest_tx['balance_after'])), Decimal('9250.00'))

    def test_03_credit_reward(self):
        """Reward credit increases balance and creates REWARD transaction with positive amount."""
        team = fetch_one("SELECT * FROM teams WHERE team_code = 'TEAM001'")
        with db_transaction() as (conn, cursor):
            new_bal = WalletService.credit_reward(team['id'], auction_id=self.auction_id, reward_amount=2000.00, cursor=cursor)

        self.assertEqual(new_bal, Decimal('12000.00'))
        updated_team = fetch_one("SELECT * FROM teams WHERE id = %s", (team['id'],))
        self.assertEqual(Decimal(str(updated_team['current_balance'])), Decimal('12000.00'))

        txs = fetch_all("SELECT * FROM transactions WHERE team_id = %s ORDER BY id DESC", (team['id'],))
        self.assertEqual(txs[0]['transaction_type'], 'REWARD')
        self.assertEqual(Decimal(str(txs[0]['amount'])), Decimal('2000.00'))

    def test_04_insufficient_balance_fails(self):
        """Attempting to deduct more than current balance must fail and roll back."""
        team = fetch_one("SELECT * FROM teams WHERE team_code = 'TEAM002'")
        with self.assertRaises(ValueError):
            with db_transaction() as (conn, cursor):
                WalletService.deduct_winning_bid(team['id'], auction_id=self.auction_id, amount=15000.00, cursor=cursor)

        # Ensure no change occurred
        refreshed = fetch_one("SELECT * FROM teams WHERE id = %s", (team['id'],))
        self.assertEqual(Decimal(str(refreshed['current_balance'])), Decimal('10000.00'))

if __name__ == '__main__':
    unittest.main()
