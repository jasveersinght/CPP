import os
import time
import json
import logging
from flask import Blueprint, render_template, request, session, jsonify, current_app
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from routes.auth import host_required
from config import get_config
from database.db import fetch_one, fetch_all, db_transaction
from services.auction_service import AuctionService
from services.wallet_service import WalletService
from services.leaderboard_service import LeaderboardService
from services.anticheat_service import AntiCheatService
from services.reconciliation_service import ReconciliationService
from sockets.auction_events import get_online_team_count
from database.seed_data import reset_test_data as run_reset_test_data

logger = logging.getLogger(__name__)

host_bp = Blueprint('host', __name__)

@host_bp.route('/host/dashboard')
@host_required
def dashboard():
    """Host Control Panel with system status and team management."""
    socketio = current_app.extensions.get('socketio')
    ReconciliationService.reconcile_expired_auctions(socketio=socketio)

    active_auction = AuctionService.get_active_auction()
    recent_bids = AuctionService.get_recent_bids(active_auction['id']) if active_auction else []

    questions = fetch_all("SELECT * FROM questions ORDER BY id ASC")
    teams = fetch_all("SELECT * FROM teams ORDER BY id ASC")
    transactions = WalletService.get_all_transactions(limit=30)
    violations = AntiCheatService.get_all_violations(limit=30)
    auction_history = AuctionService.get_auction_history(limit=30)
    leaderboard = LeaderboardService.get_leaderboard()
    system_stats = AuctionService.get_system_stats()
    system_stats['online_teams'] = get_online_team_count()

    cfg = get_config()
    is_dev_mode = cfg.ENV != 'production'

    return render_template(
        'host_dashboard.html',
        active_auction=active_auction,
        recent_bids=recent_bids,
        questions=questions,
        teams=teams,
        transactions=transactions,
        violations=violations,
        auction_history=auction_history,
        leaderboard=leaderboard,
        system_stats=system_stats,
        is_dev_mode=is_dev_mode,
        default_starting_balance=cfg.STARTING_WALLET_BALANCE
    )

@host_bp.route('/host/live-auction')
@host_required
def live_auction_projector():
    """Projector / Big Screen display for live auditorium presentation."""
    socketio = current_app.extensions.get('socketio')
    ReconciliationService.reconcile_expired_auctions(socketio=socketio)

    active_auction = AuctionService.get_active_auction()
    leaderboard = LeaderboardService.get_leaderboard()

    return render_template(
        'live_auction.html',
        active_auction=active_auction,
        leaderboard=leaderboard
    )

@host_bp.route('/api/host/state')
@host_required
def get_state():
    """Authoritative host state API including live telemetry."""
    socketio = current_app.extensions.get('socketio')
    ReconciliationService.reconcile_expired_auctions(socketio=socketio)

    active_auction = AuctionService.get_active_auction()
    recent_bids = AuctionService.get_recent_bids(active_auction['id']) if active_auction else []
    questions = fetch_all("SELECT id, category, question_text, question_image, question_type, starting_bid, reward, status FROM questions ORDER BY id ASC")
    for q in questions:
        q['starting_bid'] = float(q['starting_bid'])
        q['reward'] = float(q['reward'])

    teams = fetch_all("SELECT id, team_code, team_name, current_balance, questions_won, questions_completed, status, violation_count, is_disqualified, is_active FROM teams ORDER BY id ASC")
    for t in teams:
        t['current_balance'] = float(t['current_balance'])

    system_stats = AuctionService.get_system_stats()
    system_stats['online_teams'] = get_online_team_count()

    return jsonify({
        'active_auction': active_auction,
        'recent_bids': recent_bids,
        'questions': questions,
        'teams': teams,
        'system_stats': system_stats,
        'leaderboard': LeaderboardService.get_leaderboard()
    })

