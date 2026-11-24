# CampusFind: Smart Campus Lost & Found

> **A Complete, Professional Multi-Page Web Platform for College Campus Recovery**  
> **Author & Developer:** Amishka Sisodiya  
> **Project Type:** College Academic Software Engineering Project  
> **Tech Stack:** Python Flask, SQLite, HTML5/CSS3, JavaScript, Jinja2, Bootstrap 5, Pytest  

---

## 📌 1. Project Overview & Core Problem

### The Core Problem
Lost items on university campuses are rarely returned. Students misplace critical possessions—such as **Student ID cards, laptops, smartphones, textbooks, keys, and water bottles**—every day. The current recovery process is broken:
- **Fragmented Channels:** Items are posted randomly across unofficial WhatsApp groups, Instagram stories, or paper notice boards where posts are quickly lost.
- **Zero Searchability:** Students have no central database to filter by campus location, date, or category.
- **False Claims & Privacy Risks:** Anyone can falsely claim expensive items, and honest finders are hesitant to publish personal phone numbers publicly.

### The CampusFind Solution
**CampusFind** is a secure, responsive, multi-page web platform designed for desktop and mobile browsers. It solves campus loss recovery with:
1. **Centralized Directory:** Instant, searchable catalog of all campus lost and found reports.
2. **Intelligent Auto-Matching (`matching.py`):** Automatically evaluates every new post against existing reports of the opposite type using a 4-tier weighted compatibility algorithm (threshold $\ge 60\%$).
3. **Cryptographic Claim & Verification Protocol:** Found items require a secret verification question. Only genuine owners who answer correctly unlock the finder's contact information, with a strict 3-attempt brute-force lockout.
4. **Data Privacy & Admin Moderation:** Finder contact details and verification answers are never exposed publicly, and administrators have full moderation powers.

---

## 🚀 2. System Architecture & Tech Stack

```
                     ┌──────────────────────────────────────────┐
                     │            Client Web Browser             │
                     │  (Desktop, Laptop, Tablet, Mobile Phone)  │
                     └────────────────────┬─────────────────────┘
                                          │ HTTP / HTTPS
                                          ▼
                     ┌──────────────────────────────────────────┐
                     │           Flask Web Application          │
                     │      (app.py / auth.py / matching.py)    │
                     └───────┬──────────────┬─────────────┬─────┘
                             │              │             │
                             ▼              ▼             ▼
                     ┌──────────────┐ ┌───────────┐ ┌───────────┐
                     │ SQLite DB    │ │ Jinja2    │ │ Static    │
                     │ (campusfind) │ │ Templates │ │ CSS/JS/Img│
                     └──────────────┘ └───────────┘ └───────────┘
```

| Component | Technology | Rationale |
|---|---|---|
| **Backend** | Python Flask 3.x | Lightweight, clean WSGI routing, easy to explain in a viva |
| **Database** | SQLite 3 | Serverless, zero-config, portable single-file relational DB |
| **Frontend** | HTML5, CSS3, JavaScript | Pure Jinja2 server-rendered templates (no complex React/build steps) |
| **UI Design** | Bootstrap 5.3 CDN + Custom Theme | Responsive Teal & Navy modern theme, accessible on all screen sizes |
| **Security** | Werkzeug Security | Salted password & verification answer hashing, CSRF session tokens |
| **Testing** | Pytest | 24 automated unit, integration, and security edge-case tests |
| **Deployment** | Gunicorn / Render / PythonAnywhere | Fully deployable for free without paid servers |

---

## 📂 3. Directory & File Structure

