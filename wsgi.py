"""
CampusFind - WSGI Application Entry Point (wsgi.py)
Used by Gunicorn in production environments (Render, Linux servers, etc.).
"""

import os
from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    is_debug = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=port, debug=is_debug)
