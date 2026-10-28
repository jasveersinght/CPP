import logging
from decimal import Decimal
from database.db import db_transaction, fetch_all, fetch_one

logger = logging.getLogger(__name__)

class WalletService:
    @staticmethod
    def deduct_winning_bid(team_id, auction_id, amount, cursor):
        """
        Deducts winning bid from team balance within an existing transactional cursor.
        Locks the team row with FOR UPDATE, verifies sufficient balance, updates balance,
        and logs the BID_PAYMENT transaction.
        """
        amount_dec = Decimal(str(amount))
        if amount_dec <= Decimal('0'):
            raise ValueError("Winning bid deduction amount must be positive.")

        # Lock team row
        cursor.execute("SELECT * FROM teams WHERE id = %s FOR UPDATE", (team_id,))
        team = cursor.fetchone()
        if not team:
            raise ValueError(f"Team with ID {team_id} not found.")

        current_balance = Decimal(str(team['current_balance']))
        if current_balance < amount_dec:
            raise ValueError(
                f"Insufficient funds: Team {team['team_code']} has INR {current_balance:.2f} "
                f"but winning bid requires INR {amount_dec:.2f}"
            )

        new_balance = current_balance - amount_dec
        
        # Update team balance
        cursor.execute(
            "UPDATE teams SET current_balance = %s WHERE id = %s",
            (new_balance, team_id)
        )

        # Record payment transaction (negative amount)
        cursor.execute(
            """
            INSERT INTO transactions (team_id, auction_id, transaction_type, amount, description, balance_after)
            VALUES (%s, %s, 'BID_PAYMENT', %s, %s, %s)
            """,
            (team_id, auction_id, -amount_dec, f"Winning bid payment for Auction #{auction_id}", new_balance)
        )

        logger.info(
            f"PAYMENT PROCESSED: Team {team['team_code']} deducted INR {amount_dec:.2f}. "
            f"Balance: INR {current_balance:.2f} -> INR {new_balance:.2f}"
        )
        return new_balance

    @staticmethod
    def credit_reward(team_id, auction_id, reward_amount, cursor):
        """
        Credits question reward to team balance within an existing transactional cursor.
        Locks the team row, increments balance, and logs the REWARD transaction.
        """
        reward_dec = Decimal(str(reward_amount))
        if reward_dec <= Decimal('0'):
            raise ValueError("Reward credit amount must be positive.")

        cursor.execute("SELECT * FROM teams WHERE id = %s FOR UPDATE", (team_id,))
        team = cursor.fetchone()
        if not team:
            raise ValueError(f"Team with ID {team_id} not found.")

        current_balance = Decimal(str(team['current_balance']))
        new_balance = current_balance + reward_dec

        cursor.execute(
            "UPDATE teams SET current_balance = %s WHERE id = %s",
            (new_balance, team_id)
        )

        cursor.execute(
            """
            INSERT INTO transactions (team_id, auction_id, transaction_type, amount, description, balance_after)
            VALUES (%s, %s, 'REWARD', %s, %s, %s)
            """,
            (team_id, auction_id, reward_dec, f"Bounty reward for solving Question in Auction #{auction_id}", new_balance)
        )

        logger.info(
            f"MONEY CREDIT: Team {team['team_code']} rewarded INR {reward_dec:.2f}. "
            f"Balance: INR {current_balance:.2f} -> INR {new_balance:.2f}"
        )
        return new_balance

    @staticmethod
    def get_team_transactions(team_id):
        """Fetches complete transaction ledger for a specific team."""
        sql = """
            SELECT id, auction_id, transaction_type, amount, description, balance_after, created_at
            FROM transactions
            WHERE team_id = %s
            ORDER BY id DESC
        """
        rows = fetch_all(sql, (team_id,))
        for r in rows:
            r['created_at_formatted'] = r['created_at'].strftime('%d %b %Y, %H:%M:%S') if r.get('created_at') else ''
        return rows

    @staticmethod
    def get_all_transactions(limit=100):
        """Host view: fetch all recent transactions across all teams."""
        sql = """
            SELECT tx.id, tx.team_id, tx.auction_id, tx.transaction_type, tx.amount,
                   tx.description, tx.balance_after, tx.created_at,
                   t.team_code, t.team_name
            FROM transactions tx
            JOIN teams t ON tx.team_id = t.id
            ORDER BY tx.id DESC
            LIMIT %s
        """
        rows = fetch_all(sql, (limit,))
        for r in rows:
            r['created_at_formatted'] = r['created_at'].strftime('%d %b %Y, %H:%M:%S') if r.get('created_at') else ''
        return rows
