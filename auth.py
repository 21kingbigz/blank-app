import streamlit as st
import json
import os
import hashlib
import pandas as pd
from typing import Dict, Any

# --- Constants ---
USERS_FILE = "users.json"
PLAN_OVERRIDES_FILE = "plan_overrides.csv" # Looking for CSV

# Mapping for abbreviations in the CSV to full tier names
TIER_ABBREVIATION_MAP = {
    "un": "Unlimited",
    "tpro": "Teacher Pro",
    "28pro": "28/1 Pro",
    "univ": "Universal Pro",
    "free": "Free Tier"
}

# --- Helper Functions ---
def hash_password(password: str) -> str:
    """Hashes a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users() -> Dict[str, Any]:
    """Loads user data from the JSON file."""
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users_data: Dict[str, Any]):
    """Saves user data to the JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users_data, f, indent=4)

def load_plan_overrides() -> Dict[str, str]:
    """Loads plan overrides from the CSV file."""
    overrides = {}
    if os.path.exists(PLAN_OVERRIDES_FILE):
        try:
            df = pd.read_csv(PLAN_OVERRIDES_FILE, header=None, names=['email', 'tier_abbr'])
            for _, row in df.iterrows():
                email = str(row['email']).strip().lower()
                tier_abbr = str(row['tier_abbr']).strip().lower()
                full_tier_name = TIER_ABBREVIATION_MAP.get(tier_abbr, "Free Tier")
                overrides[email] = full_tier_name
            st.toast("Plan overrides loaded from CSV.", icon="✅") 
        except Exception as e:
            st.error(f"Error loading plan overrides from CSV: {e}", icon="🚫")
            return {}
    return overrides

# --- Authentication Functions ---
def render_login_page():
    """Renders the login and sign-up page."""
    st.title("Welcome to Artorius")
    st.subheader("Login or Sign Up")

    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        st.markdown("### Existing User Login")
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email").strip().lower()
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")

            if submitted:
                users = load_users()
                hashed_password = hash_password(password)

                if email in users and users[email]['password'] == hashed_password:
                    st.session_state.logged_in = True
                    st.session_state.current_user = email
                    
                    # Load plan overrides here to ensure it's fresh
                    plan_overrides = load_plan_overrides()
                    
                    # Import storage_logic here to avoid circular dependency
                    from storage_logic import load_storage_tracker
                    st.session_state['storage'] = load_storage_tracker(email)
                    
                    # Apply override or default tier from users.json
                    if email in plan_overrides:
                        new_tier = plan_overrides[email]
                        st.session_state['storage']['tier'] = new_tier
                        st.toast(f"Your plan has been overridden to: {new_tier}", icon="👑")
                    else:
                        st.session_state['storage']['tier'] = users[email].get('tier', 'Free Tier')
                        
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

    with tab_signup:
        st.markdown("### Create New Account")
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email").strip().lower()
            new_password = st.text_input("Password", type="password", key="signup_password1")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_password2")
            signup_submitted = st.form_submit_button("Sign Up")

            if signup_submitted:
                if not new_email or not new_password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    users = load_users()
                    if new_email in users:
                        st.error("An account with this email already exists.")
                    else:
                        hashed_pass = hash_password(new_password)
                        users[new_email] = {
                            "password": hashed_pass,
                            "tier": "Free Tier"  # Default tier for new users
                        }
                        save_users(users)
                        st.success("Account created successfully! Please log in.")
                        
                        # --- Auto-login for new users with correct tier handling ---
                        st.session_state.logged_in = True
                        st.session_state.current_user = new_email
                        
                        from storage_logic import load_storage_tracker 
                        st.session_state['storage'] = load_storage_tracker(new_email)
                        
                        plan_overrides = load_plan_overrides()
                        if new_email in plan_overrides:
                            st.session_state['storage']['tier'] = plan_overrides[new_email]
                            st.toast(f"Your plan has been set to: {plan_overrides[new_email]} via override.", icon="👑")
                        else:
                            st.session_state['storage']['tier'] = "Free Tier" # Ensure default if no override
                            
                        st.rerun()

def logout():
    """Logs out the current user."""
    st.session_state.logged_in = False
    st.session_state.pop('current_user', None)
    st.session_state.pop('storage', None)
    st.session_state.pop('utility_db', None)
    st.session_state.pop('teacher_db', None)
    st.success("You have been logged out.")
    st.rerun()
