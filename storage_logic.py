def check_storage_limit(storage: Dict, action_area: str) -> Tuple[bool, Optional[str], float]:
    """Checks if the user can perform an action based on their tier and usage.
    Returns (can_proceed: bool, error_message: str, effective_limit_mb: float).
    """
    current_tier = storage.get('tier') 
    
    # FINAL CRITICAL FIX 1: Unlimited users ALWAYS pass the check, regardless of how other values loaded.
    if current_tier == "Unlimited":
        # Always return True, no error message, and a huge limit for safety
        return True, None, 100000000.0 
        
    # --- Non-Unlimited Tier Logic Below ---
    effective_limit = TIER_LIMITS.get(current_tier, TIER_LIMITS['Free Tier']) # Default to the assigned tier's limit
    used_mb = storage.get('total_used_mb', 0.0)
    
    # --- Universal Limit Check (used by the main app dispatcher) ---
    if action_area == 'universal':
        # Universal Pro gets 5000MB limit. Dedicated tiers (28/1 Pro, Teacher Pro) and Free get 500MB universal limit.
        if current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] 
        else:
            effective_limit = TIER_LIMITS['Free Tier'] 
            
        if used_mb >= effective_limit:
            return False, f"Total storage limit reached ({used_mb:.2f}MB / {effective_limit}MB). Please upgrade or clean up data.", effective_limit
        return True, None, effective_limit

    # --- Tiered/Dedicated Limit Check for Saving (utility_save or teacher_save) ---
    
    if action_area == 'utility_save':
        used_mb = storage['utility_used_mb']
        if current_tier == '28/1 Pro': 
            effective_limit = TIER_LIMITS['28/1 Pro'] 
        elif current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] 
        else: # Free Tier or Teacher Pro tier uses the Free Tier limit
            effective_limit = TIER_LIMITS['Free Tier']
        
    elif action_area == 'teacher_save':
        used_mb = storage['teacher_used_mb']
        if current_tier == 'Teacher Pro':
            effective_limit = TIER_LIMITS['Teacher Pro'] 
        elif current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] 
        else: # Free Tier or 28/1 Pro tier uses the Free Tier limit
            effective_limit = TIER_LIMITS['Free Tier']
    
    # Check if the next save would exceed the limit
    if used_mb + NEW_SAVE_COST_BASE_MB > effective_limit:
        return False, f"Storage limit reached ({used_mb:.2f}MB / {effective_limit}MB) for your current plan's {action_area.replace('_save', '').title()} section.", effective_limit
    
    return True, None, effective_limit
