import logging
from decimal import Decimal
from datetime import datetime
from config import get_config
from database.db import db_transaction, fetch_one, fetch_all, get_db_cursor
from services.wallet_service import WalletService

logger = logging.getLogger(__name__)

class AuctionService:
    @staticmethod
    def get_active_auction():
        """
        Fetches the currently active (LIVE) auction if any.
        Computes remaining time based on server database time.
        Does NOT expose the correct answer!
        """
        sql = """
            SELECT a.id, a.question_id, a.starting_bid, a.current_bid,
                   a.current_bidder_id, a.status,
                   a.started_at, a.ends_at,
                   TIMESTAMPDIFF(MICROSECOND, NOW(6), a.ends_at) / 1000000.0 as time_remaining,
                   q.category, q.question_text, q.question_image, q.question_type,
                   q.options, q.reward,
                   t.team_code as current_bidder_code, t.team_name as current_bidder_name
            FROM auctions a
            JOIN questions q ON a.question_id = q.id
            LEFT JOIN teams t ON a.current_bidder_id = t.id
            WHERE a.status = 'LIVE'
            ORDER BY a.id DESC
            LIMIT 1
        """
        row = fetch_one(sql)
        if not row:
            return None

        # Convert Decimal values for JSON serialization
        time_rem = float(row['time_remaining']) if row['time_remaining'] is not None else 0.0
        row['time_remaining'] = max(0.0, round(time_rem, 2))
        row['starting_bid'] = float(row['starting_bid'])
        row['current_bid'] = float(row['current_bid'])
        row['reward'] = float(row['reward'])
        row['ends_at_iso'] = row['ends_at'].isoformat() if row['ends_at'] else None
        row['started_at_iso'] = row['started_at'].isoformat() if row['started_at'] else None
        return row

    @staticmethod
    def get_auction_by_id(auction_id):
        """Fetch auction details by ID."""
        sql = """
            SELECT a.*, q.category, q.question_text, q.question_image, q.question_type,
                   q.options, q.reward,
                   t.team_code as winner_code, t.team_name as winner_name
            FROM auctions a
            JOIN questions q ON a.question_id = q.id
            LEFT JOIN teams t ON a.winner_team_id = t.id
            WHERE a.id = %s
        """
        return fetch_one(sql, (auction_id,))

    @staticmethod
    def start_auction(question_id, socketio=None):
        """
        Host starts an auction for a specified question.
        Ensures only ONE live auction exists.
        Initializes auction with starting bid and 10s countdown.
        """
        cfg = get_config()
        duration_sec = cfg.AUCTION_DURATION_SECONDS

        with db_transaction() as (conn, cursor):
            # 1. Enforce single LIVE auction constraint
            cursor.execute("SELECT id FROM auctions WHERE status = 'LIVE' FOR UPDATE")
            live_existing = cursor.fetchone()
            if live_existing:
                raise ValueError(f"Cannot start auction: Auction #{live_existing['id']} is currently LIVE.")

            # 2. Lock and validate question
            cursor.execute("SELECT * FROM questions WHERE id = %s FOR UPDATE", (question_id,))
            question = cursor.fetchone()
            if not question:
                raise ValueError(f"Question #{question_id} not found.")
            if question['status'] not in ('AVAILABLE', 'ENDED'):
                raise ValueError(f"Question #{question_id} is in status '{question['status']}' and cannot be auctioned.")

            # 3. Mark question LIVE
            cursor.execute("UPDATE questions SET status = 'LIVE' WHERE id = %s", (question_id,))

            starting_bid = question['starting_bid']

            # 4. Insert new Auction row
            cursor.execute(
                """
                INSERT INTO auctions (question_id, starting_bid, current_bid, current_bidder_id, status, started_at, ends_at)
                VALUES (%s, %s, %s, NULL, 'LIVE', NOW(6), DATE_ADD(NOW(6), INTERVAL %s SECOND))
                """,
                (question_id, starting_bid, starting_bid, duration_sec)
            )
            auction_id = cursor.lastrowid

            # Fetch fresh auction data with server timestamps
            cursor.execute(
                """
                SELECT a.id, a.question_id, a.starting_bid, a.current_bid, a.status,
                       a.ends_at, TIMESTAMPDIFF(MICROSECOND, NOW(6), a.ends_at) / 1000000.0 as time_remaining,
                       q.category, q.question_text, q.question_type, q.reward, q.options
                FROM auctions a
                JOIN questions q ON a.question_id = q.id
                WHERE a.id = %s
                """,
                (auction_id,)
            )
            auction_data = cursor.fetchone()

        logger.info(f"AUCTION STARTED: Auction #{auction_id} for Question #{question_id}. Starting bid: INR {starting_bid:.2f}")

        # Broadcast real-time event via Socket.IO
        if socketio:
            payload = {
                'auction_id': auction_id,
                'question_id': question_id,
                'category': auction_data['category'],
                'question_text': auction_data['question_text'],
                'question_type': auction_data['question_type'],
                'starting_bid': float(auction_data['starting_bid']),
                'current_bid': float(auction_data['current_bid']),
                'next_bid': float(auction_data['starting_bid']),
                'reward': float(auction_data['reward']),
                'time_remaining': max(0.0, round(float(auction_data['time_remaining']), 2)),
                'ends_at_iso': auction_data['ends_at'].isoformat() if auction_data['ends_at'] else None,
                'current_bidder': None
            }
            socketio.emit('auction_started', payload)

        return auction_id

    @staticmethod
    def place_bid(auction_id, team_id, socketio=None):
        """
        Executes a bid on a live auction with row-level locking (SELECT ... FOR UPDATE).
        Server-authoritative validation:
        1. Locks auction row.
        2. Validates auction status == 'LIVE'.
        3. Verifies server/database time has not passed ends_at.
        4. Validates team eligibility, limits (5 question limit), and balance.
        5. Calculates server-determined next bid (starting bid for first, +₹10 for subsequent).
        6. Records bid in bids table.
        7. Resets ends_at to NOW(6) + 10s.
        8. Commits transaction and broadcasts bid_update.
        """
        cfg = get_config()
        duration_sec = cfg.AUCTION_DURATION_SECONDS
        increment = Decimal(str(cfg.BID_INCREMENT))

        with db_transaction() as (conn, cursor):
            # 1. Lock auction row
            cursor.execute("SELECT * FROM auctions WHERE id = %s FOR UPDATE", (auction_id,))
            auction = cursor.fetchone()
            if not auction:
                raise ValueError(f"Auction #{auction_id} does not exist.")

            if auction['status'] != 'LIVE':
                raise ValueError(f"Auction #{auction_id} is not LIVE (status: {auction['status']}).")

            # 2. Check server/database time vs ends_at
            cursor.execute("SELECT NOW(6) as now_time")
            now_time = cursor.fetchone()['now_time']

            if auction['ends_at'] and now_time >= auction['ends_at']:
                # Auction expired! Trigger atomic close within this transaction context
                logger.info(f"Bid rejected on expired auction #{auction_id}. Auto-closing auction.")
                AuctionService._close_auction_internal(auction_id, cursor, socketio=socketio)
                raise ValueError("Auction has already expired! No more bids accepted.")

            # 3. Lock team row and validate
            cursor.execute("SELECT * FROM teams WHERE id = %s FOR UPDATE", (team_id,))
            team = cursor.fetchone()
            if not team:
                raise ValueError(f"Team #{team_id} does not exist.")

            if team['is_disqualified']:
                raise ValueError("Team is disqualified from competition due to violations.")

            if not team.get('is_active', True):
                raise ValueError("Team account has been deactivated by host.")

            if team['questions_won'] >= cfg.MAX_QUESTIONS_PER_TEAM or team['questions_completed'] >= cfg.MAX_QUESTIONS_PER_TEAM:
                raise ValueError(f"Question limit reached: Your team has already won {team['questions_won']} questions (maximum {cfg.MAX_QUESTIONS_PER_TEAM}).")

            if auction['current_bidder_id'] == team_id:
                raise ValueError("Your team is already the highest bidder!")

            # 4. Calculate next valid bid
            current_bid = Decimal(str(auction['current_bid']))
            starting_bid = Decimal(str(auction['starting_bid']))

            if auction['current_bidder_id'] is None:
                # First bid is starting bid
                next_bid = starting_bid
            else:
                next_bid = current_bid + increment

            team_balance = Decimal(str(team['current_balance']))
            if team_balance < next_bid:
                raise ValueError(
                    f"Insufficient funds: Wallet has INR {team_balance:.2f}, but next bid is INR {next_bid:.2f}."
                )

            # 5. Insert Bid record
            cursor.execute(
                """
                INSERT INTO bids (auction_id, team_id, bid_amount, bid_time)
                VALUES (%s, %s, %s, NOW(6))
                """,
                (auction_id, team_id, next_bid)
            )

            # 6. Update Auction: update bid, current bidder, and reset ends_at to NOW(6) + 10s
            cursor.execute(
                """
                UPDATE auctions
                SET current_bid = %s,
                    current_bidder_id = %s,
                    ends_at = DATE_ADD(NOW(6), INTERVAL %s SECOND)
                WHERE id = %s
                """,
                (next_bid, team_id, duration_sec, auction_id)
            )

            # Fetch updated auction with fresh ends_at
            cursor.execute(
                """
                SELECT a.ends_at, TIMESTAMPDIFF(MICROSECOND, NOW(6), a.ends_at) / 1000000.0 as time_remaining
                FROM auctions a WHERE a.id = %s
                """,
                (auction_id,)
            )
            updated = cursor.fetchone()

        logger.info(
            f"BID ACCEPTED: Auction #{auction_id} - Team {team['team_code']} ({team['team_name']}) "
            f"bid INR {next_bid:.2f}. Timer reset to {duration_sec}s."
        )

        # 7. Broadcast bid update to all clients
        if socketio:
            next_amount_after = float(next_bid + increment)
            payload = {
                'auction_id': auction_id,
                'current_bid': float(next_bid),
                'next_bid': next_amount_after,
                'current_bidder_id': team['id'],
                'current_bidder_code': team['team_code'],
                'current_bidder_name': team['team_name'],
                'ends_at_iso': updated['ends_at'].isoformat() if updated['ends_at'] else None,
                'time_remaining': max(0.0, round(float(updated['time_remaining']), 2))
            }
            socketio.emit('bid_update', payload)

        return float(next_bid)

    @staticmethod
    def close_auction(auction_id, socketio=None):
        """Public method to close an auction atomically."""
        with db_transaction() as (conn, cursor):
            return AuctionService._close_auction_internal(auction_id, cursor, socketio=socketio)

    @staticmethod
    def _close_auction_internal(auction_id, cursor, socketio=None):
        """
        Internal implementation of closing an auction within an existing transaction cursor.
        """
        cfg = get_config()
        cursor.execute("SELECT * FROM auctions WHERE id = %s FOR UPDATE", (auction_id,))
        auction = cursor.fetchone()
        if not auction or auction['status'] != 'LIVE':
            return None

        winner_id = auction['current_bidder_id']
        question_id = auction['question_id']
        winning_bid = auction['current_bid']

        broadcast_data = {
            'auction_id': auction_id,
            'question_id': question_id,
            'has_winner': False,
            'winner_team_id': None,
            'winner_team_code': None,
            'winner_team_name': None,
            'winning_bid': float(winning_bid) if winning_bid else 0.0
        }

        if winner_id:
            # There is a winning team!
            cursor.execute("SELECT * FROM teams WHERE id = %s FOR UPDATE", (winner_id,))
            winner = cursor.fetchone()

            # Deduct winning bid atomically from winner's wallet
            WalletService.deduct_winning_bid(winner_id, auction_id, winning_bid, cursor)

            # Update winner stats and status
            new_won = winner['questions_won'] + 1
            new_status = 'COMPLETED' if new_won >= cfg.MAX_QUESTIONS_PER_TEAM else 'WAITING'
            cursor.execute(
                """
                UPDATE teams
                SET questions_won = %s,
                    status = %s
                WHERE id = %s
                """,
                (new_won, new_status, winner_id)
            )

            # Set question status = QUESTION_ACTIVE (associated with winning team)
            cursor.execute("UPDATE questions SET status = 'QUESTION_ACTIVE' WHERE id = %s", (question_id,))

            # Set auction status = ENDED
            cursor.execute(
                """
                UPDATE auctions
                SET status = 'ENDED',
                    winner_team_id = %s
                WHERE id = %s
                """,
                (winner_id, auction_id)
            )

            broadcast_data['has_winner'] = True
            broadcast_data['winner_team_id'] = winner['id']
            broadcast_data['winner_team_code'] = winner['team_code']
            broadcast_data['winner_team_name'] = winner['team_name']

            logger.info(
                f"AUCTION CLOSED: Auction #{auction_id} WON by Team {winner['team_code']} "
                f"for INR {winning_bid:.2f}. Question #{question_id} is now QUESTION_ACTIVE."
            )
        else:
            # No bids placed
            cursor.execute("UPDATE questions SET status = 'AVAILABLE' WHERE id = %s", (question_id,))
            cursor.execute("UPDATE auctions SET status = 'ENDED', winner_team_id = NULL WHERE id = %s", (auction_id,))

            logger.info(f"AUCTION CLOSED: Auction #{auction_id} expired with no bids. Question #{question_id} reset to AVAILABLE.")

        if socketio:
            socketio.emit('auction_ended', broadcast_data)

        return broadcast_data

    @staticmethod
    def cancel_auction(auction_id, socketio=None):
        """Host manually cancels an active auction without deducting any funds."""
        with db_transaction() as (conn, cursor):
            cursor.execute("SELECT * FROM auctions WHERE id = %s FOR UPDATE", (auction_id,))
            auction = cursor.fetchone()
            if not auction or auction['status'] != 'LIVE':
                raise ValueError("Auction is not live or does not exist.")

            question_id = auction['question_id']
            cursor.execute("UPDATE questions SET status = 'AVAILABLE' WHERE id = %s", (question_id,))
            cursor.execute("UPDATE auctions SET status = 'CANCELLED' WHERE id = %s", (auction_id,))

        logger.info(f"AUCTION CANCELLED: Host cancelled Auction #{auction_id}. Question #{question_id} reset to AVAILABLE.")

        if socketio:
            socketio.emit('auction_ended', {
                'auction_id': auction_id,
                'has_winner': False,
                'cancelled': True
            })

    @staticmethod
    def get_recent_bids(auction_id, limit=15):
        """Fetches recent bids for an auction in descending order."""
        sql = """
            SELECT b.id, b.bid_amount, b.bid_time,
                   t.team_code, t.team_name
            FROM bids b
            JOIN teams t ON b.team_id = t.id
            WHERE b.auction_id = %s
            ORDER BY b.id DESC
            LIMIT %s
        """
        rows = fetch_all(sql, (auction_id, limit))
        for r in rows:
            r['bid_time_formatted'] = r['bid_time'].strftime('%H:%M:%S') if r.get('bid_time') else ''
        return rows

    @staticmethod
    def get_auction_history(limit=50):
        """Fetches history of past auctions for host and team dashboards."""
        sql = """
            SELECT a.id, a.starting_bid, a.current_bid as winning_bid, a.status,
                   a.started_at, a.ends_at,
                   q.category, q.question_text, q.reward,
                   t.team_code as winner_code, t.team_name as winner_name
            FROM auctions a
            JOIN questions q ON a.question_id = q.id
            LEFT JOIN teams t ON a.winner_team_id = t.id
            WHERE a.status IN ('ENDED', 'CANCELLED')
            ORDER BY a.id DESC
            LIMIT %s
        """
        rows = fetch_all(sql, (limit,))
        for r in rows:
            r['started_at_formatted'] = r['started_at'].strftime('%d %b %H:%M:%S') if r.get('started_at') else ''
        return rows

    @staticmethod
    def get_team_won_questions(team_id):
        """
        Fetches all questions won by the specified team and their submission/solving status.
        Associates questions via auctions.winner_team_id and auctions.question_id.
        """
        sql = """
            SELECT q.id as question_id, q.category, q.question_text, q.question_image, q.question_type,
                   q.options, q.reward,
                   a.id as auction_id, a.current_bid as winning_bid,
                   s.id as submission_id, s.is_correct, s.submitted_answer, s.reward_credited,
                   s.submitted_at
            FROM auctions a
            JOIN questions q ON a.question_id = q.id
            LEFT JOIN submissions s ON a.id = s.auction_id
            WHERE a.winner_team_id = %s
            ORDER BY a.id ASC
        """
        rows = fetch_all(sql, (team_id,))
        for r in rows:
            r['reward'] = float(r['reward'])
            r['winning_bid'] = float(r['winning_bid']) if r['winning_bid'] else 0.0
            r['reward_credited'] = float(r['reward_credited']) if r['reward_credited'] is not None else 0.0
            r['is_solved'] = r['submission_id'] is not None
            r['submitted_at_formatted'] = r['submitted_at'].strftime('%H:%M:%S') if r.get('submitted_at') else None
        return rows

    @staticmethod
    def get_system_stats():
        """Aggregates high-level system telemetry for host dashboard."""
        registered_teams = fetch_one("SELECT count(*) as c FROM teams WHERE is_active = TRUE")['c']
        disqualified_teams = fetch_one("SELECT count(*) as c FROM teams WHERE is_disqualified = TRUE")['c']
        completed_teams = fetch_one("SELECT count(*) as c FROM teams WHERE questions_completed >= 5")['c']
        total_questions = fetch_one("SELECT count(*) as c FROM questions")['c']
        available_questions = fetch_one("SELECT count(*) as c FROM questions WHERE status = 'AVAILABLE'")['c']
        active_auction = AuctionService.get_active_auction()

        return {
            'registered_teams': registered_teams,
            'disqualified_teams': disqualified_teams,
            'completed_teams': completed_teams,
            'total_questions': total_questions,
            'available_questions': available_questions,
            'active_auction': active_auction
        }
