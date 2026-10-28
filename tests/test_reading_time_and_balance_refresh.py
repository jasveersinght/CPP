import unittest
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import init_database, seed_database
from database.db import fetch_one, execute_query
from services.auction_service import AuctionService
from services.answer_service import AnswerService
from config import get_config

class TestReadingTimeAndBalanceRefresh(unittest.TestCase):
    def setUp(self):
        init_database()
        seed_database()

    def test_01_question_reading_time_blocks_bids(self):
        """Auction initializes in 10s reading phase and rejects bids until reading time finishes."""
        q = fetch_one("SELECT id, starting_bid FROM questions WHERE id = 1")
        auction_id = AuctionService.start_auction(q['id'], reading_duration=10, bidding_duration=30)

        active = AuctionService.get_active_auction()
        self.assertIsNotNone(active)
        self.assertEqual(active['phase'], 'READING')
        self.assertGreater(active['reading_time_remaining'], 0.0)
        self.assertEqual(active['reading_duration'], 10)
        self.assertEqual(active['bidding_duration'], 30)

        # Attempting to bid during reading phase must be rejected
        team = fetch_one("SELECT id FROM teams WHERE team_code = 'TEAM001'")
        with self.assertRaises(ValueError) as ctx:
            AuctionService.place_bid(auction_id, team['id'])
        self.assertIn("Question reading time in progress", str(ctx.exception))

    def test_02_transition_to_bidding_allows_bids_and_30s_reset(self):
        """Once reading phase elapses, bidding opens for 30s and valid bids reset timer to 30s."""
        q = fetch_one("SELECT id, starting_bid FROM questions WHERE id = 1")
        auction_id = AuctionService.start_auction(q['id'], reading_duration=10, bidding_duration=30)

        # Fast forward reading phase past bidding_starts_at
        execute_query("UPDATE auctions SET bidding_starts_at = DATE_SUB(NOW(6), INTERVAL 1 SECOND) WHERE id = %s", (auction_id,))

        active = AuctionService.get_active_auction()
        self.assertEqual(active['phase'], 'BIDDING')

        team1 = fetch_one("SELECT id FROM teams WHERE team_code = 'TEAM001'")
        team2 = fetch_one("SELECT id FROM teams WHERE team_code = 'TEAM002'")

        # First bid accepted
        bid1 = AuctionService.place_bid(auction_id, team1['id'])
        self.assertEqual(bid1, float(q['starting_bid']))

        # Verify ends_at is reset to ~30 seconds in future
        auction_after = fetch_one(
            "SELECT TIMESTAMPDIFF(MICROSECOND, NOW(6), ends_at) / 1000000.0 as rem FROM auctions WHERE id = %s",
            (auction_id,)
        )
        self.assertGreaterEqual(float(auction_after['rem']), 28.0)
        self.assertLessEqual(float(auction_after['rem']), 31.0)

        # Second bid accepted and resets timer
        bid2 = AuctionService.place_bid(auction_id, team2['id'])
        self.assertEqual(bid2, float(q['starting_bid']) + 10.0)

    def test_03_answer_submission_instant_balance_update(self):
        """Submitting a correct answer immediately returns updated balance and credits purse in database."""
        q = fetch_one("SELECT * FROM questions WHERE id = 1")
        team = fetch_one("SELECT * FROM teams WHERE team_code = 'TEAM001'")
        initial_balance = Decimal(str(team['current_balance']))

        # Simulate won auction
        execute_query(
            """
            INSERT INTO auctions (question_id, starting_bid, current_bid, current_bidder_id, winner_team_id, status)
            VALUES (%s, %s, %s, %s, %s, 'ENDED')
            """,
            (q['id'], q['starting_bid'], 500.0, team['id'], team['id'])
        )
        auction = fetch_one("SELECT id FROM auctions ORDER BY id DESC LIMIT 1")
        execute_query("UPDATE questions SET status = 'QUESTION_ACTIVE' WHERE id = %s", (q['id'],))

        result = AnswerService.submit_answer(auction['id'], team['id'], q['correct_answer'])

        self.assertTrue(result['is_correct'])
        expected_new_balance = float(initial_balance + Decimal(str(q['reward'])))
        self.assertEqual(result['new_balance'], expected_new_balance)

        # Check DB reflects new balance immediately
        refreshed_team = fetch_one("SELECT * FROM teams WHERE id = %s", (team['id'],))
        self.assertEqual(float(refreshed_team['current_balance']), expected_new_balance)
        self.assertEqual(refreshed_team['correct_answers'], 1)
        self.assertEqual(refreshed_team['questions_completed'], 1)

    def test_04_sound_js_defines_playRewardSound(self):
        """Verifies static/js/sound.js defines playRewardSound so browser won't crash on answer evaluation."""
        sound_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'js', 'sound.js')
        with open(sound_file, 'r', encoding='utf-8') as f:
            code = f.read()

        self.assertIn("playRewardSound", code, "sound.js must implement playRewardSound()")
        self.assertIn("playBiddingOpenSound", code, "sound.js must implement playBiddingOpenSound()")

if __name__ == '__main__':
    unittest.main()
