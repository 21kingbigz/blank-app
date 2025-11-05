import json
import os
import random
from typing import Dict, Tuple, Optional # <-- FIX for NameError

# --- CONSTANTS ---
STORAGE_TRACKER_FILE = "storage_tracker.json"
BASE_DIR = "user_data"
NEW_SAVE_COST_BASE_MB = 0.5 

TIER_LIMITS = {
    'Free Tier': 500.0,      # 0.5 GB
    '28/1 Pro': 3000.0,      # 3 GB dedicated to utility
    'Teacher Pro': 3000.0,   # 3 GB dedicated to teacher
    'Universal Pro': 5000.0, # 5 GB total
    'Unlimited': 100000000.0 # Effectively unlimited
}

UTILITY_DB_INITIAL = {"saved_items": []}
TEACHER_DB_INITIAL = {
    "lessons": [],
    "units": [],
    "worksheets": [],
    "quizzes": [],
    "vocab": [],
    "tests": []
}

def get_file_path(base_name: str, user_email: str) -> str:
    """Returns the full path for a user-specific file."""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    safe_email = user_email.replace('@', '_at_').replace('.', '_dot_')
    return os.path.join(BASE_DIR, f"{base_name}{safe_email}.json")


def load_db_file(file_path: str, initial_data: Dict) -> Dict:
    """Loads a user's data file or returns initial data if not found."""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return initial_data
    return initial_data

def save_db_file(data: Dict, file_path: str):
    """Saves a user's data file."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


def load_storage_tracker(user_email: str) -> Dict:
    """Loads the user's storage tracker or creates a default one."""
    file_path = get_file_path(STORAGE_TRACKER_FILE.replace(".json", "_"), user_email)
    
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError:
                pass 
                
    # Initial data structure for new user
    return {
        'tier': 'Free Tier', 
        'total_used_mb': 0.0,
        'utility_used_mb': 0.0,
        'teacher_used_mb': 0.0,
        'general_used_mb': 0.0
    }

def save_storage_tracker(storage: Dict, user_email: str):
    """Saves the user's storage tracker."""
    file_path = get_file_path(STORAGE_TRACKER_FILE.replace(".json", "_"), user_email)
    with open(file_path, "w") as f:
        json.dump(storage, f, indent=4)

def calculate_mock_save_size(data_content: str) -> float:
    """Calculates a mock size for saved data based on length."""
    # This simulates a small, variable file size
    return NEW_SAVE_COST_BASE_MB + (len(data_content) / 1000000) * random.uniform(0.1, 0.5)

def check_storage_limit(storage: Dict, action_area: str) -> Tuple[bool, Optional[str], float]:
    """Checks if the user can perform an action based on their tier and usage.
    Returns (can_proceed: bool, error_message: str, effective_limit_mb: float).
    """
    current_tier = storage.get('tier') 
    
    # CRITICAL FIX 1: Unlimited users ALWAYS pass the check immediately.
    if current_tier == "Unlimited":
        return True, None, TIER_LIMITS['Unlimited']
        
    # --- Non-Unlimited Tier Logic Below ---
    effective_limit = TIER_LIMITS.get(current_tier, TIER_LIMITS['Free Tier'])
    
    # --- Universal Limit Check (used by the main app dispatcher) ---
    if action_area == 'universal':
        if current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] 
        else: # Dedicated tiers (28/1 Pro, Teacher Pro) and Free use the Free Tier universal limit
            effective_limit = TIER_LIMITS['Free Tier'] 
            
        used_mb = storage.get('total_used_mb', 0.0)
            
        if used_mb >= effective_limit:
            return False, f"Total storage limit reached ({used_mb:.2f}MB / {effective_limit}MB). Please upgrade or clean up data.", effective_limit
        return True, None, effective_limit

    # --- Tiered/Dedicated Limit Check for Saving (utility_save or teacher_save) ---
    
    # Initialize values
    used_mb = 0.0
    
    if action_area == 'utility_save':
        used_mb = storage['utility_used_mb']
        if current_tier == '28/1 Pro': 
            effective_limit = TIER_LIMITS['28/1 Pro'] 
        elif current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] 
        else:
            effective_limit = TIER_LIMITS['Free Tier']
        
    elif action_area == 'teacher_save':
        used_mb = storage['teacher_used_mb']
        if current_tier == 'Teacher Pro':
            effective_limit = TIER_LIMITS['Teacher Pro'] 
        elif current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] 
        else:
            effective_limit = TIER_LIMITS['Free Tier']
    
    # Check if the next save would exceed the limit
    if used_mb + NEW_SAVE_COST_BASE_MB > effective_limit:
        return False, f"Storage limit reached ({used_mb:.2f}MB / {effective_limit}MB) for your current plan's {action_area.replace('_save', '').title()} section.", effective_limit
    
    return True, None, effective_limit
