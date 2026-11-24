"""
Pytest Configuration & Fixtures for CampusFind
Provides isolated test databases, Flask test clients, and authenticated sessions.
"""

import os
import tempfile
import pytest
from app import app as flask_app
from database import init_db, execute_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Create and configure a new app instance for each test with isolated database."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test-secret-key-campusfind',
        'WTF_CSRF_ENABLED': False
    })

    with flask_app.app_context():
        init_db(db_path)
        # Seed test admin and standard test user
        admin_pw = generate_password_hash("Admin@123")
        user_pw = generate_password_hash("Password@123")
        
        execute_db(
            "INSERT INTO User (name, email, password_hash, role, active) VALUES ('Admin User', 'admin@test.edu', ?, 'admin', 1)",
            (admin_pw,)
        )
        execute_db(
            "INSERT INTO User (name, email, password_hash, role, active) VALUES ('Alice Student', 'alice@test.edu', ?, 'user', 1)",
            (user_pw,)
        )
        execute_db(
            "INSERT INTO User (name, email, password_hash, role, active) VALUES ('Bob Student', 'bob@test.edu', ?, 'user', 1)",
            (user_pw,)
        )

    yield flask_app

    os.close(db_fd)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


class AuthActions:
    """Helper class to log in and out test users."""
    def __init__(self, client):
        self._client = client

    def login(self, email='alice@test.edu', password='Password@123'):
        # Get csrf token first
        res = self._client.get('/login')
        with self._client.session_transaction() as sess:
            csrf = sess.get('_csrf_token', '')
        return self._client.post('/login', data={
            'email': email,
            'password': password,
            'csrf_token': csrf
        }, follow_redirects=True)

    def login_admin(self):
        return self.login(email='admin@test.edu', password='Admin@123')

    def logout(self):
        return self._client.get('/logout', follow_redirects=True)


@pytest.fixture
def auth(client):
    return AuthActions(client)
