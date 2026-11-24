"""
CampusFind - Smart Campus Lost & Found
Main Flask Application

Author: Amishka Sisodiya
Technology Stack: Python Flask, SQLite, Jinja2 Templates, Bootstrap 5
"""

import os
import uuid
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, abort, g
)
from werkzeug.utils import secure_filename

from database import init_db, get_db, query_db, execute_db, close_db
from auth import (
    hash_secret, verify_secret, generate_csrf_token, validate_csrf,
    login_required, admin_required, get_current_user
)
import matching

# Initialize Flask App
app = Flask(__name__)
# Secret key from environment variable or production fallback
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'campusfind-production-secret-key-2026')
# Debug mode: OFF by default in production, can be enabled via FLASK_DEBUG=1
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max file upload
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['DATABASE'] = os.environ.get('DATABASE', os.path.join(app.root_path, 'campusfind.db'))

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register database teardown
app.teardown_appcontext(close_db)

# Auto-initialize database on application boot if database file does not exist
with app.app_context():
    db_file = app.config['DATABASE']
    if not os.path.exists(db_file):
        init_db(db_file)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
VALID_CATEGORIES = ['ID card', 'electronics', 'books', 'bottle', 'keys', 'clothing', 'other']


def allowed_file(filename):
    """Check if uploaded file has a valid image extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_storage):
    """Save user uploaded image with unique prefix and return relative path."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        return None
    safe_name = secure_filename(file_storage.filename)
    unique_name = f"{uuid.uuid4().hex[:10]}_{safe_name}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file_storage.save(save_path)
    return f"uploads/{unique_name}"


# ---------------------------------------------------------
# CSRF and Context Processors
# ---------------------------------------------------------
@app.before_request
def check_csrf():
    """Enforce CSRF token verification for unsafe HTTP methods."""
    # Only validate on POST, PUT, DELETE
    if request.method in ('POST', 'PUT', 'DELETE'):
        validate_csrf()


@app.context_processor
def inject_global_vars():
    """Make common state variables available to all templates."""
    user = get_current_user()
    unread_count = 0
    if user:
        row = query_db(
            "SELECT COUNT(*) as count FROM Notification WHERE user_id = ? AND is_read = 0",
            (user['id'],),
            one=True
        )
        if row:
            unread_count = row['count']

    return {
        'current_user': user,
        'unread_count': unread_count,
        'csrf_token': generate_csrf_token(),
        'valid_categories': VALID_CATEGORIES,
        'now_year': datetime.now().year,
        'project_author': 'Amishka Sisodiya',
        'project_name': 'CampusFind'
    }


# ---------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', message="The page you are looking for does not exist."), 404


@app.errorhandler(413)
def file_too_large(error):
    flash("The uploaded file is too large. Maximum allowed size is 5 MB.", "danger")
    return redirect(request.referrer or url_for('browse'))


@app.errorhandler(500)
def internal_error(error):
    return render_template('404.html', message="An unexpected server error occurred. Please try again."), 500


# ---------------------------------------------------------
# Public Routes
# ---------------------------------------------------------
@app.route('/')
def index():
    """Landing Page: Hero section, how it works, recent items, CTAs."""
    recent_items = query_db(
        """
        SELECT i.*, u.name as user_name 
        FROM Item i
        JOIN User u ON i.user_id = u.id
        WHERE i.status IN ('Open', 'Matched')
        ORDER BY i.created_at DESC
        LIMIT 6
        """
    )
    # Quick statistics for hero display
    stats = query_db(
        """
        SELECT 
            SUM(CASE WHEN type = 'lost' THEN 1 ELSE 0 END) as lost_count,
            SUM(CASE WHEN type = 'found' THEN 1 ELSE 0 END) as found_count,
            SUM(CASE WHEN status IN ('Claimed', 'Returned') THEN 1 ELSE 0 END) as returned_count
        FROM Item
        """,
        one=True
    )
    return render_template('index.html', recent_items=recent_items, stats=stats)


@app.route('/about')
def about():
    """About Page: Core problem, approach, matching algorithm explanation, author info."""
    return render_template('about.html')


