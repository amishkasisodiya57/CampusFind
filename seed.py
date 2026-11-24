"""
CampusFind - Database Seeding Script (seed.py)
Creates tables, populates administrator, 5 student demo users,
and ~15 realistic lost and found items including verified matching pairs.
"""

import os
import sqlite3
from werkzeug.security import generate_password_hash
from database import init_db, get_db, execute_db, query_db
from matching import find_and_record_matches


def run_seed():
    print("Initializing CampusFind database...")
    conn = init_db()

    # Clear existing data to ensure idempotent clean seed
    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.execute("DELETE FROM Notification;")
    conn.execute("DELETE FROM Claim;")
    conn.execute("DELETE FROM Match;")
    conn.execute("DELETE FROM Item;")
    conn.execute("DELETE FROM User;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.commit()

    print("Creating administrator and demo users...")
    users = [
        # Admin account
        ("Campus Administrator", "admin@campusfind.edu", "Admin@123", "admin"),
        # 5 Demo student users
        ("Arav Sharma", "arav@campusfind.edu", "Password@123", "user"),
        ("Priya Patel", "priya@campusfind.edu", "Password@123", "user"),
        ("Rohan Verma", "rohan@campusfind.edu", "Password@123", "user"),
        ("Sneha Reddy", "sneha@campusfind.edu", "Password@123", "user"),
        ("Kabir Mehta", "kabir@campusfind.edu", "Password@123", "user"),
    ]

    user_ids = {}
    for name, email, raw_pw, role in users:
        pw_hash = generate_password_hash(raw_pw)
        cur = conn.execute(
            "INSERT INTO User (name, email, password_hash, role, active) VALUES (?, ?, ?, ?, 1)",
            (name, email, pw_hash, role)
        )
        user_ids[email] = cur.lastrowid

    conn.commit()
    print(f"Created {len(users)} users successfully.")

    # 15+ Sample Items including verified matching pairs
    # Verification answer hashes are stored lowercase & trimmed
    items = [
        # --- PAIR 1: Electronics (Dell Laptop) -> EXPECTED MATCH SCORE >= 60 ---
        {
            "user_id": user_ids["arav@campusfind.edu"],
            "type": "lost",
            "title": "Blue Dell Inspiron 15 Laptop",
            "category": "electronics",
            "description": "Lost my blue Dell Inspiron laptop in a black protective sleeve with a GitHub sticker on the back lid.",
            "location": "Central Library 2nd Floor",
            "date": "2026-11-22",
            "photo_path": None,
            "status": "Open",
            "q": None,
            "a": None
        },
        {
            "user_id": user_ids["priya@campusfind.edu"],
            "type": "found",
            "title": "Dell Inspiron Laptop found in Library",
            "category": "electronics",
            "description": "Found a blue Dell laptop left on study table 14 in Central Library with stickers on it.",
            "location": "Central Library",
            "date": "2026-11-23",
            "photo_path": None,
            "status": "Open",
            "q": "What sticker is on the laptop lid?",
            "a": "github"
        },

        # --- PAIR 2: ID Card -> EXPECTED MATCH SCORE >= 60 ---
        {
            "user_id": user_ids["rohan@campusfind.edu"],
            "type": "lost",
            "title": "Student ID Card (Computer Science)",
            "category": "ID card",
            "description": "Lost my college identity card near the main canteen during lunch break. Roll number 2024CS42.",
            "location": "Main Canteen",
            "date": "2026-11-21",
            "photo_path": None,
            "status": "Open",
            "q": None,
            "a": None
        },
        {
            "user_id": user_ids["sneha@campusfind.edu"],
            "type": "found",
            "title": "Found Student Identity Card near Canteen",
            "category": "ID card",
            "description": "Found a student ID card on the wooden table outside the canteen.",
            "location": "Main Canteen",
            "date": "2026-11-21",
            "photo_path": None,
            "status": "Open",
            "q": "What is the roll number printed on the card?",
            "a": "2024cs42"
        },

        # --- PAIR 3: Bottle -> EXPECTED MATCH SCORE >= 60 ---
        {
            "user_id": user_ids["kabir@campusfind.edu"],
            "type": "lost",
            "title": "Black Milton Thermos Water Bottle",
            "category": "bottle",
            "description": "Black stainless steel Milton thermos bottle with a small dent on the bottom rim.",
            "location": "Sports Complex Badminton Court",
            "date": "2026-11-20",
            "photo_path": None,
            "status": "Open",
            "q": None,
            "a": None
        },
        {
            "user_id": user_ids["arav@campusfind.edu"],
            "type": "found",
            "title": "Milton Black Steel Water Bottle",
            "category": "bottle",
            "description": "Found a black insulated thermos water bottle near the badminton court bench.",
            "location": "Sports Complex",
            "date": "2026-11-21",
            "photo_path": None,
            "status": "Open",
            "q": "What is the brand of the bottle?",
            "a": "milton"
        },

        # --- PAIR 4: Books -> EXPECTED MATCH SCORE >= 60 ---
        {
            "user_id": user_ids["priya@campusfind.edu"],
            "type": "lost",
            "title": "Thomas Calculus Textbook & Green Notebook",
            "category": "books",
            "description": "Thomas Calculus 14th edition along with a spiral green ruled notebook left after class.",
            "location": "Science Block Room 304",
            "date": "2026-11-19",
            "photo_path": None,
            "status": "Open",
            "q": None,
            "a": None
        },
        {
            "user_id": user_ids["kabir@campusfind.edu"],
            "type": "found",
            "title": "Calculus Textbook & Notebook left in classroom",
            "category": "books",
            "description": "Found calculus textbook and a notebook left on the back bench in room 304.",
            "location": "Science Block",
            "date": "2026-11-20",
            "photo_path": None,
            "status": "Open",
            "q": "What color is the spiral notebook?",
            "a": "green"
        },

        # --- PAIR 5: Keys -> EXPECTED MATCH SCORE >= 60 ---
        {
            "user_id": user_ids["sneha@campusfind.edu"],
            "type": "lost",
            "title": "Set of 3 Keys on Red Honda Lanyard",
            "category": "keys",
            "description": "Lost bike key and two small locker keys attached to a bright red lanyard.",
            "location": "Student Parking Lot B",
            "date": "2026-11-23",
            "photo_path": None,
            "status": "Open",
            "q": None,
            "a": None
        },
        {
            "user_id": user_ids["rohan@campusfind.edu"],
            "type": "found",
            "title": "Keys on Red Lanyard",
            "category": "keys",
            "description": "Found a bunch of keys on a red lanyard near two-wheeler parking lot B.",
            "location": "Parking Lot B",
            "date": "2026-11-23",
            "photo_path": None,
            "status": "Open",
            "q": "What brand logo is on the vehicle key?",
            "a": "honda"
        },

        # --- INDEPENDENT / UNPAIRED ITEMS ---
        {
            "user_id": user_ids["arav@campusfind.edu"],
            "type": "lost",
            "title": "Grey North Face Winter Hoodie (Size L)",
            "category": "clothing",
            "description": "Dark grey hoodie with front pouch pocket, forgotten on the auditorium seat after cultural fest.",
            "location": "Main Auditorium",
            "date": "2026-11-18",
            "photo_path": None,
            "status": "Open",
            "q": None,
            "a": None
        },
        {
            "user_id": user_ids["priya@campusfind.edu"],
            "type": "found",
            "title": "Casio Scientific Calculator fx-991EX",
            "category": "electronics",
            "description": "Found a black and white solar Casio calculator in the mechanical workshop hall.",
            "location": "Mechanical Engineering Lab",
            "date": "2026-11-17",
            "photo_path": None,
            "status": "Open",
            "q": "What model number is written on the calculator?",
            "a": "fx-991ex"
        },
        {
            "user_id": user_ids["rohan@campusfind.edu"],
            "type": "lost",
            "title": "Titan Leather Strap Analog Watch",
            "category": "other",
            "description": "Brown leather strap classic watch lost in hostel dining area.",
            "location": "Hostel 3 Mess",
            "date": "2026-11-15",
            "photo_path": None,
            "status": "Open",
            "q": None,
            "a": None
        },
        {
            "user_id": user_ids["sneha@campusfind.edu"],
            "type": "found",
            "title": "Navy Blue Compact Umbrella",
            "category": "other",
            "description": "Found a foldable umbrella near the security booth at the main entrance gate.",
            "location": "Campus Main Gate",
            "date": "2026-11-16",
            "photo_path": None,
            "status": "Open",
            "q": "What is the pattern inside the umbrella?",
            "a": "checkered"
        },
        {
            "user_id": user_ids["kabir@campusfind.edu"],
            "type": "lost",
            "title": "Boat Airdopes Wireless Earbuds Case",
            "category": "electronics",
            "description": "Matte black wireless earbuds charging case lost in reading room.",
            "location": "Central Library Reading Room",
            "date": "2026-11-24",
            "photo_path": None,
            "status": "Open",
            "q": None,
            "a": None
        }
    ]

    print(f"Inserting {len(items)} sample items and computing auto-matches...")
    created_item_ids = []
    for item in items:
        ans_hash = generate_password_hash(item["a"].strip().lower()) if item["a"] else None
        cur = conn.execute(
            """
            INSERT INTO Item (
                user_id, type, title, category, description, location, date,
                photo_path, status, verification_question, verification_answer_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["user_id"], item["type"], item["title"], item["category"],
                item["description"], item["location"], item["date"], item["photo_path"],
                item["status"], item["q"], ans_hash
            )
        )
        item_id = cur.lastrowid
        created_item_ids.append(item_id)
        # Execute matching for this newly inserted item
        find_and_record_matches(item_id, db=conn)

    conn.commit()

    # Query match count
    match_count = conn.execute("SELECT COUNT(*) FROM Match").fetchone()[0]
    notif_count = conn.execute("SELECT COUNT(*) FROM Notification").fetchone()[0]
    print(f"Seed complete!")
    print(f"  - Users created: {len(users)}")
    print(f"  - Items created: {len(items)}")
    print(f"  - Smart matches generated (score >= 60%): {match_count}")
    print(f"  - System notifications dispatched: {notif_count}")
    conn.close()


if __name__ == "__main__":
    run_seed()
