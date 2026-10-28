import pymysql
import pymysql.cursors
import logging
import queue
import threading
import time
from contextlib import contextmanager
from config import get_config

logger = logging.getLogger(__name__)

class ConnectionPool:
    """Thread-safe connection pool for PyMySQL supporting high-concurrency event scale."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConnectionPool, cls).__new__(cls)
                cls._instance._init_pool()
            return cls._instance

    def _init_pool(self):
        self._pool = queue.Queue()
        self._created_connections = 0
        self._pool_lock = threading.Lock()

    def _create_new_raw_connection(self):
        cfg = get_config().get_db_config()
        conn = pymysql.connect(
            host=cfg['host'],
            port=cfg['port'],
            user=cfg['user'],
            password=cfg['password'],
            database=cfg['database'],
            charset=cfg['charset'],
            autocommit=cfg['autocommit'],
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn

    def get_connection(self, timeout=10.0):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                conn = self._pool.get_nowait()
                try:
                    conn.ping(reconnect=True)
                    return conn
                except Exception:
                    try:
                        conn._raw_close()
                    except Exception:
                        pass
                    with self._pool_lock:
                        self._created_connections = max(0, self._created_connections - 1)
            except queue.Empty:
                cfg_obj = get_config()
                max_total = getattr(cfg_obj, 'DB_POOL_SIZE', 50) + getattr(cfg_obj, 'DB_POOL_MAX_OVERFLOW', 30)
                with self._pool_lock:
                    if self._created_connections < max_total:
                        self._created_connections += 1
                        try:
                            return self._create_new_raw_connection()
                        except Exception:
                            self._created_connections -= 1
                            raise
                time.sleep(0.01)

        # Fallback wait on queue
        try:
            conn = self._pool.get(timeout=2.0)
            conn.ping(reconnect=True)
            return conn
        except Exception:
            return self._create_new_raw_connection()

    def release_connection(self, conn, discard=False):
        if not conn:
            return
        if discard:
            try:
                conn._raw_close()
            except Exception:
                pass
            with self._pool_lock:
                self._created_connections = max(0, self._created_connections - 1)
            return

        try:
            # Rollback any uncommitted transaction state before returning to pool
            conn.rollback()
            self._pool.put_nowait(conn)
        except Exception:
            try:
                conn._raw_close()
            except Exception:
                pass
            with self._pool_lock:
                self._created_connections = max(0, self._created_connections - 1)

_global_pool = ConnectionPool()

def get_db_connection():
    """
    Returns a pooled PyMySQL connection.
    Calling conn.close() safely returns the connection to the pool.
    """
    conn = _global_pool.get_connection()
    if not hasattr(conn, '_raw_close'):
        conn._raw_close = conn.close

    # Monkey patch close to return to pool
    conn.close = lambda: _global_pool.release_connection(conn)
    return conn

@contextmanager
def db_transaction():
    """
    Context manager providing an ACID transactional connection and cursor.
    Automatically rolls back on any exception and commits on clean exit.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield conn, cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction rolled back due to error: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

@contextmanager
def get_db_cursor():
    """Read-only or auto-commit cursor helper."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
        conn.close()

def execute_query(sql, params=None):
    """Execute query with automatic commit."""
    with db_transaction() as (conn, cursor):
        cursor.execute(sql, params or ())
        return cursor.lastrowid

def fetch_one(sql, params=None):
    """Execute select query and return single row dict."""
    with get_db_cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchone()

def fetch_all(sql, params=None):
    """Execute select query and return all row dicts."""
    with get_db_cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchall()