```
NEW PROJECT/
├── app.py                      # Main Flask application with routes, context processors, error handlers
├── database.py                 # SQLite database connection, schema definition, and query helpers
├── matching.py                 # Intelligent 4-tier auto-matching scoring engine
├── auth.py                     # Authentication helpers, password hashing, and CSRF protection
├── seed.py                     # Seeds admin, 5 student demo users, and 15 sample items with matches
├── requirements.txt            # Python dependencies (Flask, Werkzeug, pytest, gunicorn)
├── Procfile                    # Process command for Gunicorn cloud deployment
├── runtime.txt                 # Specifies Python runtime version for cloud hosts
├── .gitignore                  # Git ignore rules for bytecode, virtual environments, and caches
├── README.md                   # Complete documentation, setup, deployment, and viva guide
│
├── static/
│   ├── css/
│   │   └── style.css           # Custom Teal & Navy responsive CSS styling, animations, cards, badges
│   ├── js/
│   │   └── main.js             # Client-side validation, 5MB photo preview, dynamic form fields
│   └── uploads/                # Directory for user-uploaded item photos (.gitkeep tracked)
│
├── templates/                  # Jinja2 HTML Templates
│   ├── base.html               # Base layout: sticky navbar with notification badge, footer (Amishka Sisodiya)
│   ├── index.html              # Landing page (hero, how it works, recent listings, platform stats)
│   ├── register.html           # User registration form
│   ├── login.html              # User login form with demo credentials hint
│   ├── post_item.html          # Unified 3-click post form for Lost and Found items
│   ├── edit_item.html          # Edit post form (restricted to owner or admin)
│   ├── browse.html             # Search and filter directory (keyword, type, category, location, date)
│   ├── item_detail.html        # Item view + Claim verification modal/form + finder contact card
│   ├── my_posts.html           # User dashboard with their items and ranked auto-match cards
│   ├── notifications.html      # In-app notifications with mark-all-read
│   ├── admin.html              # Admin dashboard: moderation tables and user account toggles
│   ├── about.html              # Problem statement, approach, and author Amishka Sisodiya
│   └── 404.html                # Friendly custom 404 error page
│
└── tests/                      # Automated Pytest Suite
    ├── conftest.py             # Fixtures: isolated test database, test client, authenticated sessions
    ├── test_matching.py        # Unit tests for scoring algorithm (category, location, date, keywords)
    ├── test_claim.py           # Claim verification tests (correct, wrong, 3-attempt lockout, mark returned)
    ├── test_auth.py            # Auth tests (register, login, active/deactivated status, admin RBAC)
    └── test_negative.py        # Negative edge-case tests (empty fields, oversized files, unauthorized access)
```

---

## 🗄️ 4. Database Schema

The database uses SQLite with foreign key enforcement enabled (`PRAGMA foreign_keys = ON;`).

```
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
  │     User     │1        *│     Item     │1        *│    Claim     │
  ├──────────────┤──────────├──────────────┤──────────├──────────────┤
  │ id (PK)      │          │ id (PK)      │          │ id (PK)      │
  │ name         │          │ user_id (FK) │          │ item_id (FK) │
  │ email        │          │ type         │          │ claimant_id  │
  │ password_hash│          │ title        │          │ attempts     │
  │ role         │          │ category     │          │ result       │
  │ active       │          │ description  │          │ timestamp    │
  │ created_at   │          │ location     │          └──────────────┘
  └──────────────┘          │ date         │
          │1                │ photo_path   │
          │                 │ status       │
          │*                │ verif_quest  │
  ┌──────────────┐          │ verif_ans_hsh│
  │ Notification │          │ created_at   │
  ├──────────────┤          └──────┬───────┘
  │ id (PK)      │                 │1
  │ user_id (FK) │                 │
  │ message      │                 │*
  │ is_read      │          ┌──────────────┐
  │ timestamp    │          │    Match     │
  └──────────────┘          ├──────────────┤
                            │ id (PK)      │
                            │ lost_item_id │
                            │ found_item_id│
                            │ score        │
                            │ created_at   │
                            └──────────────┘
```

1. **User Table:** `id`, `name`, `email` (UNIQUE), `password_hash`, `role` ('user' or 'admin'), `active` (1 or 0), `created_at`.
2. **Item Table:** `id`, `user_id` (FK User), `type` ('lost' or 'found'), `title`, `category` (ID card, electronics, books, bottle, keys, clothing, other), `description`, `location`, `date`, `photo_path`, `status` ('Open', 'Matched', 'Claimed', 'Returned'), `verification_question`, `verification_answer_hash`, `created_at`.
3. **Match Table:** `id`, `lost_item_id` (FK Item), `found_item_id` (FK Item), `score`, `created_at` with `UNIQUE(lost_item_id, found_item_id)`.
4. **Claim Table:** `id`, `item_id` (FK Item), `claimant_id` (FK User), `attempts` (default 0), `result` ('pending', 'approved', 'rejected'), `timestamp`.
5. **Notification Table:** `id`, `user_id` (FK User), `message`, `is_read` (default 0), `timestamp`.

