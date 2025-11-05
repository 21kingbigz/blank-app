import streamlit as st
import json
import os
import math
import pandas as pd
from typing import Tuple, Optional, Dict

# --- Configuration Constants ---
TEACHER_DATA_FILE_BASE = "teacher_data_"
UTILITY_DATA_FILE_BASE = "utility_data_"
STORAGE_TRACKER_FILE_BASE = "storage_tracker_"

DAILY_SAVED_DATA_COST_MB = 1.0  
NEW_SAVE_COST_BASE_MB = 10.0    
UTILITY_DB_INITIAL = {"saved_items": []} 
TEACHER_DB_INITIAL = {"units": [], "lessons": [], "vocab": [], "worksheets": [], "quizzes": [], "tests": []}

TIER_LIMITS = {
    "Free Tier": 500, "28/1 Pro": 3000, "Teacher Pro": 3000, 
    "Universal Pro": 5000, "Unlimited": float('inf') # Inf is for internal logic, not check_storage_limit
}
STORAGE_INITIAL = {
    "tier": "Free Tier", # This will be overwritten by the tier in users.json
    "total_used_mb": 0.0,
    "utility_used_mb": 0.0, 
    "teacher_used_mb": 0.0,
    "general_used_mb": 0.0, 
    "last_load_timestamp": pd.Timestamp.now().isoformat()
}

# --- Persistence Helpers ---

def get_file_path(base_name: str, user_email: str) -> str:
    """Generates a unique file path for a user."""
    safe_email = user_email.replace('@', '_').replace('.', '_')
    return f"{base_name}{safe_email}.json"

def load_db_file(filename: str, initial_data: Dict) -> Dict:
    """Loads data from a user-specific JSON file (persistence)."""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else initial_data
        except (json.JSONDecodeError, FileNotFoundError):
            return initial_data
    return initial_data

def save_db_file(data: Dict, filename: str):
    """Saves data to a user-specific JSON file (persistence)."""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception:
        # st.error(f"Error saving {filename}: {e}") # Commented out to prevent Streamlit error during non-run
        pass

# --- Core Storage Logic ---

def load_storage_tracker(user_email: str) -> Dict:
    """Loads user tier and usage stats and applies daily cost."""
    storage_file = get_file_path(STORAGE_TRACKER_FILE_BASE, user_email)
    utility_file = get_file_path(UTILITY_DATA_FILE_BASE, user_email)
    teacher_file = get_file_path(TEACHER_DATA_FILE_BASE, user_email)

    data = load_db_file(storage_file, STORAGE_INITIAL)
    
    # 1. Load the latest DBs into memory for calculation
    current_utility_db = load_db_file(utility_file, UTILITY_DB_INITIAL)
    current_teacher_db = load_db_file(teacher_file, TEACHER_DB_INITIAL)

    last_load = pd.Timestamp(data.get('last_load_timestamp', pd.Timestamp.now().isoformat()))
    time_delta = pd.Timestamp.now() - last_load
    days_passed = math.floor(time_delta.total_seconds() / (24 * 3600))
    
    # Apply daily cost only if not Unlimited
    if days_passed >= 1 and data['tier'] != 'Unlimited':
        
        # 2. Update utility items' size (daily cost application)
        all_utility_items = current_utility_db['saved_items']
        total_utility_items = len(all_utility_items)
        if total_utility_items > 0:
            total_cost_to_apply = days_passed * DAILY_SAVED_DATA_COST_MB 
            daily_cost_per_utility_item = total_cost_to_apply / total_utility_items
            for item in all_utility_items:
                item['size_mb'] = item.get('size_mb', 0.0) + daily_cost_per_utility_item
        
        # 3. Update teacher items' size (daily cost application)
        all_teacher_items_flat = []
        for db_key in current_teacher_db.keys():
            all_teacher_items_flat.extend(current_teacher_db[db_key])
        
        total_teacher_items = len(all_teacher_items_flat)
        if total_teacher_items > 0:
            total_cost_to_apply = days_passed * DAILY_SAVED_DATA_COST_MB 
            daily_cost_per_teacher_item = total_cost_to_apply / total_teacher_items
            for item in all_teacher_items_flat:
                item['size_mb'] = item.get('size_mb', 0.0) + daily_cost_per_teacher_item

        # 4. Save the updated item sizes back to the files (Persistence)
        save_db_file(current_utility_db, utility_file)
        save_db_file(current_teacher_db, teacher_file)
        
        # 5. RECALCULATE ALL TOTALS by summing the *actual* saved item sizes
        data['utility_used_mb'] = sum(item.get('size_mb', 0.0) for item in current_utility_db['saved_items'])
        data['teacher_used_mb'] = sum(
            item.get('size_mb', 0.0)
            for db_key in current_teacher_db.keys() 
            for item in current_teacher_db[db_key]
        )
        data['total_used_mb'] = data['utility_used_mb'] + data['teacher_used_mb'] + data['general_used_mb']
        
    # Update timestamp for next load calculation
    data['last_load_timestamp'] = pd.Timestamp.now().isoformat()
    
    # Store the currently loaded DBs in session state for the app to use
    st.session_state['utility_db'] = current_utility_db
    st.session_state['teacher_db'] = current_teacher_db
    
    return data

