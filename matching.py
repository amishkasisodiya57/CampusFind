"""
CampusFind - Auto-Matching Engine (matching.py)

CORE PROBLEM & APPROACH:
Lost items on campus are rarely returned because students and finders have no
central mechanism to connect. This module implements the intelligent scoring
algorithm that automatically identifies when a newly reported 'Lost' item
corresponds to an already reported 'Found' item (or vice-versa).

SCORING BREAKDOWN (Max Score: 100):
1. Same Category: +40 points
   - Strict categorical agreement (e.g., ID card == ID card, electronics == electronics).
2. Same Location: +25 points
   - Campus locations often have minor naming variations (e.g., "Library 2nd Floor" vs "Central Library").
   - Awards full 25 points if exact, substring, or key location tokens match.
3. Date within 3 Days: +15 points
   - Items are typically found on the same day or shortly after being lost.
   - Absolute difference <= 3 days awards 15 points.
4. Keyword Overlap: Up to +20 points
   - Extracts descriptive keywords from title and description (ignoring common English stop words).
   - Each unique overlapping keyword contributes +5 points (capped at 20 points).

MATCH THRESHOLD:
- A total score of 60 or higher designates a "Possible Match".
- Both users are notified immediately in-app, and matches appear on their "My Posts" dashboard.
"""

import re
from datetime import datetime
from database import query_db, execute_db, get_db

# Common English stop words to exclude from keyword extraction
STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and',
    'any', 'are', 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below',
    'between', 'both', 'but', 'by', 'could', 'did', 'do', 'does', 'doing', 'down',
    'during', 'each', 'few', 'for', 'from', 'further', 'had', 'has', 'have',
    'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 'his',
    'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'me',
    'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off', 'on',
    'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over',
    'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than', 'that', 'the',
    'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they',
    'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very',
    'was', 'we', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom',
    'why', 'with', 'would', 'you', 'your', 'yours', 'yourself', 'yourselves'
}

LOCATION_SYNONYMS = {
    'audi': 'auditorium',
    'lab': 'laboratory',
    'canteen': 'cafeteria',
    'cafe': 'cafeteria',
    'lib': 'library',
}


def _extract_keywords(text):
    """
    Extract meaningful normalized alphanumeric keywords of length >= 3,
    excluding common stop words.
    """
    if not text:
        return set()
    tokens = re.findall(r'[a-zA-Z0-9]+', str(text).lower())
    return {token for token in tokens if len(token) >= 3 and token not in STOP_WORDS}


def _parse_date(date_val):
    """
    Safely parse date from string (YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY)
    or datetime/date object.
    """
    if isinstance(date_val, datetime):
        return date_val.date()
    if hasattr(date_val, 'year') and hasattr(date_val, 'month') and hasattr(date_val, 'day'):
        return date_val

    date_str = str(date_val).strip()
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _val(item, key, default=''):
    """Safely get value from dict or sqlite3.Row."""
    if item is None:
        return default
    try:
        val = item[key]
        return val if val is not None else default
    except (KeyError, IndexError, TypeError):
        return default


