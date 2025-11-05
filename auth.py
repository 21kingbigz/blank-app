import streamlit as st
import json
import os
import pandas as pd # Needed for user_overrides.csv

USERS_FILE = "users.json"
OVERRIDES_FILE = "user_overrides.csv"

# Tier mapping based on codes in user_overrides.csv
tier_map = {
    'fr': 'Free Tier',
    '28': '28/1 Pro',
    'te': 'Teacher Pro',
    'un': 'Unlimited', # Code for Unlimited
    'up': 'Universal Pro'
}

def load_users():
    """Loads users and applies tier overrides."""
    if not os.path.exists(USERS_FILE):
        return {}
    
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
        
    overrides = load_plan_overrides()
    
    # Apply overrides
    for email, user_data in users.items():
        if email in overrides:
            code = overrides[email]
            users[email]['tier'] = tier_map.get(code, 'Free Tier')
        elif 'tier' not in users[email]:
            users[email]['tier'] = 'Free Tier'
            
    return users

def load_plan_overrides():
    """Loads plan overrides from CSV."""
    overrides = {}
    if not os.path.exists(OVERRIDES_FILE):
        return overrides
    
    try:
        df = pd.read_csv(OVERRIDES_FILE, header=None, names=['email', 'code'])
        # Ensure codes are clean and map
        for _, row in df.iterrows():
            email = str(row['email']).strip().lower()
            code = str(row['code']).strip().lower()
            if code in tier_map:
                overrides[email] = code
    except Exception as e:
        st.error(f"Error loading plan overrides: {e}")
        
    return overrides


def check_login(email, password):
    """Verifies user credentials."""
    users = load_users()
    email = email.strip().lower()
    
    if email in users and users[email]['password'] == password:
        st.session_state.logged_in = True
        st.session_state.current_user = email
        st.session_state.current_tier = users[email]['tier']
        return True
    return False

def logout():
    """Resets the session state for logout."""
    st.session_state.logged_in = False
    # Clear all application-specific state keys
    keys_to_clear = ['current_user', 'current_tier', 'storage', 'app_mode', 'utility_view', 'teacher_mode', 'utility_db', 'teacher_db']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def render_login_page():
    """Renders the login form."""
    st.title("Artorius Login")
    
    if not os.path.exists(USERS_FILE):
        st.warning("No user database found. Using mock credentials: user@example.com / password")
        # Create a mock user file if it doesn't exist
        with open(USERS_FILE, "w") as f:
             json.dump({"user@example.com": {"password": "password", "tier": "Free Tier"}}, f)

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if check_login(email, password):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid email or password.")
