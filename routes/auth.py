import functools
import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database.db import fetch_one

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

def team_required(view):
    """Decorator requiring a logged-in team."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user_type') != 'team' or not session.get('team_id'):
            flash('Please log in as a team to access this page.', 'warning')
            return redirect(url_for('auth.team_login'))
        return view(**kwargs)
    return wrapped_view

def host_required(view):
    """Decorator requiring a logged-in host."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user_type') != 'host' or not session.get('host_id'):
            flash('Please log in as host administrator to access this page.', 'warning')
            return redirect(url_for('auth.host_login'))
        return view(**kwargs)
    return wrapped_view

def _process_team_login(team_code, password):
    """Helper to authenticate and establish a team session."""
    team_code = (team_code or '').strip().upper()
    if not team_code or not password:
        flash('Team Code and Password are required.', 'danger')
        return render_template('login.html', active_role='team')

    team = fetch_one("SELECT * FROM teams WHERE team_code = %s", (team_code,))
    if not team or not check_password_hash(team['password_hash'], password):
        logger.warning(f"Failed team login attempt for code: {team_code}")
        flash('Invalid Team Code or Password.', 'danger')
        return render_template('login.html', active_role='team')

    if not team.get('is_active', True):
        logger.warning(f"Deactivated team attempted login: {team_code}")
        flash('This team account has been deactivated by the tournament director.', 'danger')
        return render_template('login.html', active_role='team')

    if team['is_disqualified']:
        logger.warning(f"Disqualified team attempted login: {team_code}")
        flash('This team has been disqualified due to integrity violations.', 'danger')
        return render_template('login.html', active_role='team')

    # Clean session and populate team credentials
    session.clear()
    session['user_type'] = 'team'
    session['team_id'] = team['id']
    session['team_code'] = team['team_code']
    session['team_name'] = team['team_name']
    session.permanent = True

    logger.info(f"Team logged in: {team['team_code']} - {team['team_name']}")
    return redirect(url_for('team.dashboard'))

def _process_host_login(username, password):
    """Helper to authenticate and establish a host administrator session."""
    username = (username or '').strip()
    if not username or not password:
        flash('Username and Password are required.', 'danger')
        return render_template('login.html', active_role='host')

    host = fetch_one("SELECT * FROM hosts WHERE username = %s", (username,))
    if not host or not check_password_hash(host['password_hash'], password):
        logger.warning(f"Failed host login attempt for username: {username}")
        flash('Invalid Host Username or Password.', 'danger')
        return render_template('login.html', active_role='host')

    # Clean session and populate host credentials
    session.clear()
    session['user_type'] = 'host'
    session['host_id'] = host['id']
    session['host_username'] = host['username']
    session.permanent = True

    logger.info(f"Host logged in: {host['username']}")
    return redirect(url_for('host.dashboard'))

@auth_bp.route('/')
def index():
    """Root landing page: redirects to team or host dashboard if logged in, otherwise unified login."""
    if session.get('user_type') == 'team':
        return redirect(url_for('team.dashboard'))
    elif session.get('user_type') == 'host':
        return redirect(url_for('host.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login endpoint supporting both Team (User) and Host (Admin) authentication."""
    if session.get('user_type') == 'team':
        return redirect(url_for('team.dashboard'))
    elif session.get('user_type') == 'host':
        return redirect(url_for('host.dashboard'))

    active_role = request.args.get('role', 'team').lower()
    if active_role not in ('team', 'host'):
        active_role = 'team'

    if request.method == 'POST':
        role = request.form.get('role', '').strip().lower()
        if not role:
            # Infer role if not explicitly passed
            if request.form.get('username'):
                role = 'host'
            else:
                role = 'team'

        if role == 'host':
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            return _process_host_login(username, password)
        else:
            team_code = request.form.get('team_code', '')
            password = request.form.get('password', '')
            return _process_team_login(team_code, password)

    return render_template('login.html', active_role=active_role)

@auth_bp.route('/team/login', methods=['GET', 'POST'])
def team_login():
    """Dedicated / legacy team login endpoint (renders unified login with team active or handles post)."""
    if session.get('user_type') == 'team':
        return redirect(url_for('team.dashboard'))

    if request.method == 'POST':
        team_code = request.form.get('team_code', '')
        password = request.form.get('password', '')
        return _process_team_login(team_code, password)

    return render_template('login.html', active_role='team')

@auth_bp.route('/host/login', methods=['GET', 'POST'])
def host_login():
    """Dedicated / legacy host login endpoint (renders unified login with host active or handles post)."""
    if session.get('user_type') == 'host':
        return redirect(url_for('host.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        return _process_host_login(username, password)

    return render_template('login.html', active_role='host')

@auth_bp.route('/logout')
def logout():
    """Universal logout endpoint."""
    user_type = session.get('user_type')
    session.clear()
    flash('You have been securely logged out.', 'info')
    if user_type == 'host':
        return redirect(url_for('auth.login', role='host'))
    return redirect(url_for('auth.login', role='team'))
