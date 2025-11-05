import json
import os
from typing import Dict, Tuple, Optional

# --- CONSTANTS ---
STORAGE_TRACKER_FILE = "storage_tracker.json"
BASE_DIR = "user_data"
NEW_SAVE_COST_BASE_MB = 0.5 

TIER_LIMITS = {
    'Free Tier': 500.0,      # 0.5 GB universal for general usage and default for specific areas
    '28/1 Pro': 3000.0,      # 3 GB dedicated to utility; universal limit for app navigation is Free Tier's 500MB
    'Teacher Pro': 3000.0,   # 3 GB dedicated to teacher; universal limit for app navigation is Free Tier's 500MB
    'Universal Pro': 5000.0, # 5 GB total for all tools combined
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
    """Loads the user's storage tracker or creates a default one.
    Ensures all keys are present and initialized to 0.0 for new or incomplete trackers.
    """
    file_path = get_file_path(STORAGE_TRACKER_FILE.replace(".json", "_"), user_email)
    
    default_tracker = {
        'tier': 'Free Tier', # Default tier for new users
        'total_used_mb': 0.0,
        'utility_used_mb': 0.0,
        'teacher_used_mb': 0.0,
        'general_used_mb': 0.0 # Added general_used_mb for 28-in-1 hub tracking
    }
    
    loaded_data = {}
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                loaded_data = json.load(f)
            except json.JSONDecodeError:
                pass # If file is corrupted, it acts as if it's a new file, using default_tracker
    
    # Merge loaded data with default to ensure all keys exist and default values are set for new keys.
    tracker = {**default_tracker, **loaded_data} 
    
    return tracker

def save_storage_tracker(storage: Dict, user_email: str):
    """Saves the user's storage tracker."""
    file_path = get_file_path(STORAGE_TRACKER_FILE.replace(".json", "_"), user_email)
    with open(file_path, "w") as f:
        json.dump(storage, f, indent=4)

def calculate_mock_save_size(data_content: str) -> float:
    """Calculates a mock size for saved data based on length.
    Using a fixed multiplier for predictability.
    """
    # A base cost plus a variable cost based on content length
    return NEW_SAVE_COST_BASE_MB + (len(data_content) / 1000000) * 0.3 # 0.3MB per 1MB of text

def check_storage_limit(storage: Dict, action_area: str) -> Tuple[bool, Optional[str], float]:
    """Checks if the user can perform an action based on their tier and usage.
    Returns (can_proceed: bool, error_message: str, effective_limit_mb: float).
    """
    current_tier = storage.get('tier', 'Free Tier') # Default to Free Tier if not found
    
    if current_tier == "Unlimited":
        return True, None, TIER_LIMITS['Unlimited'] # Unlimited access

    total_used_mb = storage.get('total_used_mb', 0.0)

    # Determine the universal limit for the current tier for overall app access
    universal_limit_for_tier = TIER_LIMITS['Free Tier'] # Default universal limit for Free, 28/1, Teacher
    if current_tier == 'Universal Pro' or current_tier == 'Unlimited':
        universal_limit_for_tier = TIER_LIMITS.get(current_tier, TIER_LIMITS['Universal Pro'])
    
    # --- Universal Access Check (for overall app interaction and general usage) ---
    # This applies to 'universal' (login) and 'general_usage' (28-in-1 hub, etc.)
    if action_area in ['universal', 'general_usage']:
        if total_used_mb >= universal_limit_for_tier:
            return False, f"Total storage limit reached ({total_used_mb:.2f}MB / {universal_limit_for_tier:.0f}MB). Please upgrade or clean up data.", universal_limit_for_tier
        
        return True, None, universal_limit_for_tier # Allow interaction if within universal limit


    # --- Specific Action Area Checks (for saving data in dedicated tools) ---
    used_mb_for_area = 0.0
    area_limit = 0.0
    
    # Determine the specific area's used MB and its limit based on tier
    if action_area == 'utility_save':
        used_mb_for_area = storage.get('utility_used_mb', 0.0)
        if current_tier == '28/1 Pro' or current_tier == 'Universal Pro': 
            area_limit = TIER_LIMITS['28/1 Pro'] # 28/1 Pro and Universal Pro get this dedicated limit for utility
        else:
            area_limit = TIER_LIMITS['Free Tier'] # Free tier limit for others
        
    elif action_area == 'teacher_save':
        used_mb_for_area = storage.get('teacher_used_mb', 0.0)
        if current_tier == 'Teacher Pro' or current_tier == 'Universal Pro':
            area_limit = TIER_LIMITS['Teacher Pro'] # Teacher Pro and Universal Pro get this dedicated limit for teacher
        else:
            area_limit = TIER_LIMITS['Free Tier'] # Free tier limit for others
    
    # Calculate potential new size and check if it would exceed the area limit
    mock_next_save_size = calculate_mock_save_size("MOCK_CONTENT_FOR_SIZE_ESTIMATION")
    if (used_mb_for_area + mock_next_save_size) > area_limit:
        return False, f"Storage limit reached ({used_mb_for_area:.2f}MB / {area_limit:.0f}MB) for your current plan's {action_area.replace('_save', '').title()} section. Next save would exceed limit.", area_limit
    
    return True, None, area_limit
