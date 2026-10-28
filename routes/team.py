import logging
from flask import Blueprint, render_template, request, session, jsonify, current_app
from routes.auth import team_required
from database.db import fetch_one, fetch_all
from services.auction_service import AuctionService
from services.wallet_service import WalletService
from services.answer_service import AnswerService
from services.leaderboard_service import LeaderboardService
from services.anticheat_service import AntiCheatService
from services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)

team_bp = Blueprint('team', __name__)

@team_bp.route('/team/dashboard')
@team_required
def dashboard():
    """Renders the comprehensive Team Dashboard."""
    team_id = session.get('team_id')

    # Multi-layer safety: reconcile expired auctions when dashboard loads
    socketio = current_app.extensions.get('socketio')
    ReconciliationService.reconcile_expired_auctions(socketio=socketio)

    # Fetch latest team data
    team = fetch_one("SELECT * FROM teams WHERE id = %s", (team_id,))
    if not team or not team.get('is_active', True):
        session.clear()
        return jsonify({'error': 'Team not found or inactive'}), 403

    # Fetch active auction if any
    active_auction = AuctionService.get_active_auction()

    # Fetch all won questions in team queue
    won_questions = AuctionService.get_team_won_questions(team_id)

    # Compute current rank
    leaderboard = LeaderboardService.get_leaderboard()
    current_rank = '-'
    for entry in leaderboard:
        if entry['team_id'] == team_id:
            current_rank = entry['rank']
            break

    transactions = WalletService.get_team_transactions(team_id)

    return render_template(
        'team_dashboard.html',
        team=team,
        active_auction=active_auction,
        won_questions=won_questions,
        current_rank=current_rank,
        transactions=transactions[:15]
    )

@team_bp.route('/api/team/state')
@team_required
def get_state():
    """API returning authoritative team state for real-time resynchronization."""
    team_id = session.get('team_id')
    socketio = current_app.extensions.get('socketio')
    ReconciliationService.reconcile_expired_auctions(socketio=socketio)

    team = fetch_one("SELECT * FROM teams WHERE id = %s", (team_id,))
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    active_auction = AuctionService.get_active_auction()
    won_questions = AuctionService.get_team_won_questions(team_id)

    leaderboard = LeaderboardService.get_leaderboard()
    current_rank = '-'
    for entry in leaderboard:
        if entry['team_id'] == team_id:
            current_rank = entry['rank']
            break

    return jsonify({
        'team': {
            'id': team['id'],
            'team_code': team['team_code'],
            'team_name': team['team_name'],
            'current_balance': float(team['current_balance']),
            'starting_balance': float(team['starting_balance']),
            'questions_won': team['questions_won'],
            'questions_completed': team['questions_completed'],
            'correct_answers': team['correct_answers'],
            'status': team['status'],
            'violation_count': team['violation_count'],
            'is_disqualified': bool(team['is_disqualified']),
            'is_active': bool(team.get('is_active', True)),
            'rank': current_rank
        },
        'active_auction': active_auction,
        'won_questions': won_questions
    })

@team_bp.route('/api/team/won-questions')
@team_required
def get_won_questions_api():
    """Returns the team's won questions queue."""
    team_id = session.get('team_id')
    won_questions = AuctionService.get_team_won_questions(team_id)
    return jsonify({
        'won_questions': won_questions,
        'total_won': len(won_questions)
    })

@team_bp.route('/api/team/bid', methods=['POST'])
@team_required
def place_bid_api():
    """HTTP endpoint to place a bid on an active auction."""
    team_id = session.get('team_id')
    data = request.get_json() or {}
    auction_id = data.get('auction_id')

    if not auction_id:
        return jsonify({'success': False, 'error': 'Auction ID required.'}), 400

    socketio = current_app.extensions.get('socketio')

    try:
        new_bid = AuctionService.place_bid(int(auction_id), int(team_id), socketio=socketio)
        return jsonify({
            'success': True,
            'message': f'Bid placed successfully at ₹{new_bid:.2f}',
            'new_bid': new_bid
        })
    except Exception as e:
        logger.warning(f"Bid rejected for Team #{team_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@team_bp.route('/api/team/submit-answer', methods=['POST'])
@team_required
def submit_answer_api():
    """Endpoint for winning team to submit answer for a won auction question."""
    team_id = session.get('team_id')
    data = request.get_json() or {}
    auction_id = data.get('auction_id')
    answer_text = data.get('answer', '').strip()

    if not auction_id or not answer_text:
        return jsonify({'success': False, 'error': 'Auction ID and Answer are required.'}), 400

    socketio = current_app.extensions.get('socketio')

    try:
        result = AnswerService.submit_answer(int(auction_id), int(team_id), answer_text, socketio=socketio)
        updated_won = AuctionService.get_team_won_questions(team_id)
        return jsonify({
            'success': True,
            'result': result,
            'won_questions': updated_won
        })
    except Exception as e:
        logger.warning(f"Answer submission error for Team #{team_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@team_bp.route('/api/team/transactions')
@team_required
def get_transactions():
    """Fetches team's transaction history."""
    team_id = session.get('team_id')
    transactions = WalletService.get_team_transactions(team_id)
    return jsonify({'transactions': transactions})

@team_bp.route('/api/team/violation', methods=['POST'])
@team_required
def report_violation():
    """Reports anti-cheat violation (fullscreen exit, tab switch, page blur)."""
    team_id = session.get('team_id')
    data = request.get_json() or {}
    v_type = data.get('violation_type', 'GENERAL_VIOLATION')
    details = data.get('details', '')

    socketio = current_app.extensions.get('socketio')
    result = AntiCheatService.record_violation(team_id, v_type, details=details, socketio=socketio)
    return jsonify({'success': True, 'violation': result})
