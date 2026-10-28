import os
import sys

# Ensure the root directory is on sys.path so modules (config, database, routes, services, sockets) are importable
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import the configured Flask WSGI application instance
from app import app

# Vercel's Python WSGI runtime discovers 'app' automatically
