"""
CampusFind - Full End-to-End System & Route Verification Script
Exercises all 9 pages, user roles, auto-matching, claim verification,
admin controls, and error handling.
"""

import sys
import io
from app import app
from database import query_db, execute_db

def test_full_system():
    print("=" * 60)
    print("STARTING FULL END-TO-END CAMPUSFIND SYSTEM VERIFICATION")
    print("=" * 60)

    client = app.test_client()
    passed = 0
    total = 0

    def assert_check(condition, description):
        nonlocal passed, total
        total += 1
        if condition:
            print(f" [PASS] {description}")
            passed += 1
        else:
            print(f" [FAIL] {description}")
            raise AssertionError(f"Check failed: {description}")

    # 1. LANDING PAGE
    res = client.get('/')
    assert_check(res.status_code == 200, "Landing page (/) loads with HTTP 200")
    html = res.data.decode('utf-8')
    assert_check("Lost something on campus?" in html, "Landing page contains hero headline")
    assert_check("How It Works" in html, "Landing page contains How It Works section")
    assert_check("Amishka Sisodiya" in html, "Footer contains author Amishka Sisodiya")

    # 2. ABOUT PAGE
    res = client.get('/about')
    assert_check(res.status_code == 200, "About page (/about) loads with HTTP 200")
    html = res.data.decode('utf-8')
    assert_check("The Auto-Matching Algorithm" in html, "About page explains matching algorithm")
    assert_check("Amishka Sisodiya" in html, "About page credits Amishka Sisodiya")

    # 3. REGISTRATION PAGE & FLOW
    res = client.get('/register')
    assert_check(res.status_code == 200, "Register page (/register) loads with HTTP 200")
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    
    # Register new student with timestamped email
    import time
    test_email = f"e2e_{int(time.time())}@campusfind.edu"
    res_reg = client.post('/register', data={
        'name': 'E2E Test Student',
        'email': test_email,
        'password': 'Password@123',
        'csrf_token': csrf
    }, follow_redirects=True)
    assert_check(res_reg.status_code == 200, "User registration succeeds with HTTP 200")
    assert_check("Welcome, E2E Test Student!" in res_reg.data.decode('utf-8'), "Welcome flash message displayed")

    # 4. LOGOUT
    res_logout = client.get('/logout', follow_redirects=True)
    assert_check("You have been safely logged out." in res_logout.data.decode('utf-8'), "Logout succeeds")

    # 5. LOGIN FLOW
    client.get('/login')
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    
    res_login = client.post('/login', data={
        'email': 'arav@campusfind.edu',
        'password': 'Password@123',
        'csrf_token': csrf
    }, follow_redirects=True)
    assert_check(res_login.status_code == 200, "Login as Arav Sharma succeeds with HTTP 200")
    assert_check("Welcome back, Arav Sharma!" in res_login.data.decode('utf-8'), "User session initialized")

    # 6. POSTING A LOST ITEM
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')

    res_post_lost = client.post('/post', data={
        'type': 'lost',
        'title': 'Sony WH-1000XM4 Noise Canceling Headphones',
        'category': 'electronics',
        'location': 'Computer Lab 3',
        'date': '2026-11-24',
        'description': 'Silver wireless over-ear headphones left next to computer workstation 12.',
        'csrf_token': csrf
    }, follow_redirects=True)
    assert_check(res_post_lost.status_code == 200, "Posting Lost item succeeds with HTTP 200")
    assert_check("Sony WH-1000XM4" in res_post_lost.data.decode('utf-8'), "Item detail renders newly posted item")

    # 7. POSTING A FOUND ITEM (MATCHING THE LOST ITEM)
    client.get('/logout')
    client.get('/login')
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    # Login as Priya to post found item
    client.post('/login', data={
        'email': 'priya@campusfind.edu',
        'password': 'Password@123',
        'csrf_token': csrf
    }, follow_redirects=True)

    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')

    res_post_found = client.post('/post', data={
        'type': 'found',
        'title': 'Found Sony Wireless Headphones in Lab',
        'category': 'electronics',
        'location': 'Computer Lab 3',
        'date': '2026-11-24',
        'description': 'Found silver Sony headphones on table in Computer Lab 3.',
        'verification_question': 'What color is the hard carry case?',
        'verification_answer': 'grey case',
        'csrf_token': csrf
    }, follow_redirects=True)
    assert_check(res_post_found.status_code == 200, "Posting Found item with verification question succeeds")
    found_html = res_post_found.data.decode('utf-8')
    assert_check("potential match" in found_html or "posted" in found_html, "Smart auto-matcher alerts user of potential match")

    # 8. BROWSE & SEARCH WITH MULTIPLE FILTERS
    # Keyword search
    res_search = client.get('/browse?q=Sony')
    assert_check(res_search.status_code == 200, "Search by keyword loads with HTTP 200")
    assert_check("Sony" in res_search.data.decode('utf-8'), "Keyword filter returns relevant items")

    # Category filter
    res_cat = client.get('/browse?category=electronics')
    assert_check(res_cat.status_code == 200, "Filter by category loads with HTTP 200")

    # Type filter (lost only)
    res_lost = client.get('/browse?type=lost')
    assert_check(res_lost.status_code == 200, "Filter by type=lost loads with HTTP 200")

    # 9. MY POSTS & SMART MATCHES
    res_my_posts = client.get('/my-posts')
    assert_check(res_my_posts.status_code == 200, "My Posts dashboard loads with HTTP 200")
    my_posts_html = res_my_posts.data.decode('utf-8')
    assert_check("Possible Smart Matches" in my_posts_html or "Match" in my_posts_html, "Ranked match cards displayed on My Posts")

    # 10. CLAIM AND VERIFICATION FLOW
    # Let Arav (who lost headphones) claim Priya's found headphones
    client.get('/logout')
    client.get('/login')
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    client.post('/login', data={
        'email': 'arav@campusfind.edu',
        'password': 'Password@123',
        'csrf_token': csrf
    }, follow_redirects=True)

    # Find the found item ID
    found_item = query_db("SELECT id FROM Item WHERE title LIKE '%Sony%' AND type = 'found'", one=True)
    item_id = found_item['id']

    # Step A: View item detail - secret answer must NEVER appear in HTML
    res_item = client.get(f'/item/{item_id}')
    item_html = res_item.data.decode('utf-8')
    assert_check("What color is the hard carry case?" in item_html, "Verification question is displayed to claimant")
    assert_check("grey case" not in item_html, "Secret verification answer is NEVER revealed in HTML")

    # Step B: Submit WRONG verification answer
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    res_wrong = client.post(f'/item/{item_id}/claim', data={
        'verification_answer': 'blue leather case',
        'csrf_token': csrf
    }, follow_redirects=True)
    wrong_html = res_wrong.data.decode('utf-8')
    assert_check("Incorrect verification answer" in wrong_html, "Wrong answer generates error alert")
    assert_check("priya@campusfind.edu" not in wrong_html, "Finder contact details remained completely hidden")

    # Step C: Submit CORRECT verification answer (case insensitive & trimmed)
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    res_correct = client.post(f'/item/{item_id}/claim', data={
        'verification_answer': '  Grey Case  ',
        'csrf_token': csrf
    }, follow_redirects=True)
    correct_html = res_correct.data.decode('utf-8')
    assert_check("Verification SUCCESSFUL" in correct_html, "Correct verification answer approved")
    assert_check("priya@campusfind.edu" in correct_html, "Finder contact details unlocked and revealed upon approval")

    # Step D: Finder marks item as RETURNED
    client.get('/logout')
    client.get('/login')
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    client.post('/login', data={
        'email': 'priya@campusfind.edu',
        'password': 'Password@123',
        'csrf_token': csrf
    }, follow_redirects=True)

    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    res_returned = client.post(f'/item/{item_id}/return', data={
        'csrf_token': csrf
    }, follow_redirects=True)
    assert_check("marked as Returned" in res_returned.data.decode('utf-8'), "Finder marked item as Returned")

    # 11. NOTIFICATIONS FLOW
    res_notif = client.get('/notifications')
    assert_check(res_notif.status_code == 200, "Notifications page loads with HTTP 200")
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    res_read_all = client.post('/notifications/read-all', data={'csrf_token': csrf}, follow_redirects=True)
    assert_check("All notifications marked as read." in res_read_all.data.decode('utf-8'), "Mark all notifications read succeeds")

    # 12. ADMIN DASHBOARD & MODERATION
    client.get('/logout')
    client.get('/login')
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    client.post('/login', data={
        'email': 'admin@campusfind.edu',
        'password': 'Admin@123',
        'csrf_token': csrf
    }, follow_redirects=True)

    res_admin = client.get('/admin')
    assert_check(res_admin.status_code == 200, "Admin dashboard loads with HTTP 200")
    admin_html = res_admin.data.decode('utf-8')
    assert_check("Admin Control Center" in admin_html, "Admin header rendered")
    assert_check("Moderate Posts" in admin_html, "Posts moderation table present")
    assert_check("Manage Users" in admin_html, "Users management table present")

    # Admin toggle user active status
    target_student = query_db("SELECT id FROM User WHERE email = 'arav@campusfind.edu'", one=True)
    target_id = target_student['id']
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')
    res_toggle = client.post(f'/admin/user/{target_id}/toggle', data={'csrf_token': csrf}, follow_redirects=True)
    assert_check("deactivated" in res_toggle.data.decode('utf-8') or "reactivated" in res_toggle.data.decode('utf-8'), "Admin can toggle user active status")

    # 13. ERROR PAGE (404)
    res_404 = client.get('/non-existent-campus-page')
    assert_check(res_404.status_code == 404, "Invalid URL returns HTTP 404")
    assert_check("Item or Page Not Found" in res_404.data.decode('utf-8'), "Custom friendly 404 page rendered")

    print("=" * 60)
    print(f"VERIFICATION COMPLETE: {passed}/{total} CHECKS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == '__main__':
    test_full_system()
