import logging
from database.db import db_transaction, fetch_all, fetch_one

logger = logging.getLogger(__name__)

class AntiCheatService:
    @staticmethod
    def record_violation(team_id, violation_type, details=None, socketio=None):
        """
        Records an anti-cheating violation for a team.
        Enforces 3-strike rule:
        - Strike 1: Warning
        - Strike 2: Final warning
        - Strike 3: Disqualification from competition
        """
        with db_transaction() as (conn, cursor):
            cursor.execute("SELECT * FROM teams WHERE id = %s FOR UPDATE", (team_id,))
            team = cursor.fetchone()
            if not team:
                raise ValueError("Team not found.")

            new_count = team['violation_count'] + 1
            is_disqualified = team['is_disqualified']

            if new_count >= 3:
                is_disqualified = True

            cursor.execute(
                """
                UPDATE teams
                SET violation_count = %s,
                    is_disqualified = %s
                WHERE id = %s
                """,
                (new_count, is_disqualified, team_id)
            )

            cursor.execute(
                """
                INSERT INTO violations (team_id, violation_type, violation_count, details, occurred_at)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (team_id, violation_type, new_count, details)
            )

        logger.warning(
            f"ANTI-CHEAT VIOLATION: Team {team['team_code']} triggered '{violation_type}'. "
            f"Strike count: {new_count} (Disqualified: {is_disqualified})"
        )

        violation_payload = {
            'team_id': team_id,
            'team_code': team['team_code'],
            'team_name': team['team_name'],
            'violation_type': violation_type,
            'strike_count': new_count,
            'is_disqualified': is_disqualified,
            'details': details
        }

        if socketio:
            socketio.emit('team_violation', violation_payload)
            if is_disqualified:
                from services.leaderboard_service import LeaderboardService
                socketio.emit('leaderboard_update', {'leaderboard': LeaderboardService.get_leaderboard()})

        return violation_payload

    @staticmethod
    def get_all_violations(limit=100):
        """Fetches all logged violations for the host monitor."""
        sql = """
            SELECT v.id, v.team_id, v.violation_type, v.violation_count, v.details, v.occurred_at,
                   t.team_code, t.team_name, t.is_disqualified
            FROM violations v
            JOIN teams t ON v.team_id = t.id
            ORDER BY v.id DESC
            LIMIT %s
        """
        rows = fetch_all(sql, (limit,))
        for r in rows:
            r['occurred_at_formatted'] = r['occurred_at'].strftime('%d %b %Y, %H:%M:%S') if r.get('occurred_at') else ''
        return rows
