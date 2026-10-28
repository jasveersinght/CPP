import os
import sys
import logging

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from config import get_config
from routes.auth import auth_bp
from routes.team import team_bp
from routes.host import host_bp
from sockets.auction_events import register_socket_handlers
from services.reconciliation_service import AuctionWatchdog, ReconciliationService
from database.db import ensure_schema_compatibility

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('math_auction')

def create_app(config_class=None):
    """Application factory for MATH AUCTION."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static')
    )
    
    if config_class is None:
        app.config.from_object(get_config())
    else:
        app.config.from_object(config_class)

    # Initialize SocketIO with threading mode for concurrent workers
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        logger=False,
        engineio_logger=False
    )
    app.extensions['socketio'] = socketio

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(host_bp)

    # Register SocketIO event handlers
    register_socket_handlers(socketio)

    # Error handlers (Prevent leaking stack traces)
    @app.errorhandler(404)
    def handle_not_found(e):
        return render_template('error.html', error_code=404, error_message="Page Not Found"), 404

    @app.errorhandler(500)
    def handle_server_error(e):
        logger.error(f"Internal Server Error: {e}", exc_info=True)
        return render_template('error.html', error_code=500, error_message="An internal server error occurred. Our engineers have been alerted."), 500

    # Startup reconciliation & Watchdog launch
    with app.app_context():
        try:
            # Ensure database schema has newly added columns
            ensure_schema_compatibility()

            logger.info("Running startup reconciliation for expired auctions...")
            ReconciliationService.reconcile_expired_auctions(socketio=socketio)
            
            # Start background watchdog daemon
            interval = app.config.get('WATCHDOG_INTERVAL_SECONDS', 0.5)
            AuctionWatchdog.start_watchdog(socketio=socketio, interval_seconds=interval)
        except Exception as e:
            logger.error(f"Startup initialization error: {e}", exc_info=True)

    return app, socketio

app, socketio = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting MATH AUCTION Server on http://127.0.0.1:{port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