---

## 🧠 5. The Auto-Matching Scoring Algorithm (`matching.py`)

When an item is posted or updated, the system scans all active posts of the opposite type. The score is calculated strictly out of **100 points**:

$$\text{Total Score} = \text{Category (40)} + \text{Location (25)} + \text{Date (15)} + \text{Keywords (up to 20)}$$

| Factor | Points | Rule & Logic |
|---|---|---|
| **Same Category** | **40 points** | Strict case-insensitive category equality (`lost.category == found.category`). |
| **Same Location** | **25 points** | Exact match, substring match (e.g. *"Central Library 2nd Floor"* vs *"Central Library"*), or campus synonym token match (*"audi"* $\rightarrow$ *"auditorium"*). |
| **Date within 3 Days** | **15 points** | Absolute date difference $\le 3\text{ days}$ ($|d_1 - d_2| \le 3$). 4 or more days awards 0 points. |
| **Keyword Overlap** | **Up to 20 points** | Cleans title and description by removing common English stop words. Each unique matching keyword adds **+5 points** (capped at 20 points). |

### Match Threshold & Dispatch:
- A total score of **60 points or higher** is designated as a **Possible Match**.
- The pair is recorded in the `Match` table.
- Post statuses update from `Open` to `Matched`.
- Immediate in-app notifications are generated and delivered to both users.
- Ranked matches appear with percentage badges on the users' **My Posts** dashboard.

---

## 🔒 6. Claim & Verification Security Protocol

Found items present the highest risk of false or malicious claims. CampusFind implements a multi-layered verification protocol:

1. **Secret Question Creation:** When reporting a Found item, the finder must specify a verification question (e.g. *"What is written on the keychain?"*) and answer (e.g. *"Batman"*).
2. **Cryptographic Answer Hashing:** The answer is trimmed, lowercased, and salted/hashed using Werkzeug (`generate_password_hash`). **The plain answer is NEVER stored in the database and NEVER sent to the browser.**
3. **Verification Submission:** A claimant logs in and submits their answer. The input is trimmed, lowercased, and validated using `check_password_hash`.
4. **Outcome A — Correct Answer:**
   - Claim result set to `approved`.
   - Post status set to `Claimed`.
   - Finder contact details (name and college email) are **unlocked and displayed only to the verified claimant**.
   - Notifications dispatched to both parties.
5. **Outcome B — Incorrect Answer:**
   - Attempt counter is incremented.
   - Finder contact details **remain completely hidden**.
   - User is warned with the remaining attempts count.
6. **3-Attempt Brute-Force Lockout:**
   - If a user fails **3 consecutive attempts** on an item, their claim is permanently locked (`rejected`). Future submissions are blocked.
7. **Return Handover:** Once physical handover occurs on campus, the finder marks the item as `Returned`.

---

## 💻 7. Local Setup & Execution Guide

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14 installed on your machine.
- Git (optional).

### Step 1: Open Terminal in Project Directory
Navigate to the project directory:
```bash
cd "c:\Users\amish\OneDrive\Desktop\NEW PROJECT"
```

### Step 2: Install Dependencies
Install all required libraries (Flask, Werkzeug, pytest, gunicorn):
```bash
pip install -r requirements.txt
```

### Step 3: Populate Seed Data (Demo Users & Matching Items)
Run the seed script to create all database tables and load 6 users and 15 realistic items:
```bash
python seed.py
```
*Output will display:*
```
Initializing CampusFind database...
Creating administrator and demo users...
Created 6 users successfully.
Inserting 15 sample items and computing auto-matches...
Seed complete!
  - Users created: 6
  - Items created: 15
  - Smart matches generated (score >= 60%): 6
  - System notifications dispatched: 12
```

### Step 4: Start the Flask Application
Run the local development server:
```bash
python app.py
```
Open your web browser and go to:
👉 **`http://127.0.0.1:5000`** (or `http://localhost:5000`)

---

## 🔑 8. Pre-Configured Demo Accounts (For Viva Demonstration)

