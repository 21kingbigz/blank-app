import streamlit as st
import pandas as pd
import json
import os
import hashlib
from typing import Optional, Dict

USERS_FILE = "users.json"
UNLIMITED_USERS_FILE = "unlimited_users.csv"

# --- Utility Functions ---

def hash_password(password):
    """Hashes a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users() -> Dict:
    """Loads user data from users.json."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_users(users: Dict):
    """Saves user data to users.json."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_unlimited_whitelist() -> set:
    """Loads whitelisted emails from a CSV file."""
    if os.path.exists(UNLIMITED_USERS_FILE):
        try:
            # Assuming CSV has a column named 'email'
            df = pd.read_csv(UNLIMITED_USERS_FILE)
            return set(df['email'].str.lower().tolist())
        except Exception:
            return set()
    return set()

# --- Authentication Core Logic ---

def authenticate_user(email: str, password: str) -> Optional[str]:
    """Checks credentials and returns the email if valid, otherwise None."""
    users = load_users()
    hashed_password = hash_password(password)
    
    if email in users and users[email]['password'] == hashed_password:
        return email
    return None

def register_user(email: str, password: str, plan_code: str) -> str:
    """Registers a new user and returns a status message."""
    users = load_users()
    
    if email in users:
        return "Error: This email is already registered."
    
    # Check whitelist for automatic Unlimited tier
    whitelist = load_unlimited_whitelist()
    
    # Map input code to full tier name
    tier_map = {
        'un': 'Unlimited', 'tpro': 'Teacher Pro', '28pro': '28/1 Pro', 
        'univ': 'Universal Pro', 'free': 'Free Tier'
    }
    
    initial_tier = 'Free Tier'
    
    if email.lower() in whitelist:
        initial_tier = 'Unlimited'
    elif plan_code in tier_map:
        initial_tier = tier_map[plan_code]
    else:
        return "Error: Invalid plan code. Must be un, tpro, 28pro, univ, or free."

    # Create the user profile
    users[email] = {
        'password': hash_password(password),
        'tier': initial_tier
    }
    
    save_users(users)
    return f"Success: User {email} registered with {initial_tier} plan."

def render_login_page():
    """Renders the login/signup UI and sets session state upon success."""
    st.title("Artorius Login")
    st.markdown("---")

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None

    col_login, col_signup = st.columns(2)

    with col_login:
        st.subheader("Existing User Login")
        login_email = st.text_input("Email (Login)", key="login_email")
        login_password = st.text_input("Password (Login)", type="password", key="login_password")
        
        if st.button("Login", key="login_btn", use_container_width=True):
            user_email = authenticate_user(login_email, login_password)
            if user_email:
                st.session_state.logged_in = True
                st.session_state.current_user = user_email
                st.toast("Login successful! Welcome.")
                st.rerun()
            else:
                st.error("Invalid email or password.")

    with col_signup:
        st.subheader("New User Sign Up")
        signup_email = st.text_input("Email (Signup)", key="signup_email")
        signup_password = st.text_input("Password (Signup)", type="password", key="signup_password")
        plan_code = st.text_input("Plan Code (un, tpro, 28pro, univ, free)", key="plan_code").lower().strip()
        
        if st.button("Register", key="register_btn", use_container_width=True):
            if not signup_email or not signup_password or not plan_code:
                st.error("All fields are required.")
            else:
                status = register_user(signup_email, signup_password, plan_code)
                if status.startswith("Success"):
                    st.success(status)
                    # Attempt to log in immediately after successful registration
                    user_email = authenticate_user(signup_email, signup_password)
                    if user_email:
                        st.session_state.logged_in = True
                        st.session_state.current_user = user_email
                        st.toast("Registration and Login successful! Welcome.")
                        st.rerun()
                else:
                    st.error(status)
                    
# --- Logout Function ---
def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    # Preserve necessary global keys but clear user-specific data
    keys_to_keep = ['logged_in', 'current_user']
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    st.toast("Logged out successfully.")
    st.rerun()
