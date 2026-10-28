import logging
from database.db import fetch_all

logger = logging.getLogger(__name__)

class LeaderboardService:
    @staticmethod
    def get_leaderboard():
        """
        Calculates and returns the authoritative live competition leaderboard.
        Ranked by:
        1. Current Wallet Balance (DESC)
        2. Correct Answers count (DESC)
        3. Questions Won count (DESC)
        4. Questions Completed (ASC)
        """
        sql = """
            SELECT id as team_id, team_code, team_name, current_balance,
                   questions_won, questions_completed, correct_answers,
                   status, is_disqualified, violation_count
            FROM teams
            ORDER BY
                is_disqualified ASC,
                current_balance DESC,
                correct_answers DESC,
                questions_won DESC,
                questions_completed ASC,
                id ASC
        """
        rows = fetch_all(sql)
        leaderboard = []
        rank = 1
        for row in rows:
            leaderboard.append({
                'rank': rank,
                'team_id': row['team_id'],
                'team_code': row['team_code'],
                'team_name': row['team_name'],
                'current_balance': float(row['current_balance']),
                'questions_won': row['questions_won'],
                'questions_completed': row['questions_completed'],
                'correct_answers': row['correct_answers'],
                'status': row['status'],
                'is_disqualified': bool(row['is_disqualified']),
                'violation_count': row['violation_count']
            })
            rank += 1
        return leaderboard
