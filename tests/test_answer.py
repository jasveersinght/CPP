import unittest
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import init_database, seed_database
from database.db import fetch_one, execute_query
from services.answer_service import AnswerService
from services.auction_service import AuctionService

class TestAnswer(unittest.TestCase):
    def setUp(self):
        init_database()
        seed_database()

    def test_01_numerical_normalization(self):
        """Numerical answers should normalize integers, decimals, and scientific tolerances."""
        self.assertTrue(AnswerService.normalize_and_check('Numerical', '30', '30'))
        self.assertTrue(AnswerService.normalize_and_check('Numerical', '30.0', '30'))
        self.assertTrue(AnswerService.normalize_and_check('Numerical', '30.00', '30'))
        self.assertTrue(AnswerService.normalize_and_check('Numerical', '250', '250'))
        self.assertTrue(AnswerService.normalize_and_check('Numerical', '  250.0  ', '250'))
        self.assertFalse(AnswerService.normalize_and_check('Numerical', '251', '250'))

    def test_02_fraction_and_percentage_normalization(self):
        """Fractions like 5/12 and percentages like 12% should match accurately."""
        self.assertTrue(AnswerService.normalize_and_check('Text', '5/12', '5/12'))
        self.assertTrue(AnswerService.normalize_and_check('Numerical', '12%', '12'))
        self.assertTrue(AnswerService.normalize_and_check('Numerical', '12', '12'))

    def test_03_mcq_normalization(self):
        """MCQ options should match on letter option regardless of formatting."""
        self.assertTrue(AnswerService.normalize_and_check('MCQ', 'A', 'A'))
        self.assertTrue(AnswerService.normalize_and_check('MCQ', 'a', 'A'))
        self.assertTrue(AnswerService.normalize_and_check('MCQ', 'A) 15', 'A'))
        self.assertTrue(AnswerService.normalize_and_check('MCQ', 'A', 'A) 15'))
        self.assertFalse(AnswerService.normalize_and_check('MCQ', 'B', 'A'))

    def test_04_multiple_answer_normalization(self):
        """Multiple Answer questions should match order-independently as sets."""
        self.assertTrue(AnswerService.normalize_and_check('Multiple Answer', 'B, D, E', 'B, D, E'))
        self.assertTrue(AnswerService.normalize_and_check('Multiple Answer', 'E, B, D', 'B, D, E'))
        self.assertTrue(AnswerService.normalize_and_check('Multiple Answer', 'b, d, e', 'B, D, E'))
        self.assertFalse(AnswerService.normalize_and_check('Multiple Answer', 'B, D', 'B, D, E'))

    def test_05_submit_answer_correct_and_reward(self):
        """Winning team submitting correct answer earns reward and updates completed count."""
        q = fetch_one("SELECT * FROM questions LIMIT 1")  # Use any seeded question
        team = fetch_one("SELECT * FROM teams WHERE team_code = 'TEAM001'")

        # Simulate won auction
        execute_query(
            """
            INSERT INTO auctions (question_id, starting_bid, current_bid, current_bidder_id, winner_team_id, status)
            VALUES (%s, %s, %s, %s, %s, 'ENDED')
            """,
            (q['id'], q['starting_bid'], 600.0, team['id'], team['id'])
        )
        auction = fetch_one("SELECT id FROM auctions ORDER BY id DESC LIMIT 1")
        execute_query("UPDATE questions SET status = 'QUESTION_ACTIVE' WHERE id = %s", (q['id'],))

        result = AnswerService.submit_answer(auction['id'], team['id'], q['correct_answer'])
        self.assertTrue(result['is_correct'])
        self.assertEqual(Decimal(str(result['reward_credited'])), Decimal(str(q['reward'])))

        updated_team = fetch_one("SELECT * FROM teams WHERE id = %s", (team['id'],))
        self.assertEqual(updated_team['questions_completed'], 1)
        self.assertEqual(updated_team['correct_answers'], 1)

    def test_06_prevent_duplicate_submissions(self):
        """Duplicate submissions for the same auction must be rejected."""
        q = fetch_one("SELECT * FROM questions LIMIT 1")
        team = fetch_one("SELECT * FROM teams LIMIT 1")
        execute_query(
            """
            INSERT INTO auctions (question_id, starting_bid, current_bid, current_bidder_id, winner_team_id, status)
            VALUES (%s, 500, 500, %s, %s, 'ENDED')
            """,
            (q['id'], team['id'], team['id'])
        )
        auction = fetch_one("SELECT id FROM auctions ORDER BY id DESC LIMIT 1")

        AnswerService.submit_answer(auction['id'], team['id'], q['correct_answer'])

        with self.assertRaises(ValueError):
            AnswerService.submit_answer(auction['id'], team['id'], q['correct_answer'])

    def test_07_unauthorized_team_cannot_submit(self):
        """A team that did not win the auction cannot submit an answer."""
        q = fetch_one("SELECT * FROM questions LIMIT 1")
        winner = fetch_one("SELECT * FROM teams WHERE team_code = 'TEAM001'")
        imposter = fetch_one("SELECT * FROM teams WHERE team_code = 'TEAM002'")
        execute_query(
            """
            INSERT INTO auctions (question_id, starting_bid, current_bid, current_bidder_id, winner_team_id, status)
            VALUES (%s, 500, 500, %s, %s, 'ENDED')
            """,
            (q['id'], winner['id'], winner['id'])
        )
        auction = fetch_one("SELECT id FROM auctions ORDER BY id DESC LIMIT 1")

        with self.assertRaises(ValueError):
            AnswerService.submit_answer(auction['id'], imposter['id'], q['correct_answer'])

if __name__ == '__main__':
    unittest.main()
