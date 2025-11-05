import json
import os
from typing import Dict, Tuple, Optional

# --- CONSTANTS ---
STORAGE_TRACKER_FILE = "storage_tracker.json"
BASE_DIR = "user_data"
NEW_SAVE_COST_BASE_MB = 0.5 

TIER_LIMITS = {
    'Free Tier': 500.0,      # 0.5 GB
    '28/1 Pro': 3000.0,      # 3 GB dedicated to utility (universal default for others still 0.5GB)
    'Teacher Pro': 3000.0,   # 3 GB dedicated to teacher (universal default for others still 0.5GB)
    'Universal Pro': 5000.0, # 5 GB total for everything
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
                # If file is corrupted, return initial data
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
        'tier': 'Free Tier', 
        'total_used_mb': 0.0,
        'utility_used_mb': 0.0,
        'teacher_used_mb': 0.0,
        'general_used_mb': 0.0
    }
    
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                loaded_data = json.load(f)
                # Merge with default to ensure all keys exist for existing users
                # This handles cases where new keys (like 'general_used_mb') are added later
                for key, default_value in default_tracker.items():
                    if key not in loaded_data:
                        loaded_data[key] = default_value
                return loaded_data
            except json.JSONDecodeError:
                # If file is corrupted, return default
                return default_tracker
    return default_tracker

def save_storage_tracker(storage: Dict, user_email: str):
    """Saves the user's storage tracker."""
    file_path = get_file_path(STORAGE_TRACKER_FILE.replace(".json", "_"), user_email)
    with open(file_path, "w") as f:
        json.dump(storage, f, indent=4)

def calculate_mock_save_size(data_content: str) -> float:
    """Calculates a mock size for saved data based on length.
    Using a fixed multiplier for predictability.
    """
    return NEW_SAVE_COST_BASE_MB + (len(data_content) / 1000000) * 0.3

def check_storage_limit(storage: Dict, action_area: str) -> Tuple[bool, Optional[str], float]:
    """Checks if the user can perform an action based on their tier and usage.
    Returns (can_proceed: bool, error_message: str, effective_limit_mb: float).
    """
    current_tier = storage.get('tier', 'Free Tier') # Default to Free Tier if not found
    
    if current_tier == "Unlimited":
        return True, None, TIER_LIMITS['Unlimited'] # Unlimited access
        
    effective_limit = TIER_LIMITS.get(current_tier, TIER_LIMITS['Free Tier']) # Default to Free Tier limit
    
    # --- Universal Limit Check (for overall app interaction) ---
    if action_area == 'universal':
        universal_limit_for_tier = TIER_LIMITS.get(current_tier, TIER_LIMITS['Free Tier']) # Get specific limit for the tier
        
        # Free Tier, 28/1 Pro, Teacher Pro users share the Free Tier limit for general/universal usage
        if current_tier in ['Free Tier', '28/1 Pro', 'Teacher Pro']:
            universal_limit_for_tier = TIER_LIMITS['Free Tier']
        
        total_used_mb = storage.get('total_used_mb', 0.0)

        # Check if total usage is at or above the universal limit
        if total_used_mb >= universal_limit_for_tier:
            return False, f"Total storage limit reached ({total_used_mb:.2f}MB / {universal_limit_for_tier:.0f}MB). Please upgrade or clean up data.", universal_limit_for_tier
        
        return True, None, universal_limit_for_tier # Allow interaction if within universal limit


    # --- Specific Action Area Checks (for saving data) ---
    used_mb_for_area = 0.0
    area_limit = 0.0

    if action_area == 'utility_save':
        used_mb_for_area = storage.get('utility_used_mb', 0.0)
        if current_tier == '28/1 Pro': 
            area_limit = TIER_LIMITS['28/1 Pro'] # Dedicated limit for 28/1 Pro
        elif current_tier == 'Universal Pro':
            area_limit = TIER_LIMITS['Universal Pro'] # Universal Pro covers all
        else:
            area_limit = TIER_LIMITS['Free Tier'] # Free tier limit for others
        
    elif action_area == 'teacher_save':
        used_mb_for_area = storage.get('teacher_used_mb', 0.0)
        if current_tier == 'Teacher Pro':
            area_limit = TIER_LIMITS['Teacher Pro'] # Dedicated limit for Teacher Pro
        elif current_tier == 'Universal Pro':
            area_limit = TIER_LIMITS['Universal Pro'] # Universal Pro covers all
        else:
            area_limit = TIER_LIMITS['Free Tier'] # Free tier limit for others
    
    # Calculate potential new size and check against area limit
    mock_next_save_size = calculate_mock_save_size("MOCK_CONTENT_FOR_SIZE_ESTIMATION")
    if (used_mb_for_area + mock_next_save_size) > area_limit:
        return False, f"Storage limit reached ({used_mb_for_area:.2f}MB / {area_limit:.0f}MB) for your current plan's {action_area.replace('_save', '').title()} section.", area_limit
    
    return True, None, area_limit
