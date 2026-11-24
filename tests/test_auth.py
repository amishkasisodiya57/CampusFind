"""
CampusFind - Authentication & Authorization Tests (tests/test_auth.py)
Tests:
  - User registration with validation
  - Duplicate email detection
  - Login success & invalid credentials
  - Deactivated user blocking
  - Admin access control & toggle user status
"""

import pytest
from database import query_db, execute_db


def test_registration_success(client, app):
    """Registering a new student account succeeds."""
    client.get('/register')
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    res = client.post('/register', data={
        'name': 'New Student',
        'email': 'newstudent@college.edu',
        'password': 'Password@123',
        'csrf_token': csrf
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Welcome, New Student!" in res.data

    with app.app_context():
        user = query_db("SELECT * FROM User WHERE email = 'newstudent@college.edu'", one=True)
        assert user is not None
        assert user['name'] == 'New Student'
        assert user['role'] == 'user'


def test_registration_duplicate_email(client):
    """Registering with an already existing email is rejected."""
    client.get('/register')
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    res = client.post('/register', data={
        'name': 'Duplicate Alice',
        'email': 'alice@test.edu',  # Already seeded
        'password': 'Password@123',
        'csrf_token': csrf
    }, follow_redirects=True)

    assert b"An account with that email already exists" in res.data


def test_login_success_and_logout(client, auth):
    """User can log in with valid credentials and log out."""
    res = auth.login(email='alice@test.edu', password='Password@123')
    assert res.status_code == 200
    assert b"Welcome back, Alice Student!" in res.data

    # Logout
    res_logout = auth.logout()
    assert b"You have been safely logged out" in res_logout.data


def test_login_invalid_password(auth):
    """Login with wrong password fails with friendly warning."""
    res = auth.login(email='alice@test.edu', password='WrongPassword!')
    assert b"Invalid email or password" in res.data


def test_deactivated_user_cannot_login(client, auth, app):
    """Deactivated user account is blocked from signing in."""
    with app.app_context():
        execute_db("UPDATE User SET active = 0 WHERE email = 'bob@test.edu'")

    res = auth.login(email='bob@test.edu', password='Password@123')
    assert b"Your account has been deactivated" in res.data


def test_admin_access_control(client, auth):
    """Regular users are blocked from admin panel; admin can access."""
    # Regular user Alice attempts to view admin panel
    auth.login(email='alice@test.edu', password='Password@123')
    res_user = client.get('/admin', follow_redirects=True)
    assert b"Administrator privileges required" in res_user.data

    auth.logout()

    # Admin logs in
    auth.login_admin()
    res_admin = client.get('/admin')
    assert res_admin.status_code == 200
    assert b"Admin Control Center" in res_admin.data


def test_admin_toggle_user_status(client, auth, app):
    """Admin can deactivate and reactivate a user account."""
    auth.login_admin()
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    # Deactivate Alice (id=2)
    res = client.post('/admin/user/2/toggle', data={'csrf_token': csrf}, follow_redirects=True)
    assert res.status_code == 200
    assert b"deactivated" in res.data

    with app.app_context():
        user = query_db("SELECT active FROM User WHERE id = 2", one=True)
        assert user['active'] == 0

    # Reactivate Alice
    res2 = client.post('/admin/user/2/toggle', data={'csrf_token': csrf}, follow_redirects=True)
    assert b"reactivated" in res2.data

    with app.app_context():
        user = query_db("SELECT active FROM User WHERE id = 2", one=True)
        assert user['active'] == 1