@host_bp.route('/api/host/start-auction', methods=['POST'])
@host_required
def start_auction():
    """Host starts an auction for an available question."""
    data = request.get_json() or {}
    question_id = data.get('question_id')

    if not question_id:
        return jsonify({'success': False, 'error': 'Question ID is required.'}), 400

    socketio = current_app.extensions.get('socketio')

    try:
        auction_id = AuctionService.start_auction(int(question_id), socketio=socketio)
        return jsonify({
            'success': True,
            'message': f'Auction #{auction_id} started successfully!',
            'auction_id': auction_id
        })
    except Exception as e:
        logger.error(f"Error starting auction: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400

@host_bp.route('/api/host/cancel-auction', methods=['POST'])
@host_required
def cancel_auction():
    """Host cancels an active auction without financial penalty."""
    data = request.get_json() or {}
    auction_id = data.get('auction_id')

    if not auction_id:
        return jsonify({'success': False, 'error': 'Auction ID is required.'}), 400

    socketio = current_app.extensions.get('socketio')

    try:
        AuctionService.cancel_auction(int(auction_id), socketio=socketio)
        return jsonify({
            'success': True,
            'message': f'Auction #{auction_id} was successfully cancelled.'
        })
    except Exception as e:
        logger.error(f"Error cancelling auction: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400

@host_bp.route('/api/host/end-auction', methods=['POST'])
@host_required
def end_auction():
    """Host forces active auction to end immediately."""
    data = request.get_json() or {}
    auction_id = data.get('auction_id')

    if not auction_id:
        return jsonify({'success': False, 'error': 'Auction ID is required.'}), 400

    socketio = current_app.extensions.get('socketio')

    try:
        result = AuctionService.close_auction(int(auction_id), socketio=socketio)
        return jsonify({
            'success': True,
            'message': f'Auction #{auction_id} ended.',
            'result': result
        })
    except Exception as e:
        logger.error(f"Error ending auction: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400

@host_bp.route('/api/host/teams/add', methods=['POST'])
@host_required
def add_team():
    """
    Host creates a new team on the fly without SQL editing.
    Enforces unique team code, secure password hashing, and starting balance ledger.
    """
    data = request.get_json() or {}
    team_name = data.get('team_name', '').strip()
    team_code = data.get('team_code', '').strip().upper()
    password = data.get('password', '').strip()

    cfg = get_config()
    default_balance = getattr(cfg, 'STARTING_WALLET_BALANCE', 10000.0)

    try:
        starting_balance = float(data.get('starting_balance', default_balance))
        if starting_balance < 0:
            return jsonify({'success': False, 'error': 'Starting balance cannot be negative.'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid starting balance amount.'}), 400

    if not team_name:
        return jsonify({'success': False, 'error': 'Team name is required.'}), 400
    if not team_code:
        return jsonify({'success': False, 'error': 'Team code is required.'}), 400
    if not password:
        return jsonify({'success': False, 'error': 'Password is required.'}), 400

    # Check uniqueness of team code
    existing = fetch_one("SELECT id FROM teams WHERE team_code = %s", (team_code,))
    if existing:
        return jsonify({'success': False, 'error': f"Team code '{team_code}' already exists. Please choose a unique code."}), 400

    pwd_hash = generate_password_hash(password)

    try:
        with db_transaction() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO teams (
                    team_code, team_name, password_hash, starting_balance, current_balance,
                    questions_won, questions_completed, correct_answers, status,
                    violation_count, is_disqualified, is_active
                )
                VALUES (%s, %s, %s, %s, %s, 0, 0, 0, 'WAITING', 0, FALSE, TRUE)
                """,
                (team_code, team_name, pwd_hash, starting_balance, starting_balance)
            )
            new_team_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO transactions (team_id, transaction_type, amount, description, balance_after)
                VALUES (%s, 'STARTING_BALANCE', %s, 'Initial competition purse credit', %s)
                """,
                (new_team_id, starting_balance, starting_balance)
            )

        logger.info(f"HOST ADDED TEAM: ID={new_team_id}, Code={team_code}, Name='{team_name}', Balance=INR {starting_balance:,.2f}")
        return jsonify({
            'success': True,
            'message': f"Team '{team_name}' ({team_code}) created successfully with ₹{starting_balance:,.2f}!",
            'team': {
                'id': new_team_id,
                'team_code': team_code,
                'team_name': team_name,
                'current_balance': starting_balance
            }
        })
    except Exception as e:
        logger.error(f"Error adding team {team_code}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f"Failed to add team: {str(e)}"}), 500

@host_bp.route('/api/host/teams/toggle-active', methods=['POST'])
@host_required
def toggle_team_active():
    """
    Toggles team active status (soft-disable). Prevents accidental deletion of teams and ledger.
    """
    data = request.get_json() or {}
    team_id = data.get('team_id')

    if not team_id:
        return jsonify({'success': False, 'error': 'Team ID required.'}), 400

    try:
        team = fetch_one("SELECT id, team_code, is_active FROM teams WHERE id = %s", (int(team_id),))
        if not team:
            return jsonify({'success': False, 'error': 'Team not found.'}), 404

        new_status = not bool(team['is_active'])
        with db_transaction() as (conn, cursor):
            cursor.execute("UPDATE teams SET is_active = %s WHERE id = %s", (new_status, team_id))

        status_label = "activated" if new_status else "deactivated"
        logger.info(f"Team {team['team_code']} {status_label} by host.")
        return jsonify({
            'success': True,
            'is_active': new_status,
            'message': f"Team {team['team_code']} has been {status_label}."
        })
    except Exception as e:
        logger.error(f"Error toggling team status: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@host_bp.route('/api/host/reset-test-data', methods=['POST'])
@host_required
def reset_test_data_endpoint():
    """
    Resets all competition rounds, bids, and transactions for a clean test run.
    Strictly blocked in production environments.
    """
    cfg = get_config()
    if cfg.ENV == 'production':
        return jsonify({'success': False, 'error': 'Resetting test data is disabled in production mode.'}), 403

    try:
        run_reset_test_data()
        socketio = current_app.extensions.get('socketio')
        if socketio:
            socketio.emit('leaderboard_update', {'leaderboard': LeaderboardService.get_leaderboard()})
        return jsonify({
            'success': True,
            'message': 'Competition test data successfully reset! All teams have fresh ₹10,000 purses.'
        })
    except Exception as e:
        logger.error(f"Error resetting test data: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f"Failed to reset data: {str(e)}"}), 500

@host_bp.route('/api/host/questions/upload-image', methods=['POST'])
@host_required
def upload_question_image():
    """
    Host uploads a JPEG/PNG photo for a question.
    Saves to static/images/ and links in database.
    """
    try:
        question_id = request.form.get('question_id')
        if not question_id:
            return jsonify({'success': False, 'error': 'Question ID is required.'}), 400

        q = fetch_one("SELECT id, status FROM questions WHERE id = %s", (int(question_id),))
        if not q:
            return jsonify({'success': False, 'error': 'Question not found.'}), 404

        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file uploaded.'}), 400

        file = request.files['image']
        if not file or not file.filename:
            return jsonify({'success': False, 'error': 'Selected file is empty.'}), 400

        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext not in {'jpg', 'jpeg', 'png', 'webp', 'gif'}:
            return jsonify({'success': False, 'error': 'Allowed formats: JPEG, PNG, WEBP, GIF.'}), 400

        upload_folder = os.path.join(current_app.root_path, 'static', 'images')
        os.makedirs(upload_folder, exist_ok=True)

        clean_name = secure_filename(file.filename)
        filename = f"q_{question_id}_{int(time.time())}_{clean_name}"
        save_path = os.path.join(upload_folder, filename)
        file.save(save_path)

        image_url = f"/static/images/{filename}"

        with db_transaction() as (conn, cursor):
            cursor.execute("UPDATE questions SET question_image = %s WHERE id = %s", (image_url, int(question_id)))

        logger.info(f"IMAGE ATTACHED: Host uploaded photo for Question #{question_id} -> {image_url}")

        return jsonify({
            'success': True,
            'message': f'Photo attached to Question #{question_id} successfully!',
            'question_id': int(question_id),
            'image_url': image_url
        })
    except Exception as e:
        logger.error(f"Error uploading question image: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@host_bp.route('/api/host/questions/add', methods=['POST'])
@host_required
def add_new_question():
    """
    Host adds a brand new question with optional photo/diagram upload.
    """
    try:
        category = request.form.get('category', '').strip()
        question_text = request.form.get('question_text', '').strip()
        question_type = request.form.get('question_type', 'Numerical').strip()
        starting_bid = float(request.form.get('starting_bid', 500.0))
        reward = float(request.form.get('reward', 2000.0))
        correct_answer = request.form.get('correct_answer', '').strip()
        options = request.form.get('options', '').strip() or None

        if not category:
            return jsonify({'success': False, 'error': 'Category is required.'}), 400
        if not question_text:
            return jsonify({'success': False, 'error': 'Question description is required.'}), 400
        if not correct_answer:
            return jsonify({'success': False, 'error': 'Correct answer is required.'}), 400

        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                ext = file.filename.rsplit('.', 1)[-1].lower()
                if ext in {'jpg', 'jpeg', 'png', 'webp', 'gif'}:
                    upload_folder = os.path.join(current_app.root_path, 'static', 'images')
                    os.makedirs(upload_folder, exist_ok=True)
                    fname = f"q_new_{int(time.time())}_{secure_filename(file.filename)}"
                    file.save(os.path.join(upload_folder, fname))
                    image_url = f"/static/images/{fname}"

        with db_transaction() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO questions (
                    category, question_text, question_image, question_type,
                    options, starting_bid, reward, correct_answer, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'AVAILABLE')
                """,
                (category, question_text, image_url, question_type, options, starting_bid, reward, correct_answer)
            )
            new_id = cursor.lastrowid

        logger.info(f"QUESTION ADDED: Host added Question #{new_id} ({category})")
        return jsonify({
            'success': True,
            'message': f'Question #{new_id} successfully added to Question Bank!',
            'question_id': new_id,
            'image_url': image_url
        })
    except Exception as e:
        logger.error(f"Error adding question: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

