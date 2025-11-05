import streamlit as st
import pandas as pd
import json
import os
import hashlib
from typing import Optional, Dict

USERS_FILE = "users.json"
USER_OVERRIDES_FILE = "user_overrides.csv" 

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

def load_plan_overrides() -> Dict:
    """Loads whitelisted emails and their specified tiers from a CSV file."""
    if os.path.exists(USER_OVERRIDES_FILE):
        try:
            # Assuming CSV has columns: 'email', 'plan_code'
            df = pd.read_csv(USER_OVERRIDES_FILE)
            df['email'] = df['email'].str.lower()
            df['plan_code'] = df['plan_code'].str.lower().str.strip()
            # Map codes to full tier names
            tier_map = {
                'un': 'Unlimited', 'tpro': 'Teacher Pro', '28pro': '28/1 Pro', 
                'univ': 'Universal Pro'
            }
            # Create a dictionary mapping email -> full_tier_name
            overrides = {}
            for index, row in df.iterrows():
                if row['plan_code'] in tier_map:
                    overrides[row['email']] = tier_map[row['plan_code']]
            return overrides
        except Exception:
            # st.warning("Error reading user_overrides.csv. Check format.")
            return {}
    return {}

# --- Authentication Core Logic ---

def authenticate_user(email: str, password: str) -> Optional[str]:
    """Checks credentials and returns the email if valid, otherwise None."""
    users = load_users()
    hashed_password = hash_password(password)
    
    if email in users and users[email]['password'] == hashed_password:
        return email
    return None

def register_user(email: str, password: str) -> str:
    """Registers a new user and returns a status message."""
    users = load_users()
    email_lower = email.lower()
    
    if email_lower in users:
        return "Error: This email is already registered."
    
    # Check for plan override
    overrides = load_plan_overrides()
    
    # Default plan is Free Tier, unless overridden by CSV
    initial_tier = overrides.get(email_lower, 'Free Tier')
    
    # Create the user profile
    users[email_lower] = {
        'password': hash_password(password),
        'tier': initial_tier
    }
    
    save_users(users)
    return f"Success: User {email} registered with {initial_tier} plan. Please log in."

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
        login_email = st.text_input("Email (Login)", key="login_email").lower()
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
        st.markdown("*Note: All sign-ups default to **Free Tier** unless whitelisted by an administrator.*")
        signup_email = st.text_input("Email (Signup)", key="signup_email")
        signup_password = st.text_input("Password (Signup)", type="password", key="signup_password")
        
        if st.button("Register", key="register_btn", use_container_width=True):
            if not signup_email or not signup_password:
                st.error("Email and password are required.")
            else:
                status = register_user(signup_email, signup_password)
                if status.startswith("Success"):
                    st.success(status)
                    # No automatic login, force user to use the login panel
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
