import functools
import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
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

@auth_bp.route('/')
def index():
    """Root landing page: redirects to team or host dashboard if logged in, otherwise team login."""
    if session.get('user_type') == 'team':
        return redirect(url_for('team.dashboard'))
    elif session.get('user_type') == 'host':
        return redirect(url_for('host.dashboard'))
    return redirect(url_for('auth.team_login'))

@auth_bp.route('/team/login', methods=['GET', 'POST'])
def team_login():
    """Team login endpoint."""
    if session.get('user_type') == 'team':
        return redirect(url_for('team.dashboard'))

    if request.method == 'POST':
        team_code = request.form.get('team_code', '').strip().upper()
        password = request.form.get('password', '')

        if not team_code or not password:
            flash('Team Code and Password are required.', 'danger')
            return render_template('login_team.html')

        team = fetch_one("SELECT * FROM teams WHERE team_code = %s", (team_code,))
        if not team or not check_password_hash(team['password_hash'], password):
            logger.warning(f"Failed team login attempt for code: {team_code}")
            flash('Invalid Team Code or Password.', 'danger')
            return render_template('login_team.html')

        if not team.get('is_active', True):
            logger.warning(f"Deactivated team attempted login: {team_code}")
            flash('This team account has been deactivated by the tournament director.', 'danger')
            return render_template('login_team.html')

        if team['is_disqualified']:
            logger.warning(f"Disqualified team attempted login: {team_code}")
            flash('This team has been disqualified due to integrity violations.', 'danger')
            return render_template('login_team.html')

        # Clean session and populate team credentials
        session.clear()
        session['user_type'] = 'team'
        session['team_id'] = team['id']
        session['team_code'] = team['team_code']
        session['team_name'] = team['team_name']
        session.permanent = True

        logger.info(f"Team logged in: {team['team_code']} - {team['team_name']}")
        return redirect(url_for('team.dashboard'))

    return render_template('login_team.html')

@auth_bp.route('/host/login', methods=['GET', 'POST'])
def host_login():
    """Host administrator login endpoint."""
    if session.get('user_type') == 'host':
        return redirect(url_for('host.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Username and Password are required.', 'danger')
            return render_template('login_host.html')

        host = fetch_one("SELECT * FROM hosts WHERE username = %s", (username,))
        if not host or not check_password_hash(host['password_hash'], password):
            logger.warning(f"Failed host login attempt for username: {username}")
            flash('Invalid Host Username or Password.', 'danger')
            return render_template('login_host.html')

        # Clean session and populate host credentials
        session.clear()
        session['user_type'] = 'host'
        session['host_id'] = host['id']
        session['host_username'] = host['username']
        session.permanent = True

        logger.info(f"Host logged in: {host['username']}")
        return redirect(url_for('host.dashboard'))

    return render_template('login_host.html')

@auth_bp.route('/logout')
def logout():
    """Universal logout."""
    user_type = session.get('user_type')
    session.clear()
    flash('You have been securely logged out.', 'info')
    if user_type == 'host':
        return redirect(url_for('auth.host_login'))
    return redirect(url_for('auth.team_login'))