# ---------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new student or staff user."""
    if 'user_id' in session:
        return redirect(url_for('browse'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # Validations
        if not name or not email or not password:
            flash("All fields (name, email, password) are required.", "danger")
            return render_template('register.html', name=name, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html', name=name, email=email)

        if '@' not in email or '.' not in email.split('@')[-1]:
            flash("Please enter a valid email address.", "danger")
            return render_template('register.html', name=name, email=email)

        # Check existing email
        existing = query_db("SELECT id FROM User WHERE email = ?", (email,), one=True)
        if existing:
            flash("An account with that email already exists. Please log in.", "warning")
            return redirect(url_for('login'))

        # Create user
        pw_hash = hash_secret(password)
        try:
            user_id = execute_db(
                "INSERT INTO User (name, email, password_hash, role, active) VALUES (?, ?, ?, 'user', 1)",
                (name, email, pw_hash)
            )
            # Welcome notification
            execute_db(
                "INSERT INTO Notification (user_id, message) VALUES (?, ?)",
                (user_id, f"Welcome to CampusFind, {name}! Start by browsing or posting lost/found items.")
            )

            # Auto-login
            session['user_id'] = user_id
            session['user_name'] = name
            session['user_role'] = 'user'
            flash(f"Welcome, {name}! Your CampusFind account is ready.", "success")
            return redirect(url_for('browse'))
        except Exception as e:
            flash(f"Registration error: {e}", "danger")
            return render_template('register.html', name=name, email=email)

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User Login."""
    if 'user_id' in session:
        return redirect(url_for('browse'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        next_page = request.args.get('next')

        if not email or not password:
            flash("Please provide both email and password.", "danger")
            return render_template('login.html', email=email)

        user = query_db("SELECT * FROM User WHERE email = ?", (email,), one=True)
        if not user or not verify_secret(user['password_hash'], password):
            flash("Invalid email or password. Please verify your credentials.", "danger")
            return render_template('login.html', email=email)

        if user['active'] != 1:
            flash("Your account has been deactivated by an administrator. Please contact support.", "danger")
            return render_template('login.html', email=email)

        # Set session
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_role'] = user['role']

        flash(f"Welcome back, {user['name']}!", "success")
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('browse'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Clear session and log out."""
    session.clear()
    flash("You have been safely logged out.", "info")
    return redirect(url_for('index'))


# ---------------------------------------------------------
# Item Management (Post, Browse, Detail, Edit, Delete)
# ---------------------------------------------------------
@app.route('/post', methods=['GET', 'POST'])
@login_required
def post_item():
    """
    Post a Lost or Found item.
    Posting takes 3 clicks or fewer: (1) Click Post -> (2) Fill Form -> (3) Submit.
    """
    item_type = request.args.get('type', 'lost').lower()
    if item_type not in ('lost', 'found'):
        item_type = 'lost'

    if request.method == 'POST':
        item_type = request.form.get('type', 'lost').lower()
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        date_str = request.form.get('date', '').strip()
        
        verification_question = request.form.get('verification_question', '').strip()
        verification_answer = request.form.get('verification_answer', '').strip()

        # Validation
        errors = []
        if not title:
            errors.append("Item title is required.")
        if category not in VALID_CATEGORIES:
            errors.append("Please select a valid item category.")
        if not description:
            errors.append("Description is required.")
        if not location:
            errors.append("Campus location is required.")
        if not date_str:
            errors.append("Date is required.")
        
        # Found item specific validation
        if item_type == 'found':
            if not verification_question:
                errors.append("Found items must have a verification question to prevent false claims.")
            if not verification_answer:
                errors.append("Found items must have a verification answer.")

        # Photo handling
        photo_file = request.files.get('photo')
        photo_path = None
        if photo_file and photo_file.filename:
            if not allowed_file(photo_file.filename):
                errors.append("Invalid photo format. Allowed types: png, jpg, jpeg, webp, gif.")
            else:
                photo_path = save_upload(photo_file)

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                'post_item.html',
                item_type=item_type,
                form_data=request.form
            )

        # Hash verification answer (trimmed, lowercased) for security
        ans_hash = hash_secret(verification_answer.lower()) if verification_answer else None

        # Insert Item into database
        item_id = execute_db(
            """
            INSERT INTO Item (
                user_id, type, title, category, description, location, date,
                photo_path, status, verification_question, verification_answer_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Open', ?, ?)
            """,
            (
                g.user['id'], item_type, title, category, description, location,
                date_str, photo_path, verification_question or None, ans_hash
            )
        )

        # Trigger auto-matching engine
        matches = matching.find_and_record_matches(item_id)
        if matches:
            flash(
                f"Your {item_type} item was posted! Our smart auto-matcher found {len(matches)} potential match(es). Check 'My Posts' to view them.",
                "success"
            )
        else:
            flash(f"Your {item_type} item has been successfully posted!", "success")

        return redirect(url_for('item_detail', item_id=item_id))

    return render_template('post_item.html', item_type=item_type, form_data={})


@app.route('/browse')
def browse():
    """
    Search and filter campus items.
    Optimized with indexes to load in under 2 seconds.
    """
    keyword = request.args.get('q', '').strip()
    item_type = request.args.get('type', '').strip().lower()
    category = request.args.get('category', '').strip()
    location = request.args.get('location', '').strip()
    date_val = request.args.get('date', '').strip()
    status = request.args.get('status', '').strip()

    query_parts = ["SELECT i.*, u.name as user_name FROM Item i JOIN User u ON i.user_id = u.id WHERE 1=1"]
    params = []

    # Filter by type (lost / found)
    if item_type in ('lost', 'found'):
        query_parts.append("AND i.type = ?")
        params.append(item_type)

    # Filter by category
    if category in VALID_CATEGORIES:
        query_parts.append("AND i.category = ?")
        params.append(category)

    # Filter by location
    if location:
        query_parts.append("AND i.location LIKE ?")
        params.append(f"%{location}%")

    # Filter by date
    if date_val:
        query_parts.append("AND i.date = ?")
        params.append(date_val)

    # Filter by status: default shows Open & Matched posts unless explicitly requested
    if status in ('Open', 'Matched', 'Claimed', 'Returned'):
        query_parts.append("AND i.status = ?")
        params.append(status)
    else:
        # Default view shows actionable posts
        query_parts.append("AND i.status IN ('Open', 'Matched')")

    # Keyword search across title and description
    if keyword:
        query_parts.append("AND (i.title LIKE ? OR i.description LIKE ? OR i.location LIKE ?)")
        kw_param = f"%{keyword}%"
        params.extend([kw_param, kw_param, kw_param])

    query_parts.append("ORDER BY i.created_at DESC")
    full_query = " ".join(query_parts)

    items = query_db(full_query, params)

    return render_template(
        'browse.html',
        items=items,
        keyword=keyword,
        selected_type=item_type,
        selected_category=category,
        selected_location=location,
        selected_date=date_val,
        selected_status=status
    )


@app.route('/item/<int:item_id>')
def item_detail(item_id):
    """
    Detailed item view.
    Includes claim status, verification form (for found items), and contact info (if claim is approved).
    Never reveals the secret verification answer!
    """
    item = query_db(
        """
        SELECT i.*, u.name as user_name, u.email as user_email 
        FROM Item i
        JOIN User u ON i.user_id = u.id
        WHERE i.id = ?
        """,
        (item_id,),
        one=True
    )
    if not item:
        abort(404)

    claim_record = None
    is_claimant = False
    is_owner = False
    claim_approved = False

    user = get_current_user()
    if user:
        is_owner = (user['id'] == item['user_id'])
        if item['type'] == 'found':
            claim_record = query_db(
                "SELECT * FROM Claim WHERE item_id = ? AND claimant_id = ?",
                (item_id, user['id']),
                one=True
            )
            if claim_record:
                is_claimant = True
                claim_approved = (claim_record['result'] == 'approved')

    # Ranked matches for this item
    matches = []
    if item['type'] == 'lost':
        matches = query_db(
            """
            SELECT m.score, i.id, i.title, i.category, i.location, i.date, i.photo_path, i.status
            FROM Match m
            JOIN Item i ON m.found_item_id = i.id
            WHERE m.lost_item_id = ?
            ORDER BY m.score DESC
            """,
            (item_id,)
        )
    else:
        matches = query_db(
            """
            SELECT m.score, i.id, i.title, i.category, i.location, i.date, i.photo_path, i.status
            FROM Match m
            JOIN Item i ON m.lost_item_id = i.id
            WHERE m.found_item_id = ?
            ORDER BY m.score DESC
            """,
            (item_id,)
        )

    return render_template(
        'item_detail.html',
        item=item,
        is_owner=is_owner,
        is_claimant=is_claimant,
        claim_record=claim_record,
        claim_approved=claim_approved,
        matches=matches
    )


@app.route('/item/<int:item_id>/claim', methods=['POST'])
@login_required
def claim_item(item_id):
    """
    Claim verification for Found items.
    Users must answer the secret verification question correctly.
    Security: Maximum 3 attempts per user per item.
    Correct answer: Reveals finder's contact and marks item 'Claimed'.
    Wrong answer: Logs attempt, locks out after 3 failed attempts.
    """
    item = query_db("SELECT * FROM Item WHERE id = ?", (item_id,), one=True)
    if not item:
        abort(404)

    if item['type'] != 'found':
        flash("Only found items can be claimed via verification.", "warning")
        return redirect(url_for('item_detail', item_id=item_id))

    if item['user_id'] == g.user['id']:
        flash("You cannot claim an item you reported yourself.", "warning")
        return redirect(url_for('item_detail', item_id=item_id))

    if item['status'] in ('Claimed', 'Returned'):
        flash(f"This item has already been {item['status'].lower()}.", "info")
        return redirect(url_for('item_detail', item_id=item_id))

    # Retrieve existing claim record or create one
    claim = query_db(
        "SELECT * FROM Claim WHERE item_id = ? AND claimant_id = ?",
        (item_id, g.user['id']),
        one=True
    )

    attempts = claim['attempts'] if claim else 0
    if attempts >= 3:
        flash("You have reached the maximum limit of 3 failed verification attempts for this item.", "danger")
        return redirect(url_for('item_detail', item_id=item_id))

    answer = request.form.get('verification_answer', '').strip().lower()
    if not answer:
        flash("Please provide an answer to the verification question.", "danger")
        return redirect(url_for('item_detail', item_id=item_id))

    # Check the answer
    is_correct = verify_secret(item['verification_answer_hash'], answer)
    new_attempts = attempts + 1

    if is_correct:
        # Success!
        if claim:
            execute_db(
                "UPDATE Claim SET attempts = ?, result = 'approved', timestamp = CURRENT_TIMESTAMP WHERE id = ?",
                (new_attempts, claim['id'])
            )
        else:
            execute_db(
                "INSERT INTO Claim (item_id, claimant_id, attempts, result) VALUES (?, ?, ?, 'approved')",
                (item_id, g.user['id'], new_attempts)
            )

        # Update item status to 'Claimed'
        execute_db("UPDATE Item SET status = 'Claimed' WHERE id = ?", (item_id,))

        # Fetch finder information
        finder = query_db("SELECT name, email FROM User WHERE id = ?", (item['user_id'],), one=True)

        # Send notifications
        execute_db(
            "INSERT INTO Notification (user_id, message) VALUES (?, ?)",
            (
                item['user_id'],
                f"Your found item '{item['title']}' was verified and claimed by {g.user['name']} ({g.user['email']})."
            )
        )
        execute_db(
            "INSERT INTO Notification (user_id, message) VALUES (?, ?)",
            (
                g.user['id'],
                f"Verification successful for '{item['title']}'! Finder contact: {finder['name']} ({finder['email']})."
            )
        )

        flash(
            f"Verification SUCCESSFUL! You have claimed '{item['title']}'. Contact finder {finder['name']} at {finder['email']} to arrange pickup.",
            "success"
        )
    else:
        # Incorrect answer
        result_status = 'rejected' if new_attempts >= 3 else 'pending'
        if claim:
            execute_db(
                "UPDATE Claim SET attempts = ?, result = ?, timestamp = CURRENT_TIMESTAMP WHERE id = ?",
                (new_attempts, result_status, claim['id'])
            )
        else:
            execute_db(
                "INSERT INTO Claim (item_id, claimant_id, attempts, result) VALUES (?, ?, ?, ?)",
                (item_id, g.user['id'], new_attempts, result_status)
            )

        remaining = 3 - new_attempts
        if remaining > 0:
            flash(f"Incorrect verification answer. You have {remaining} attempt(s) remaining.", "danger")
        else:
            flash("Incorrect verification answer. You have exceeded the maximum of 3 attempts. Claim is now locked.", "danger")

    return redirect(url_for('item_detail', item_id=item_id))


@app.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Edit an existing post (restricted to owner or admin)."""
    item = query_db("SELECT * FROM Item WHERE id = ?", (item_id,), one=True)
    if not item:
        abort(404)

    # Permission check
    if item['user_id'] != g.user['id'] and g.user['role'] != 'admin':
        flash("You do not have permission to edit this post.", "danger")
        return redirect(url_for('item_detail', item_id=item_id))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        date_str = request.form.get('date', '').strip()
        status = request.form.get('status', item['status']).strip()

        errors = []
        if not title:
            errors.append("Title is required.")
        if category not in VALID_CATEGORIES:
            errors.append("Please choose a valid category.")
        if not description:
            errors.append("Description is required.")
        if not location:
            errors.append("Location is required.")
        if not date_str:
            errors.append("Date is required.")

        photo_file = request.files.get('photo')
        photo_path = item['photo_path']
        if photo_file and photo_file.filename:
            if not allowed_file(photo_file.filename):
                errors.append("Invalid photo format.")
            else:
                photo_path = save_upload(photo_file)

        # Verification Q&A update for found items
        ver_q = item['verification_question']
        ver_ans_hash = item['verification_answer_hash']
        if item['type'] == 'found':
            new_q = request.form.get('verification_question', '').strip()
            new_ans = request.form.get('verification_answer', '').strip()
            if new_q:
                ver_q = new_q
            if new_ans:
                ver_ans_hash = hash_secret(new_ans.lower())

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template('edit_item.html', item=item)

        execute_db(
            """
            UPDATE Item 
            SET title = ?, category = ?, description = ?, location = ?, date = ?, 
                photo_path = ?, status = ?, verification_question = ?, verification_answer_hash = ?
            WHERE id = ?
            """,
            (title, category, description, location, date_str, photo_path, status, ver_q, ver_ans_hash, item_id)
        )

        # Re-trigger matching if status is Open or Matched
        if status in ('Open', 'Matched'):
            matching.find_and_record_matches(item_id)

        flash("Item post updated successfully.", "success")
        return redirect(url_for('item_detail', item_id=item_id))

    return render_template('edit_item.html', item=item)


@app.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    """Delete an item (restricted to owner or admin)."""
    item = query_db("SELECT * FROM Item WHERE id = ?", (item_id,), one=True)
    if not item:
        abort(404)

    if item['user_id'] != g.user['id'] and g.user['role'] != 'admin':
        flash("You do not have permission to delete this post.", "danger")
        return redirect(url_for('item_detail', item_id=item_id))

    execute_db("DELETE FROM Item WHERE id = ?", (item_id,))
    flash(f"Post '{item['title']}' has been deleted.", "info")
    return redirect(url_for('my_posts'))


@app.route('/item/<int:item_id>/return', methods=['POST'])
@login_required
def return_item(item_id):
    """Finder or admin marks an item as Returned."""
    item = query_db("SELECT * FROM Item WHERE id = ?", (item_id,), one=True)
    if not item:
        abort(404)

    if item['user_id'] != g.user['id'] and g.user['role'] != 'admin':
        flash("Only the finder or an admin can mark this item as Returned.", "danger")
        return redirect(url_for('item_detail', item_id=item_id))

    execute_db("UPDATE Item SET status = 'Returned' WHERE id = ?", (item_id,))
    flash(f"Item '{item['title']}' has been marked as Returned. Great job!", "success")
    return redirect(url_for('item_detail', item_id=item_id))


# ---------------------------------------------------------
# User Dashboard (My Posts, Notifications)
# ---------------------------------------------------------
@app.route('/my-posts')
@login_required
def my_posts():
    """
    User dashboard displaying their posted Lost and Found items,
    along with ranked auto-matches.
    """
    user_id = g.user['id']

    # User's items
    items = query_db(
        "SELECT * FROM Item WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )

    # For each item, retrieve matched items with score >= 60
    items_with_matches = []
    for item in items:
        if item['type'] == 'lost':
            matches = query_db(
                """
                SELECT m.score, i.id, i.title, i.category, i.location, i.date, i.photo_path, i.status
                FROM Match m
                JOIN Item i ON m.found_item_id = i.id
                WHERE m.lost_item_id = ?
                ORDER BY m.score DESC
                """,
                (item['id'],)
            )
        else:
            matches = query_db(
                """
                SELECT m.score, i.id, i.title, i.category, i.location, i.date, i.photo_path, i.status
                FROM Match m
                JOIN Item i ON m.lost_item_id = i.id
                WHERE m.found_item_id = ?
                ORDER BY m.score DESC
                """,
                (item['id'],)
            )
        items_with_matches.append({
            'item': item,
            'matches': matches
        })

    return render_template('my_posts.html', items_with_matches=items_with_matches)


@app.route('/notifications')
@login_required
def notifications():
    """User in-app notifications view."""
    user_id = g.user['id']
    notifs = query_db(
        "SELECT * FROM Notification WHERE user_id = ? ORDER BY timestamp DESC",
        (user_id,)
    )
    return render_template('notifications.html', notifications=notifs)


@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for current user."""
    execute_db("UPDATE Notification SET is_read = 1 WHERE user_id = ?", (g.user['id'],))
    flash("All notifications marked as read.", "success")
    return redirect(url_for('notifications'))


@app.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    """Mark a specific notification as read."""
    execute_db("UPDATE Notification SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, g.user['id']))
    return redirect(url_for('notifications'))


# ---------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    """
    Admin control panel to moderate posts, users, and inspect platform statistics.
    """
    # System statistics
    stats = {
        'total_users': query_db("SELECT COUNT(*) as count FROM User", one=True)['count'],
        'total_items': query_db("SELECT COUNT(*) as count FROM Item", one=True)['count'],
        'lost_items': query_db("SELECT COUNT(*) as count FROM Item WHERE type = 'lost'", one=True)['count'],
        'found_items': query_db("SELECT COUNT(*) as count FROM Item WHERE type = 'found'", one=True)['count'],
        'total_matches': query_db("SELECT COUNT(*) as count FROM Match", one=True)['count'],
        'claimed_returned': query_db("SELECT COUNT(*) as count FROM Item WHERE status IN ('Claimed', 'Returned')", one=True)['count']
    }

    # All users
    users = query_db("SELECT id, name, email, role, active, created_at FROM User ORDER BY created_at DESC")

    # All items
    items = query_db(
        """
        SELECT i.*, u.name as user_name 
        FROM Item i
        JOIN User u ON i.user_id = u.id
        ORDER BY i.created_at DESC
        """
    )

    return render_template('admin.html', stats=stats, users=users, items=items)


@app.route('/admin/user/<int:user_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_user(user_id):
    """Deactivate or reactivate a user."""
    if user_id == g.user['id']:
        flash("You cannot deactivate your own admin account.", "warning")
        return redirect(url_for('admin_dashboard'))

    target_user = query_db("SELECT * FROM User WHERE id = ?", (user_id,), one=True)
    if not target_user:
        abort(404)

    new_status = 0 if target_user['active'] == 1 else 1
    execute_db("UPDATE User SET active = ? WHERE id = ?", (new_status, user_id))

    action_label = "reactivated" if new_status == 1 else "deactivated"
    flash(f"User {target_user['name']} has been {action_label}.", "info")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/item/<int:item_id>/delete', methods=['POST'])
@admin_required
def admin_delete_item(item_id):
    """Admin moderate and delete any item."""
    item = query_db("SELECT title FROM Item WHERE id = ?", (item_id,), one=True)
    if item:
        execute_db("DELETE FROM Item WHERE id = ?", (item_id,))
        flash(f"Post '{item['title']}' was removed by administrator.", "info")
    return redirect(url_for('admin_dashboard'))


# ---------------------------------------------------------
# App Entry Point (Local Development)
# ---------------------------------------------------------
if __name__ == '__main__':
    # Initialize DB if running directly
    init_db()
    # Read production port assigned by host environment (e.g. Render / Heroku) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Turn off debug mode in production unless FLASK_DEBUG=1 is explicitly passed
    is_debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')
    app.run(host='0.0.0.0', port=port, debug=is_debug)
