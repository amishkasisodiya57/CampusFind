"""
CampusFind - Unit Tests for Auto-Matching Algorithm (tests/test_matching.py)
Tests the 4-tier scoring logic in matching.py:
  1. Category match (40 pts)
  2. Location match (25 pts)
  3. Date match within 3 days (15 pts)
  4. Keyword overlap up to 20 pts (5 pts/word, stopwords excluded)
  5. Threshold condition (total >= 60 = match)
"""

import pytest
from matching import calculate_match_score


def test_perfect_match():
    """Identical category, location, date, and multiple shared keywords should yield 100 points."""
    lost = {
        'category': 'electronics',
        'location': 'Central Library',
        'date': '2026-11-20',
        'title': 'Blue Dell Laptop Inspiron',
        'description': 'Laptop with stickers in sleeve'
    }
    found = {
        'category': 'electronics',
        'location': 'Central Library',
        'date': '2026-11-20',
        'title': 'Found Dell Laptop',
        'description': 'Blue laptop inspiron with sleeve stickers'
    }

    res = calculate_match_score(lost, found)
    assert res['category_score'] == 40
    assert res['location_score'] == 25
    assert res['date_score'] == 15
    assert res['keyword_score'] == 20
    assert res['total'] == 100
    assert res['is_match'] is True


def test_category_mismatch():
    """Different categories must yield 0 category points."""
    lost = {
        'category': 'books',
        'location': 'Main Canteen',
        'date': '2026-11-20',
        'title': 'Notebook',
        'description': 'Math notes'
    }
    found = {
        'category': 'electronics',
        'location': 'Main Canteen',
        'date': '2026-11-20',
        'title': 'Calculator',
        'description': 'Math tool'
    }

    res = calculate_match_score(lost, found)
    assert res['category_score'] == 0


def test_location_substring_and_tokens():
    """Matching campus locations with variations like 'Library 2nd Floor' vs 'Library'."""
    lost = {
        'category': 'bottle',
        'location': 'Central Library 2nd Floor',
        'date': '2026-11-20',
        'title': 'Water Bottle',
        'description': 'Steel'
    }
    found = {
        'category': 'bottle',
        'location': 'Central Library',
        'date': '2026-11-20',
        'title': 'Water Bottle',
        'description': 'Steel'
    }

    res = calculate_match_score(lost, found)
    assert res['location_score'] == 25


def test_date_boundary_conditions():
    """Dates within 3 days should get 15 points; 4+ days should get 0 points."""
    item_base = {
        'category': 'keys',
        'location': 'Parking Lot',
        'title': 'Bike Keys',
        'description': 'Keys'
    }

    # Difference of exactly 3 days: 20th to 23rd -> 15 points
    lost_3d = dict(item_base, date='2026-11-20')
    found_3d = dict(item_base, date='2026-11-23')
    res_3d = calculate_match_score(lost_3d, found_3d)
    assert res_3d['date_score'] == 15

    # Difference of 4 days: 20th to 24th -> 0 points
    found_4d = dict(item_base, date='2026-11-24')
    res_4d = calculate_match_score(lost_3d, found_4d)
    assert res_4d['date_score'] == 0


def test_keyword_overlap_and_stopwords():
    """Stop words ('the', 'in', 'and', 'with') should not count as keywords."""
    lost = {
        'category': 'clothing',
        'location': 'Auditorium',
        'date': '2026-11-20',
        'title': 'The red jacket with a hood',
        'description': 'Left in the hall'
    }
    found = {
        'category': 'clothing',
        'location': 'Sports Hall',
        'date': '2026-11-10',
        'title': 'A red jacket found in the area',
        'description': 'Red color jacket'
    }

    res = calculate_match_score(lost, found)
    # Common keywords: 'red', 'jacket' (2 words -> 2 * 5 = 10 pts)
    # 'the', 'with', 'a', 'in' are stop words and ignored
    assert 'red' in res['common_keywords']
    assert 'jacket' in res['common_keywords']
    assert 'the' not in res['common_keywords']
    assert res['keyword_score'] == 10


def test_threshold_verification():
    """Total score >= 60 is flagged as match; below 60 is not a match."""
    # Match: Category (40) + Location (25) + Keyword 'card' (5) = 70 (>= 60)
    lost_match = {
        'category': 'ID card',
        'location': 'Canteen',
        'date': '2026-11-01',
        'title': 'ID Card',
        'description': 'Student card'
    }
    found_match = {
        'category': 'ID card',
        'location': 'Canteen',
        'date': '2026-11-20',  # > 3 days apart
        'title': 'Unknown Card',
        'description': 'Plastic card'
    }
    res = calculate_match_score(lost_match, found_match)
    assert res['total'] == 70
    assert res['is_match'] is True

    # Non-match: Only Location (25) + Date (15) = 40 (< 60)
    lost_no_match = {
        'category': 'books',
        'location': 'Hostel 1',
        'date': '2026-11-20',
        'title': 'Novel',
        'description': 'Fiction book'
    }
    found_no_match = {
        'category': 'electronics',
        'location': 'Hostel 1',
        'date': '2026-11-21',
        'title': 'Charger',
        'description': 'USB cable'
    }
    res2 = calculate_match_score(lost_no_match, found_no_match)
    assert res2['total'] == 40
    assert res2['is_match'] is False
