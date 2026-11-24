"""
CampusFind - Authentication & Security Module (auth.py)
Provides password hashing, session-based CSRF protection, and route decorators.
"""

import secrets
import functools
from flask import session, request, redirect, url_for, flash, abort, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import query_db


def hash_secret(secret_str):
    """Safely hash a password or verification answer (trimmed, lowercased)."""
    if not secret_str:
        return ""
    return generate_password_hash(secret_str.strip())


def verify_secret(hashed_value, candidate_str):
    """Verify a plain string against a hashed value."""
    if not hashed_value or not candidate_str:
        return False
    return check_password_hash(hashed_value, candidate_str.strip())


def generate_csrf_token():
    """Generate or retrieve the session CSRF token."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']


def validate_csrf():
    """Validate CSRF token on POST, PUT, DELETE requests."""
    if request.method in ('POST', 'PUT', 'DELETE'):
        token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        expected = session.get('_csrf_token')
        if not expected or not token or not secrets.compare_digest(expected, token):
            flash('Security session expired or invalid form submission. Please try again.', 'danger')
            abort(400)


def get_current_user():
    """Fetch current logged in user from database, verifying active status."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = query_db("SELECT id, name, email, role, active, created_at FROM User WHERE id = ?", (user_id,), one=True)
    if not user or user['active'] != 1:
        # If user was deactivated or deleted while logged in, terminate session
        session.clear()
        return None
    return user


def login_required(view):
    """Decorator to protect routes requiring authentication."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.path))
        user = get_current_user()
        if not user:
            flash('Your account is inactive or not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        g.user = user
        return view(**kwargs)
    return wrapped_view


def admin_required(view):
    """Decorator to protect admin-only routes."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Please log in as an administrator.', 'warning')
            return redirect(url_for('login', next=request.path))
        user = get_current_user()
        if not user or user['role'] != 'admin':
            flash('Administrator privileges required to access that page.', 'danger')
            return redirect(url_for('index'))
        g.user = user
        return view(**kwargs)
    return wrapped_view