| Role | Account Name | College Email | Password | Pre-seeded Posts & Matches |
|---|---|---|---|---|
| **Admin** | Campus Administrator | `admin@campusfind.edu` | `Admin@123` | Full admin panel access, moderation tools |
| **Student** | Arav Sharma | `arav@campusfind.edu` | `Password@123` | Lost Dell Laptop (Matches with Priya, 100%) |
| **Student** | Priya Patel | `priya@campusfind.edu` | `Password@123` | Found Dell Laptop in Library (Has secret Q&A) |
| **Student** | Rohan Verma | `rohan@campusfind.edu` | `Password@123` | Lost CS ID Card (Matches with Sneha, 90%) |
| **Student** | Sneha Reddy | `sneha@campusfind.edu` | `Password@123` | Found CS ID Card (Roll number secret Q&A) |
| **Student** | Kabir Mehta | `kabir@campusfind.edu` | `Password@123` | Lost Milton Thermos Bottle (Matches Arav, 95%) |

---

## 🧪 9. Running the Pytest Test Suite

The test suite covers:
- **`test_matching.py`**: Exact match (100%), Category mismatch (0%), Location substring/synonym match, Date boundary conditions (3 days vs 4 days), Keyword extraction and stopword exclusion, Threshold scoring ($\ge 60\%$).
- **`test_claim.py`**: Correct answer approval, answer case-insensitivity and whitespace trimming, wrong answer attempt increment, 3-attempt lockout rejection, self-claim prevention, mark returned.
- **`test_auth.py`**: Registration validation, duplicate email prevention, login success/failure, deactivated user blocking, admin role-based access control (RBAC), toggle user activation.
- **`test_negative.py`**: Missing required fields, found item missing verification Q&A, non-image photo upload rejection, unauthenticated protected route redirection, unauthorized post editing/deletion, 404 page handling.

To run the full test suite:
```bash
python -m pytest tests -v
```

**Expected Result:**
```
============================= 24 passed in 24.06s =============================
```

---

## 🌐 10. Free Online Deployment Guide

CampusFind is 100% cloud-ready with `Procfile`, `runtime.txt`, and standard WSGI entry points. Below are two free options:

### Option A: Free Deployment on Render.com (Recommended)
1. Push your project to a GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Deploy CampusFind to Render"
   git branch -M main
   git remote add origin https://github.com/<your-username>/campusfind.git
   git push -u origin main
   ```
2. Go to [https://render.com](https://render.com) and sign in for free.
3. Click **"New +"** $\rightarrow$ **"Web Service"**.
4. Connect your GitHub repository.
5. Configure the settings:
   - **Name:** `campusfind`
   - **Runtime:** `Python 3`
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt && python seed.py`
   - **Start Command:** `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 wsgi:app`
   - **Instance Type:** `Free`
6. Under **Environment Variables**, add:
   - `PYTHON_VERSION` = `3.11.9`
   - `FLASK_DEBUG` = `false`
   - `SECRET_KEY` = *(Click "Generate" or type a random string)*
7. Click **"Create Web Service"**.
8. Render will build the environment, seed the database, and publish your live URL: `https://campusfind.onrender.com`.

*(Alternatively, because `render.yaml` is included in the project, you can simply use **Render Blueprints** for 1-click automatic setup).*

---

### 💾 Important: Database & Upload Persistence on Render Free Tier
- **Ephemeral Filesystem:** Render's Free Web Service tier uses an ephemeral filesystem. When the application goes idle after 15 minutes of inactivity or during a new deployment, the container resets to the Git commit state.
- **Why `seed.py` in the Build Command?** By adding `python seed.py` to the Build Command, all demo accounts, sample items, and verified auto-matches are automatically seeded fresh on every deployment!
- **Persistent Storage Alternatives:**
  - For full data persistence on a free plan, connect an external free cloud database (e.g. Neon PostgreSQL, Supabase, or Turso SQLite Cloud) by setting the `DATABASE_URL` environment variable.
  - For permanent image uploads on a free plan, connect a free object storage bucket (e.g. Cloudinary, AWS S3 Free Tier, or Supabase Storage).
  - For academic viva evaluation, the built-in SQLite database + automatic seeding + SVG category icon placeholders are completely self-contained, zero-cost, and require no third-party API keys!

