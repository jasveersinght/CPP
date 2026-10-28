import logging
import threading
import time
from database.db import db_transaction, fetch_all

logger = logging.getLogger(__name__)

class ReconciliationService:
    _last_run = 0.0
    _last_error_log = 0.0
    _run_lock = threading.Lock()

    @staticmethod
    def reconcile_expired_auctions(socketio=None, force=False):
        """
        Scans for auctions with status = 'LIVE' and ends_at <= NOW(6).
        Safely closes each expired auction within an atomic transaction.
        Throttled to at most once per 250ms to prevent query storms during 80-client bursts.
        """
        now = time.time()
        if not force:
            with ReconciliationService._run_lock:
                if now - ReconciliationService._last_run < 0.25:
                    return []
                ReconciliationService._last_run = now

        from services.auction_service import AuctionService

        expired_auctions = []
        try:
            # Query candidate expired auctions
            sql = """
                SELECT id FROM auctions
                WHERE status = 'LIVE' AND ends_at <= NOW(6)
            """
            rows = fetch_all(sql)
            if not rows:
                return []

            for row in rows:
                auction_id = row['id']
                try:
                    closed_info = AuctionService.close_auction(auction_id, socketio=socketio)
                    if closed_info:
                        expired_auctions.append(closed_info)
                        logger.info(f"WATCHDOG RECONCILIATION: Successfully closed expired auction #{auction_id}")
                except Exception as e:
                    logger.error(f"Error reconciling expired auction #{auction_id}: {e}", exc_info=True)

        except Exception as e:
            err_str = str(e)
            if "doesn't exist" in err_str or "1146" in err_str:
                return []
            now_err = time.time()
            if now_err - ReconciliationService._last_error_log > 30.0:
                ReconciliationService._last_error_log = now_err
                logger.error(f"Error during watchdog reconciliation scan: {e}")

        return expired_auctions


class AuctionWatchdog:
    """
    Background daemon thread that periodically checks for expired auctions
    and closes them authoritatively.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self, socketio=None, interval_seconds=0.5):
        self.socketio = socketio
        self.interval_seconds = interval_seconds
        self._running = False
        self._thread = None

    @classmethod
    def start_watchdog(cls, socketio=None, interval_seconds=0.5):
        with cls._lock:
            if cls._instance is None:
                cls._instance = AuctionWatchdog(socketio, interval_seconds)
                cls._instance.start()
            return cls._instance

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, name="AuctionWatchdogThread", daemon=True)
            self._thread.start()
            logger.info(f"Auction Watchdog background worker started with {self.interval_seconds}s interval.")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Auction Watchdog background worker stopped.")

    def _run_loop(self):
        while self._running:
            try:
                ReconciliationService.reconcile_expired_auctions(socketio=self.socketio, force=True)
            except Exception as e:
                logger.error(f"Watchdog loop iteration encountered error: {e}", exc_info=True)
            time.sleep(self.interval_seconds)
