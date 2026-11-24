"""
CampusFind - Unit Tests for Claim and Verification Protocol (tests/test_claim.py)
Tests:
  - Correct answer unlocks finder details and updates status to Claimed
  - Trimming and case insensitivity on answers
  - Wrong answer increments attempt count and hides finder details
  - 3-attempt lockout prevents further claims
  - User cannot claim own post
  - Finder marks item as Returned
"""

import pytest
from database import execute_db, query_db
from werkzeug.security import generate_password_hash


def _create_found_item(app, user_id=2, answer="batman"):
    """Helper to create a found item with a hashed verification answer."""
    with app.app_context():
        ans_hash = generate_password_hash(answer.strip().lower())
        item_id = execute_db(
            """
            INSERT INTO Item (
                user_id, type, title, category, description, location, date,
                status, verification_question, verification_answer_hash
            ) VALUES (?, 'found', 'Found Black Keychain', 'keys', 'Found on bench', 'Main Canteen', '2026-11-20', 'Open', 'Who is on the keychain?', ?)
            """,
            (user_id, ans_hash)
        )
        return item_id


def test_claim_success_correct_answer(client, auth, app):
    """Correct answer approves claim, reveals finder contact, and changes status to Claimed."""
    # Bob (user_id=3) creates a found item
    item_id = _create_found_item(app, user_id=3, answer="batman")

    # Alice (user_id=2) logs in
    auth.login(email='alice@test.edu', password='Password@123')

    # Get CSRF token
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    # Alice submits the correct answer with mixed casing and spaces: "  BatMan  "
    response = client.post(f'/item/{item_id}/claim', data={
        'verification_answer': '  BatMan  ',
        'csrf_token': csrf
    }, follow_redirects=True)

    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert "Verification SUCCESSFUL" in html
    assert "Claim Approved" in html
    assert "bob@test.edu" in html  # Finder's email is revealed to approved claimant

    # Check DB status
    with app.app_context():
        item = query_db("SELECT status FROM Item WHERE id = ?", (item_id,), one=True)
        assert item['status'] == 'Claimed'
        claim = query_db("SELECT * FROM Claim WHERE item_id = ? AND claimant_id = 2", (item_id,), one=True)
        assert claim['result'] == 'approved'
        assert claim['attempts'] == 1


def test_claim_failure_wrong_answer(client, auth, app):
    """Wrong answer increments attempt count and hides finder details."""
    item_id = _create_found_item(app, user_id=3, answer="batman")

    # Alice logs in
    auth.login(email='alice@test.edu', password='Password@123')

    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    # Wrong answer
    response = client.post(f'/item/{item_id}/claim', data={
        'verification_answer': 'superman',
        'csrf_token': csrf
    }, follow_redirects=True)

    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert "Incorrect verification answer" in html
    assert "2 attempt(s) remaining" in html
    assert "bob@test.edu" not in html  # Finder email must NOT be revealed

    # Check DB status remains Open
    with app.app_context():
        item = query_db("SELECT status FROM Item WHERE id = ?", (item_id,), one=True)
        assert item['status'] == 'Open'
        claim = query_db("SELECT attempts, result FROM Claim WHERE item_id = ? AND claimant_id = 2", (item_id,), one=True)
        assert claim['attempts'] == 1
        assert claim['result'] == 'pending'


def test_claim_lockout_after_3_attempts(client, auth, app):
    """User is locked out after 3 failed verification attempts."""
    item_id = _create_found_item(app, user_id=3, answer="batman")

    auth.login(email='alice@test.edu', password='Password@123')

    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    # Attempt 1 (Wrong)
    client.post(f'/item/{item_id}/claim', data={'verification_answer': 'wrong1', 'csrf_token': csrf})
    # Attempt 2 (Wrong)
    client.post(f'/item/{item_id}/claim', data={'verification_answer': 'wrong2', 'csrf_token': csrf})
    # Attempt 3 (Wrong)
    res3 = client.post(f'/item/{item_id}/claim', data={'verification_answer': 'wrong3', 'csrf_token': csrf}, follow_redirects=True)
    
    html3 = res3.data.decode('utf-8')
    assert "exceeded the maximum of 3 attempts" in html3 or "Claim Locked" in html3

    # Attempt 4 (Even with correct answer now, locked out!)
    res4 = client.post(f'/item/{item_id}/claim', data={'verification_answer': 'batman', 'csrf_token': csrf}, follow_redirects=True)
    html4 = res4.data.decode('utf-8')
    assert "maximum limit of 3 failed verification attempts" in html4

    with app.app_context():
        claim = query_db("SELECT attempts, result FROM Claim WHERE item_id = ? AND claimant_id = 2", (item_id,), one=True)
        assert claim['attempts'] == 3
        assert claim['result'] == 'rejected'


def test_cannot_claim_own_post(client, auth, app):
    """A user cannot claim an item they reported themselves."""
    # Alice (user_id=2) creates the item
    item_id = _create_found_item(app, user_id=2, answer="batman")

    auth.login(email='alice@test.edu', password='Password@123')

    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    res = client.post(f'/item/{item_id}/claim', data={
        'verification_answer': 'batman',
        'csrf_token': csrf
    }, follow_redirects=True)

    html = res.data.decode('utf-8')
    assert "You cannot claim an item you reported yourself" in html


def test_mark_item_returned(client, auth, app):
    """Finder can mark a claimed item as Returned."""
    item_id = _create_found_item(app, user_id=2, answer="batman")

    auth.login(email='alice@test.edu', password='Password@123')

    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    res = client.post(f'/item/{item_id}/return', data={'csrf_token': csrf}, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        item = query_db("SELECT status FROM Item WHERE id = ?", (item_id,), one=True)
        assert item['status'] == 'Returned'