---

### Option B: Free Deployment on PythonAnywhere.com
1. Create a free account at [https://www.pythonanywhere.com](https://www.pythonanywhere.com).
2. Open a **Bash Console** from your dashboard.
3. Clone or upload your project into your home directory:
   ```bash
   git clone https://github.com/<your-username>/campusfind.git
   cd campusfind
   pip install -r requirements.txt
   python seed.py
   ```
4. Go to the **Web** tab in PythonAnywhere dashboard:
   - Click **"Add a new web app"** $\rightarrow$ choose **Manual configuration** $\rightarrow$ **Python 3.10 / 3.11**.
   - Under **Code**, set **Source code** path: `/home/<username>/campusfind`.
   - Set **Working directory**: `/home/<username>/campusfind`.
5. Click on the **WSGI configuration file** link and update it to:
   ```python
   import sys
   path = '/home/<username>/campusfind'
   if path not in sys.path:
       sys.path.append(path)

   from app import app as application
   ```
6. Click **"Reload <username>.pythonanywhere.com"**. Your site is now live!

---

## 🎓 11. College Viva Examination Questions & Model Answers

### Q1: Why did you choose Python Flask and SQLite over Django or MERN stack?
> **Answer:** *"Flask is a lightweight, transparent micro-framework that adheres to the WSGI standard. Unlike Django, which includes heavy monolithic ORMs and admin packages that obscure underlying mechanics, Flask allows every route, decorator, query, and session check to be clearly written and easily explained during an academic viva. SQLite is serverless, zero-configuration, and stores the entire relational database in a portable file, making local demonstration, testing, and grading instant without needing separate database servers like MySQL or PostgreSQL."*

### Q2: How does the auto-matching algorithm work in `matching.py`?
> **Answer:** *"The auto-matching algorithm uses a weighted 4-factor scoring model totaling 100 points:
> 1. Category match awards 40 points for strict category agreement.
> 2. Location match awards 25 points using exact, substring, or token matching to handle campus name variations.
> 3. Date match awards 15 points if reported dates are within 3 days of each other.
> 4. Keyword overlap awards up to 20 points (5 points per common descriptive word), excluding common English stop words.
> Any pair scoring 60 points or above is categorized as a smart match. The system records it in the database and triggers in-app notifications to both parties."*

### Q3: How do you prevent unauthorized users from claiming expensive found items?
> **Answer:** *"Found items cannot be claimed on a first-come basis. The finder specifies a secret verification question (e.g. unique scratches, stickers, or serial numbers). The answer is trimmed, converted to lowercase, and cryptographically hashed using PBKDF2/SHA256 via Werkzeug. When someone attempts a claim, their answer is checked against the hash. If correct, the item status changes to Claimed and finder contact details are revealed. If incorrect, attempts are recorded; after 3 failed attempts, the user is permanently locked out from claiming that item to eliminate brute-force guessing."*

### Q4: How is security handled on the web platform?
> **Answer:** *"Security is implemented across multiple layers:
> - Passwords and verification answers are hashed using salted PBKDF2.
> - SQL injection is prevented by using parameterized SQLite queries (`?` placeholders) throughout `database.py`.
> - Cross-Site Request Forgery (CSRF) is mitigated by issuing and verifying unique cryptographically generated tokens on all POST/PUT/DELETE requests.
> - Cross-Site Scripting (XSS) is prevented by Jinja2's contextual HTML escaping.
> - Role-based access control (RBAC) ensures only admins can access moderation panels, and users can only edit or delete their own posts."*

### Q5: How did you ensure fast search response times under 2 seconds?
> **Answer:** *"In `database.py`, we created compound SQLite indexes on frequently searched columns: `idx_item_type_status` on `(type, status)`, `idx_item_category` on `category`, and `idx_item_date` on `date`. Furthermore, queries use lightweight indexed filtering, ensuring sub-second execution even across thousands of records."*

---

## 👩‍💻 12. Author Information
- **Project Lead & Developer:** Amishka Sisodiya
- **Project Title:** CampusFind: Smart Campus Lost & Found
- **Year:** 2026
- **License:** Open Source for Academic & Educational Demonstration
