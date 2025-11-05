import streamlit as st
import json
import os
import pandas as pd

# --- Configuration for storage limits ---
TIER_LIMITS = {
    "Free Tier": {
        "max_utility_saves": 5, "utility_storage_limit_bytes": 10 * 1024,
        "max_teacher_saves": 2, "teacher_storage_limit_bytes": 5 * 1024,
        "universal_storage_limit_bytes": 15 * 1024
    },
    "28/1 Pro": {
        "max_utility_saves": 500, "utility_storage_limit_bytes": 500 * 1024,
        "max_teacher_saves": 0, "teacher_storage_limit_bytes": 0, 
        "universal_storage_limit_bytes": 500 * 1024
    },
    "Teacher Pro": {
        "max_utility_saves": 0, "utility_storage_limit_bytes": 0,
        "max_teacher_saves": 500, "teacher_storage_limit_bytes": 500 * 1024,
        "universal_storage_limit_bytes": 500 * 1024
    },
    "Universal Pro": {
        "max_utility_saves": 2000, "utility_storage_limit_bytes": 2000 * 1024,
        "max_teacher_saves": 2000, "teacher_storage_limit_bytes": 2000 * 1024,
        "universal_storage_limit_bytes": 4000 * 1024
    },
    "Unlimited": {
        "max_utility_saves": float('inf'), "utility_storage_limit_bytes": float('inf'),
        "max_teacher_saves": float('inf'), "teacher_storage_limit_bytes": float('inf'),
        "universal_storage_limit_bytes": float('inf')
    }
}

# Initial empty database structures
UTILITY_DB_INITIAL = {"history": []}
TEACHER_DB_INITIAL = {"history": []}

# --- File Path Management (FIXED to use /tmp) ---
def get_file_path(prefix: str, user_email: str) -> str:
    """
    Generates a unique file path for a user's data file.
    Uses the /tmp directory for write access in Streamlit Cloud.
    """
    safe_email = user_email.replace('@', '_at_').replace('.', '_dot_')
    file_name = f"{prefix}{safe_email}.json"
    
    # CRITICAL FIX: Directs saving to the writable /tmp directory
    file_path = os.path.join("/tmp", file_name) 
    
    return file_path

# --- Database Loading and Saving ---
def load_db_file(file_path: str, initial_data: dict) -> dict:
    """Loads a user's database file, or initializes it if not found."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            # Ensure the loaded data has the 'history' key and it's a list
            if 'history' not in data or not isinstance(data['history'], list):
                data['history'] = initial_data.get('history', [])
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        # If file not found or corrupted, return initial structure
        return initial_data

def save_db_file(file_path: str, data: dict):
    """Saves a user's database file."""
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        st.error(f"Error saving file {file_path}: {e}")

# --- Storage Tracker Management ---
STORAGE_TRACKER_INITIAL = {
    "user_email": "",
    "tier": "Free Tier",
    "current_utility_storage": 0,
    "current_teacher_storage": 0,
    "current_universal_storage": 0
}

def load_storage_tracker(user_email: str) -> dict:
    """Loads a user's storage tracker, or initializes a new one."""
    file_path = get_file_path("storage_tracker_", user_email)
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            # Ensure all keys from initial are present in loaded data
            for key, value in STORAGE_TRACKER_INITIAL.items():
                if key not in data:
                    data[key] = value
            data['user_email'] = user_email # Ensure correct user email
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        # Initialize a new tracker if not found or corrupted
        initial_tracker = STORAGE_TRACKER_INITIAL.copy()
        initial_tracker['user_email'] = user_email
        return initial_tracker

def save_storage_tracker(tracker_data: dict, user_email: str):
    """Saves the current storage tracker data for a user."""
    file_path = get_file_path("storage_tracker_", user_email)
    try:
        with open(file_path, "w") as f:
            json.dump(tracker_data, f, indent=4)
    except IOError as e:
        st.error(f"Error saving storage tracker for {user_email}: {e}")

