"""
TerraRisk AI - WSGI Production Entrypoint
Used by Gunicorn, uWSGI, or Waitress in containerized or Linux environments.
Usage:
    gunicorn --workers 4 --bind 0.0.0.0:5000 wsgi:app
"""

import os
import sys

# Ensure backend directory is in python search path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server import app

if __name__ == "__main__":
    # Support running directly via python wsgi.py
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
