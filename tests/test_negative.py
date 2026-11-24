"""
CampusFind - Negative & Edge Case Tests (tests/test_negative.py)
Tests:
  - Missing mandatory fields when creating posts
  - Missing verification question/answer for found items
  - Disallowed file types for photos
  - Unauthenticated route protection
  - Unauthorized edits and deletions
  - Non-existent resource handling (404)
"""

import io
import pytest
from database import execute_db


def test_post_missing_fields(client, auth):
    """Posting an item with empty fields is rejected with validation messages."""
    auth.login()
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    res = client.post('/post', data={
        'type': 'lost',
        'title': '',  # Missing
        'category': '',  # Missing
        'location': '',  # Missing
        'date': '',  # Missing
        'description': '',  # Missing
        'csrf_token': csrf
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Item title is required" in res.data
    assert b"Please select a valid item category" in res.data


def test_post_found_item_missing_verification_qa(client, auth):
    """Found items MUST have verification question and answer."""
    auth.login()
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    res = client.post('/post', data={
        'type': 'found',
        'title': 'Found Earbuds',
        'category': 'electronics',
        'location': 'Library',
        'date': '2026-11-20',
        'description': 'White wireless earbuds',
        'verification_question': '',  # Missing!
        'verification_answer': '',  # Missing!
        'csrf_token': csrf
    }, follow_redirects=True)

    assert b"Found items must have a verification question" in res.data
    assert b"Found items must have a verification answer" in res.data


def test_post_invalid_photo_extension(client, auth):
    """Uploading files with non-image extensions (e.g. .pdf or .exe) is rejected."""
    auth.login()
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    fake_pdf = (io.BytesIO(b"%PDF-1.4 fake content"), 'malicious.pdf')

    res = client.post('/post', data={
        'type': 'lost',
        'title': 'Lost Keys',
        'category': 'keys',
        'location': 'Parking',
        'date': '2026-11-20',
        'description': 'Locker keys',
        'photo': fake_pdf,
        'csrf_token': csrf
    }, follow_redirects=True)

    assert b"Invalid photo format" in res.data


def test_unauthenticated_protected_routes(client):
    """Unauthenticated access to protected routes redirects to login."""
    protected_urls = ['/post', '/my-posts', '/notifications']
    for url in protected_urls:
        res = client.get(url, follow_redirects=False)
        assert res.status_code == 302
        assert '/login' in res.headers['Location']


def test_unauthorized_post_edit_and_delete(client, auth, app):
    """A user cannot edit or delete someone else's post."""
    # Alice (user_id=2) owns item
    with app.app_context():
        item_id = execute_db(
            """
            INSERT INTO Item (user_id, type, title, category, description, location, date, status)
            VALUES (2, 'lost', 'Alice Wallet', 'other', 'Black leather', 'Library', '2026-11-20', 'Open')
            """
        )

    # Bob (user_id=3) logs in
    auth.login(email='bob@test.edu', password='Password@123')
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token', '')

    # Bob tries to edit Alice's post
    res_edit = client.post(f'/item/{item_id}/edit', data={
        'title': 'Hacked Title',
        'category': 'other',
        'location': 'Library',
        'date': '2026-11-20',
        'description': 'Hacked',
        'csrf_token': csrf
    }, follow_redirects=True)
    assert b"do not have permission to edit this post" in res_edit.data

    # Bob tries to delete Alice's post
    res_del = client.post(f'/item/{item_id}/delete', data={'csrf_token': csrf}, follow_redirects=True)
    assert b"do not have permission to delete this post" in res_del.data


def test_404_handling(client):
    """Accessing non-existent route or item returns friendly 404 page."""
    res = client.get('/item/999999')
    assert res.status_code == 404
    assert b"404" in res.data
    assert b"Item or Page Not Found" in res.data