# --- Storage Limit Checks (FIXED) ---
def calculate_mock_save_size(content: str) -> int:
    """Calculates a mock size for saved content based on string length."""
    return len(content.encode('utf-8')) + 100 # Add a small overhead

def check_storage_limit(storage_data: dict, check_type: str) -> tuple[bool, str, int]:
    """
    Checks if a user is within their storage limits for a given type.
    check_type can be 'utility_save', 'teacher_save', or 'universal_storage'.
    Returns (can_save: bool, error_message: str, limit: int).
    """
    
    user_tier = storage_data.get('tier', 'Free Tier')
    tier_limits = TIER_LIMITS.get(user_tier, TIER_LIMITS['Free Tier'])

    can_save = True
    error_msg = ""
    # FIX: Initialize limit_value to 0 (a number)
    limit_value = 0 

    if check_type == 'utility_save':
        # Safely access history length (ensured to be list in streamlit_app.py init)
        current_saves = len(st.session_state.get('utility_db', {}).get('history', []))
        # Use .get() with a numeric fallback for safety
        max_saves = tier_limits.get('max_utility_saves', 0)
        current_storage = storage_data.get('current_utility_storage', 0)
        storage_limit = tier_limits.get('utility_storage_limit_bytes', 0)

        if max_saves != float('inf') and current_saves >= max_saves:
            can_save = False
            error_msg = f"Utility history limit ({max_saves} items) reached for your '{user_tier}' plan."
        elif storage_limit != float('inf') and current_storage >= storage_limit:
            can_save = False
            error_msg = f"Utility storage limit ({storage_limit / 1024:.1f}KB) reached for your '{user_tier}' plan."
        
        limit_value = storage_limit # Update limit_value with the guaranteed number

            
    elif check_type == 'teacher_save':
        current_saves = len(st.session_state.get('teacher_db', {}).get('history', []))
        max_saves = tier_limits.get('max_teacher_saves', 0)
        current_storage = storage_data.get('current_teacher_storage', 0)
        storage_limit = tier_limits.get('teacher_storage_limit_bytes', 0)

        if max_saves != float('inf') and current_saves >= max_saves:
            can_save = False
            error_msg = f"Teacher history limit ({max_saves} items) reached for your '{user_tier}' plan."
        elif storage_limit != float('inf') and current_storage >= storage_limit:
            can_save = False
            error_msg = f"Teacher storage limit ({storage_limit / 1024:.1f}KB) reached for your '{user_tier}' plan."
        
        limit_value = storage_limit # Update limit_value with the guaranteed number

    elif check_type == 'universal_storage':
        current_storage = storage_data.get('current_universal_storage', 0)
        storage_limit = tier_limits.get('universal_storage_limit_bytes', 0)
        
        if storage_limit != float('inf') and current_storage >= storage_limit:
            can_save = False
            error_msg = f"Universal storage limit ({storage_limit / 1024:.1f}KB) reached for your '{user_tier}' plan."
        
        limit_value = storage_limit # Update limit_value with the guaranteed number


    # Special case: If a feature type has 0 max saves or 0 storage limit, it means no access
    # (Checking limits with numeric fallbacks is key here)
    if (check_type == 'utility_save' and tier_limits.get('max_utility_saves', 1) == 0) or \
       (check_type == 'teacher_save' and tier_limits.get('max_teacher_saves', 1) == 0):
        if tier_limits.get('max_utility_saves', 1) == 0:
            can_save = False
            error_msg = f"Your '{user_tier}' plan does not include access to 28-in-1 Utilities."
        if tier_limits.get('max_teacher_saves', 1) == 0:
            can_save = False
            error_msg = f"Your '{user_tier}' plan does not include access to Teacher Aid."


    # FINAL CAST: limit_value is now guaranteed to be a number (float or int), making this safe.
    return can_save, error_msg, int(limit_value)