def save_storage_tracker(data: Dict, user_email: str):
    """Saves user tier and usage stats."""
    storage_file = get_file_path(STORAGE_TRACKER_FILE_BASE, user_email)
    save_db_file(data, storage_file)
    st.session_state['storage'] = data

def check_storage_limit(storage: Dict, action_area: str) -> Tuple[bool, Optional[str], float]:
    """Checks if the user can perform an action based on their tier and usage.
    Returns (can_proceed: bool, error_message: str, effective_limit_mb: float).
    """
    current_tier = storage['tier']
    
    # FIX: Unlimited users ALWAYS pass the check, using a large limit for math.
    if current_tier == "Unlimited":
        return True, None, 100000000.0 
        
    # --- Non-Unlimited Tier Logic ---
    effective_limit = TIER_LIMITS['Free Tier'] # Default limit
    used_mb = 0.0
    
    if action_area == 'universal':
        used_mb = storage['total_used_mb']
        # Universal limit applies to Free and Universal Pro (Dedicated tiers use Free for Universal)
        if current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] 
        else:
            effective_limit = TIER_LIMITS['Free Tier'] # Dedicated tiers fall back to Free Tier's overall limit
            
        if used_mb >= effective_limit:
            return False, f"Total storage limit reached ({used_mb:.2f}MB / {effective_limit}MB). Please upgrade or clean up data.", effective_limit
        return True, None, effective_limit

    # --- Tiered/Dedicated Limit Check for Saving ---
    
    if action_area == 'utility_save':
        used_mb = storage['utility_used_mb']
        if current_tier == '28/1 Pro': 
            effective_limit = TIER_LIMITS['28/1 Pro'] # Dedicated limit
        elif current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] # Universal limit applies
        else: # Free Tier or Teacher Pro tier uses the Free Tier limit
            effective_limit = TIER_LIMITS['Free Tier']
        
    elif action_area == 'teacher_save':
        used_mb = storage['teacher_used_mb']
        if current_tier == 'Teacher Pro':
            effective_limit = TIER_LIMITS['Teacher Pro'] # Dedicated limit
        elif current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] # Universal limit applies
        else: # Free Tier or 28/1 Pro tier uses the Free Tier limit
            effective_limit = TIER_LIMITS['Free Tier']
    
    # Check if the next save would exceed the limit
    if used_mb + NEW_SAVE_COST_BASE_MB > effective_limit:
        return False, f"Storage limit reached ({used_mb:.2f}MB / {effective_limit}MB) for your current plan's {action_area.replace('_save', '').title()} section.", effective_limit
    
    return True, None, effective_limit

def calculate_mock_save_size(content: str) -> float:
    """Calculates a save size based on content length, with a minimum base cost."""
    size = NEW_SAVE_COST_BASE_MB + (len(content) / 5000.0)
    return round(size, 2)
