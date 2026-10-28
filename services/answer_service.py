import re
import math
import logging
from decimal import Decimal
from config import get_config
from database.db import db_transaction, fetch_one, fetch_all
from services.wallet_service import WalletService

logger = logging.getLogger(__name__)

class AnswerService:
    @staticmethod
    def normalize_and_check(question_type, submitted_raw, correct_raw):
        """
        Authoritatively checks whether the submitted answer matches the correct answer.
        Supports:
        - Numerical: integers, floats, scientific tolerance, fractions (e.g. 5/12).
        - MCQ: Letter option matching (e.g. 'A' matches 'A) 15' or 'a').
        - Text: Whitespace-normalized, case-insensitive string matching.
        - Multiple Answer: Comma/space delimited set comparison, order-independent.
        """
        if submitted_raw is None or correct_raw is None:
            return False

        sub_str = str(submitted_raw).strip()
        cor_str = str(correct_raw).strip()

        if not sub_str:
            return False

        if question_type == 'Numerical':
            return AnswerService._check_numerical(sub_str, cor_str)

        elif question_type == 'MCQ':
            return AnswerService._check_mcq(sub_str, cor_str)

        elif question_type == 'Multiple Answer':
            return AnswerService._check_multiple_answer(sub_str, cor_str)

        elif question_type == 'Text':
            return AnswerService._check_text(sub_str, cor_str)

        # Fallback to normalized text
        return AnswerService._check_text(sub_str, cor_str)

    @staticmethod
    def _parse_number_or_fraction(s):
        """Parses a string into a float, supporting fractions like '5/12' or percentages like '12%'."""
        s = s.strip().rstrip('%').replace(',', '')
        if '/' in s:
            parts = s.split('/')
            if len(parts) == 2:
                try:
                    num = float(parts[0].strip())
                    den = float(parts[1].strip())
                    if den != 0:
                        return num / den
                except ValueError:
                    pass
        try:
            return float(s)
        except ValueError:
            return None

    @staticmethod
    def _check_numerical(submitted, correct):
        sub_val = AnswerService._parse_number_or_fraction(submitted)
        cor_val = AnswerService._parse_number_or_fraction(correct)

        if sub_val is not None and cor_val is not None:
            return math.isclose(sub_val, cor_val, rel_tol=1e-5, abs_tol=1e-5)

        # Fallback to string equality after basic normalization
        return submitted.lower().replace(" ", "") == correct.lower().replace(" ", "")

    @staticmethod
    def _check_mcq(submitted, correct):
        # Extract leading letter option, e.g., 'A' from 'A) 15' or 'A.' or 'option a'
        sub_match = re.match(r'^([A-Za-z])', submitted.strip())
        cor_match = re.match(r'^([A-Za-z])', correct.strip())

        if sub_match and cor_match:
            return sub_match.group(1).upper() == cor_match.group(1).upper()

        return submitted.strip().lower() == correct.strip().lower()

    @staticmethod
    def _check_multiple_answer(submitted, correct):
        # Split by commas, semicolons, or spaces, extract individual tokens/letters
        def extract_tokens(text):
            parts = re.split(r'[,; ]+', text.strip().upper())
            tokens = set()
            for p in parts:
                p_clean = re.sub(r'[^A-Z0-9]', '', p)
                if p_clean:
                    tokens.add(p_clean)
            return tokens

        sub_tokens = extract_tokens(submitted)
        cor_tokens = extract_tokens(correct)
        return sub_tokens == cor_tokens and len(cor_tokens) > 0

    @staticmethod
    def _check_text(submitted, correct):
        # Lowercase, collapse spaces, remove special trailing punctuation
        def clean(s):
            s = s.lower().strip()
            s = re.sub(r'[.,;!?"\']+$', '', s)
            return re.sub(r'\s+', ' ', s)

        # Also check if it's a fractional equivalence like 5/12
        if '/' in submitted and '/' in correct:
            num_sub = AnswerService._parse_number_or_fraction(submitted)
            num_cor = AnswerService._parse_number_or_fraction(correct)
            if num_sub is not None and num_cor is not None:
                if math.isclose(num_sub, num_cor, rel_tol=1e-5, abs_tol=1e-5):
                    return True

        return clean(submitted) == clean(correct)

    @staticmethod
    def submit_answer(auction_id, team_id, answer_text, socketio=None):
        """
        Validates and processes a team's answer submission atomically.
        """
        cfg = get_config()
        max_questions = cfg.MAX_QUESTIONS_PER_TEAM

        with db_transaction() as (conn, cursor):
            # 1. Verify auction exists and ended
            cursor.execute("SELECT * FROM auctions WHERE id = %s FOR UPDATE", (auction_id,))
            auction = cursor.fetchone()
            if not auction:
                raise ValueError("Auction not found.")
            if auction['status'] != 'ENDED':
                raise ValueError("Auction is still active; answers can only be submitted after auction ends.")
            if auction['winner_team_id'] != team_id:
                raise ValueError("Unauthorized: Only the winning team can submit an answer for this question.")

            # 2. Check duplicate submission
            cursor.execute("SELECT id FROM submissions WHERE auction_id = %s FOR UPDATE", (auction_id,))
            if cursor.fetchone():
                raise ValueError("An answer has already been submitted for this auction question.")

            # 3. Lock question
            question_id = auction['question_id']
            cursor.execute("SELECT * FROM questions WHERE id = %s FOR UPDATE", (question_id,))
            question = cursor.fetchone()
            if not question:
                raise ValueError("Question not found.")

            # 4. Check answer correctness
            is_correct = AnswerService.normalize_and_check(
                question['question_type'],
                answer_text,
                question['correct_answer']
            )

            reward_amount = Decimal(str(question['reward'])) if is_correct else Decimal('0.00')

            # 5. Insert submission record
            cursor.execute(
                """
                INSERT INTO submissions (auction_id, team_id, question_id, submitted_answer, is_correct, reward_credited)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (auction_id, team_id, question_id, answer_text, is_correct, reward_amount)
            )

            # 6. Lock and update team
            cursor.execute("SELECT * FROM teams WHERE id = %s FOR UPDATE", (team_id,))
            team = cursor.fetchone()

            # Disqualification enforcement: reject if team is disqualified (3 strikes)
            if team['is_disqualified']:
                raise ValueError("Team is disqualified from the competition due to integrity violations.")

            new_completed = team['questions_completed'] + 1
            new_correct = team['correct_answers'] + (1 if is_correct else 0)
            new_status = 'COMPLETED' if new_completed >= max_questions else 'WAITING'

            cursor.execute(
                """
                UPDATE teams
                SET questions_completed = %s,
                    correct_answers = %s,
                    status = %s
                WHERE id = %s
                """,
                (new_completed, new_correct, new_status, team_id)
            )

            # 7. Mark question completed
            cursor.execute("UPDATE questions SET status = 'COMPLETED' WHERE id = %s", (question_id,))

            # 8. If correct, credit reward via WalletService
            if is_correct:
                WalletService.credit_reward(team_id, auction_id, reward_amount, cursor)

        # Refresh team's new balance
        updated_team = fetch_one("SELECT * FROM teams WHERE id = %s", (team_id,))

        result_data = {
            'auction_id': auction_id,
            'question_id': question_id,
            'team_id': team_id,
            'team_code': updated_team['team_code'],
            'team_name': updated_team['team_name'],
            'is_correct': is_correct,
            'reward_credited': float(reward_amount),
            'new_balance': float(updated_team['current_balance']),
            'questions_completed': updated_team['questions_completed'],
            'correct_answers': updated_team['correct_answers'],
            'status': updated_team['status']
        }

        if is_correct:
            logger.info(f"ANSWER CORRECT: Team {updated_team['team_code']} answered Question #{question_id} correctly! +INR {reward_amount:.2f}")
        else:
            logger.info(f"ANSWER WRONG: Team {updated_team['team_code']} answered Question #{question_id} incorrectly.")

        if socketio:
            socketio.emit('answer_result', result_data)
            from services.leaderboard_service import LeaderboardService
            socketio.emit('leaderboard_update', {'leaderboard': LeaderboardService.get_leaderboard()})

        return result_data
