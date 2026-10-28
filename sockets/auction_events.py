import logging
import threading
from flask import session, request
from flask_socketio import emit
from services.auction_service import AuctionService
from services.leaderboard_service import LeaderboardService
from services.reconciliation_service import ReconciliationService
from services.answer_service import AnswerService
from database.db import fetch_one

logger = logging.getLogger(__name__)

# Thread-safe tracking of connected sockets and teams
_connection_lock = threading.Lock()
_connected_sids = {}  # sid -> {'user_type': str, 'user_id': int}

def get_online_team_count():
    """Returns the count of distinct teams currently connected via WebSocket."""
    with _connection_lock:
        team_ids = {info['user_id'] for info in _connected_sids.values() if info.get('user_type') == 'team' and info.get('user_id')}
        return len(team_ids)

def get_online_team_ids():
    """Returns set of team IDs currently connected."""
    with _connection_lock:
        return {info['user_id'] for info in _connected_sids.values() if info.get('user_type') == 'team' and info.get('user_id')}

def register_socket_handlers(socketio):
    """Registers all real-time Socket.IO event listeners."""

    @socketio.on('connect')
    def handle_connect():
        user_type = session.get('user_type')
        user_id = session.get('team_id') if user_type == 'team' else session.get('host_id')
        logger.info(f"SOCKET CONNECTED: sid={request.sid}, type={user_type}, id={user_id}")

        with _connection_lock:
            _connected_sids[request.sid] = {
                'user_type': user_type,
                'user_id': user_id
            }

        # Broadcast updated online count to hosts
        online_count = get_online_team_count()
        socketio.emit('online_teams_update', {'online_teams': online_count})

        # Trigger lazy reconciliation
        ReconciliationService.reconcile_expired_auctions(socketio=socketio)

        # Emit initial state snapshot
        active_auction = AuctionService.get_active_auction()
        emit('sync_state', {
            'active_auction': active_auction,
            'leaderboard': LeaderboardService.get_leaderboard(),
            'online_teams': online_count
        })

    @socketio.on('disconnect')
    def handle_disconnect():
        with _connection_lock:
            _connected_sids.pop(request.sid, None)

        online_count = get_online_team_count()
        socketio.emit('online_teams_update', {'online_teams': online_count})
        logger.info(f"SOCKET DISCONNECTED: sid={request.sid}, remaining online teams={online_count}")

    @socketio.on('request_sync')
    def handle_request_sync(data=None):
        """Authoritative state resynchronization on client reconnect, tab switch, or poll."""
        ReconciliationService.reconcile_expired_auctions(socketio=socketio)
        active_auction = AuctionService.get_active_auction()

        team_data = None
        active_question = None
        won_questions = []

        if session.get('user_type') == 'team':
            team_id = session.get('team_id')
            team_data = fetch_one(
                "SELECT id, team_code, team_name, current_balance, questions_won, "
                "questions_completed, correct_answers, status, violation_count, is_disqualified, is_active "
                "FROM teams WHERE id = %s",
                (team_id,)
            )
            if team_data:
                team_data['current_balance'] = float(team_data['current_balance'])

            won_questions = AuctionService.get_team_won_questions(team_id)

            if team_data and team_data['status'] in ('WON', 'SOLVING'):
                active_question = fetch_one(
                    """
                    SELECT q.id, q.category, q.question_text, q.question_image, q.question_type,
                           q.options, q.reward, a.id as auction_id
                    FROM auctions a
                    JOIN questions q ON a.question_id = q.id
                    WHERE a.winner_team_id = %s AND q.status = 'QUESTION_ACTIVE'
                    ORDER BY a.id DESC LIMIT 1
                    """,
                    (team_id,)
                )
                if active_question:
                    active_question['reward'] = float(active_question['reward'])

        emit('sync_state', {
            'active_auction': active_auction,
            'team': team_data,
            'active_question': active_question,
            'won_questions': won_questions,
            'leaderboard': LeaderboardService.get_leaderboard(),
            'online_teams': get_online_team_count()
        })

    @socketio.on('place_bid')
    def handle_place_bid(data):
        """Real-time bid placement via WebSocket."""
        if session.get('user_type') != 'team':
            emit('bid_error', {'error': 'Only registered teams can place bids.'})
            return

        team_id = session.get('team_id')
        auction_id = data.get('auction_id')
        if not auction_id:
            emit('bid_error', {'error': 'Auction ID is missing.'})
            return

        try:
            new_bid = AuctionService.place_bid(int(auction_id), int(team_id), socketio=socketio)
            emit('bid_success', {
                'auction_id': auction_id,
                'bid_amount': new_bid,
                'message': f'Bid placed at INR {new_bid:.2f}'
            })
        except Exception as e:
            logger.warning(f"WebSocket bid error for team {team_id}: {e}")
            emit('bid_error', {'error': str(e)})

    @socketio.on('submit_answer')
    def handle_submit_answer(data):
        """Real-time answer submission via WebSocket."""
        if session.get('user_type') != 'team':
            emit('answer_error', {'error': 'Only registered teams can submit answers.'})
            return

        team_id = session.get('team_id')
        auction_id = data.get('auction_id')
        answer_text = data.get('answer', '').strip()

        if not auction_id or not answer_text:
            emit('answer_error', {'error': 'Auction ID and Answer are required.'})
            return

        try:
            result = AnswerService.submit_answer(int(auction_id), int(team_id), answer_text, socketio=socketio)
            emit('answer_success', {'result': result})
            # Also emit updated won questions to this team
            updated_won = AuctionService.get_team_won_questions(team_id)
            emit('won_questions_update', {'won_questions': updated_won})
        except Exception as e:
            logger.warning(f"WebSocket answer error for team {team_id}: {e}")
            emit('answer_error', {'error': str(e)})