def calculate_match_score(lost_item, found_item):
    """
    Compute compatibility score between a Lost item and a Found item.
    Works with dictionaries or sqlite3.Row objects.

    Returns:
        dict: {
            'total': int (0 - 100),
            'is_match': bool (True if total >= 60),
            'category_score': int (0 or 40),
            'location_score': int (0 or 25),
            'date_score': int (0 or 15),
            'keyword_score': int (0 - 20),
            'common_keywords': list[str]
        }
    """
    # 1. CATEGORY SCORING (40 Points)
    cat_lost = str(_val(lost_item, 'category')).strip().lower()
    cat_found = str(_val(found_item, 'category')).strip().lower()
    same_category = (cat_lost == cat_found and bool(cat_lost))
    category_score = 40 if same_category else 0

    # 2. LOCATION SCORING (25 Points)
    loc_lost = str(_val(lost_item, 'location')).strip().lower()
    loc_found = str(_val(found_item, 'location')).strip().lower()
    
    location_match = False
    if loc_lost and loc_found:
        if loc_lost == loc_found:
            location_match = True
        elif (len(loc_lost) >= 4 and loc_lost in loc_found) or (len(loc_found) >= 4 and loc_found in loc_lost):
            location_match = True
        else:
            # Check meaningful word overlap in location names
            words_lost = {w for w in re.findall(r'[a-zA-Z0-9]+', loc_lost) if len(w) >= 3 and w not in STOP_WORDS}
            words_found = {w for w in re.findall(r'[a-zA-Z0-9]+', loc_found) if len(w) >= 3 and w not in STOP_WORDS}
            
            # Normalize synonyms
            words_lost = {LOCATION_SYNONYMS.get(w, w) for w in words_lost}
            words_found = {LOCATION_SYNONYMS.get(w, w) for w in words_found}
            
            if words_lost & words_found:
                location_match = True

    location_score = 25 if location_match else 0

    # 3. DATE SCORING (15 Points - within 3 days)
    date_lost = _parse_date(_val(lost_item, 'date'))
    date_found = _parse_date(_val(found_item, 'date'))
    date_score = 0
    if date_lost and date_found:
        diff_days = abs((date_lost - date_found).days)
        if diff_days <= 3:
            date_score = 15

    # 4. KEYWORD OVERLAP SCORING (Up to 20 Points)
    text_lost = f"{_val(lost_item, 'title')} {_val(lost_item, 'description')}"
    text_found = f"{_val(found_item, 'title')} {_val(found_item, 'description')}"

    keywords_lost = _extract_keywords(text_lost)
    keywords_found = _extract_keywords(text_found)

    common_keywords = sorted(list(keywords_lost.intersection(keywords_found)))
    # Each matching unique keyword contributes 5 points up to 20 max
    keyword_score = min(20, len(common_keywords) * 5)

    # FINAL AGGREGATION
    total = category_score + location_score + date_score + keyword_score
    is_match = (total >= 60)

    return {
        'total': total,
        'is_match': is_match,
        'category_score': category_score,
        'location_score': location_score,
        'date_score': date_score,
        'keyword_score': keyword_score,
        'common_keywords': common_keywords
    }


def find_and_record_matches(item_id, db=None):
    """
    Triggered when an item is created or updated. Compares it against Open
    posts of the opposite type. If score >= 60:
    - Saves/updates the match in the Match table.
    - Updates post status to 'Matched' (if it was 'Open').
    - Dispatches in-app notifications to both users.

    Returns:
        list of dicts containing match results.
    """
    conn = db or get_db()
    current_item = query_db("SELECT * FROM Item WHERE id = ?", (item_id,), one=True, db=conn)
    if not current_item:
        return []

    item_type = current_item['type']
    target_type = 'found' if item_type == 'lost' else 'lost'

    # Candidate items must be of the opposite type and in an active status ('Open' or 'Matched')
    # and not created by the exact same user (prevents matching one's own posts)
    candidates = query_db(
        """
        SELECT * FROM Item 
        WHERE type = ? AND status IN ('Open', 'Matched') AND user_id != ?
        """,
        (target_type, current_item['user_id']),
        db=conn
    )

    recorded_matches = []

    for candidate in candidates:
        if item_type == 'lost':
            lost_item = current_item
            found_item = candidate
        else:
            lost_item = candidate
            found_item = current_item

        score_res = calculate_match_score(lost_item, found_item)
        if score_res['is_match']:
            score = score_res['total']
            lost_id = lost_item['id']
            found_id = found_item['id']

            # Insert or update match
            execute_db(
                """
                INSERT INTO Match (lost_item_id, found_item_id, score)
                VALUES (?, ?, ?)
                ON CONFLICT(lost_item_id, found_item_id) DO UPDATE SET score = excluded.score
                """,
                (lost_id, found_id, score),
                commit=False,
                db=conn
            )

            # Update statuses from 'Open' to 'Matched'
            if lost_item['status'] == 'Open':
                execute_db("UPDATE Item SET status = 'Matched' WHERE id = ?", (lost_id,), commit=False, db=conn)
            if found_item['status'] == 'Open':
                execute_db("UPDATE Item SET status = 'Matched' WHERE id = ?", (found_id,), commit=False, db=conn)

            # Dispatch notification to lost item owner
            msg_lost = (
                f"Smart Match ({score}%): Your lost item '{lost_item['title']}' "
                f"matches a found item '{found_item['title']}' at {found_item['location']}."
            )
            execute_db(
                "INSERT INTO Notification (user_id, message) VALUES (?, ?)",
                (lost_item['user_id'], msg_lost),
                commit=False,
                db=conn
            )

            # Dispatch notification to found item owner
            msg_found = (
                f"Smart Match ({score}%): Your found item '{found_item['title']}' "
                f"matches a lost item report '{lost_item['title']}'."
            )
            execute_db(
                "INSERT INTO Notification (user_id, message) VALUES (?, ?)",
                (found_item['user_id'], msg_found),
                commit=False,
                db=conn
            )

            recorded_matches.append({
                'lost_item_id': lost_id,
                'found_item_id': found_id,
                'score': score,
                'breakdown': score_res
            })

    conn.commit()
    return recorded_matches
