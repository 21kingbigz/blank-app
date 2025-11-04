import streamlit as st
import os
import json
import math
import pandas as pd # Added for simple data tables/charts
import numpy as np # Added for mock data generation
from google import genai
from PIL import Image
from io import BytesIO
from google.genai.errors import APIError

# --- 0. CONFIGURATION AND PERSISTENCE FILE PATHS ---
WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash'
# File names for permanent storage (Mocked for this script)
TEACHER_DATA_FILE = "teacher_data.json"
UTILITY_DATA_FILE = "utility_data.json"
STORAGE_TRACKER_FILE = "storage_tracker.json"

# Tier Definitions and Storage Limits (in MB)
TIER_LIMITS = {
    "Free Tier": 500, # 500 MB total
    "28/1 Pro": 3000, # 3 GB for 28/1 utilities + 500MB general
    "Teacher Pro": 3000, # 3 GB for Teacher Aid + 500MB general
    "Universal Pro": 5000, # 5 GB total for everything combined
    "Unlimited": float('inf')
}
TIER_PRICES = {
    "Free Tier": "Free",
    "28/1 Pro": "$7/month",
    "Teacher Pro": "$7/month",
    "Universal Pro": "$12/month",
    "Unlimited": "$18/month"
}
# Data consumption (simulated)
DAILY_SAVED_DATA_COST_MB = 1 # 1MB per day for saved data (simplified application)
NEW_SAVE_COST_MB = 1 # Data cost for a new permanent save (simulated)

# Initial structure for databases
TEACHER_DB_INITIAL = {"units": [], "lessons": [], "vocab": [], "worksheets": [], "quizzes": [], "tests": []}
UTILITY_DB_INITIAL = {"saved_items": []}
STORAGE_INITIAL = {
    "tier": "Free Tier", 
    "total_used_mb": 40.0, # Start with some usage for demo
    "utility_used_mb": 15.0, 
    "teacher_used_mb": 20.0,
    "general_used_mb": 5.0 # For data not categorized
}

# --- LOGO & ICON CONFIGURATION ---
LOGO_FILENAME = "image (13).png"
ICON_SETTING = LOGO_FILENAME if os.path.exists(LOGO_FILENAME) else "🚨"

# Set browser tab title, favicon, and layout. 
st.set_page_config(
    page_title=WEBSITE_TITLE,
    page_icon=ICON_SETTING,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CRITICAL CSS FIXES (Minimal required CSS) ---
st.markdown(
    """
    <style>
    /* 1. INPUT FIELD BORDER */
    .stTextInput>div>div>input, .stTextArea>div>div, .stSelectbox>div>div {
        border: 1px solid #444444;
        border-radius: 6px;
    }
    /* 2. Tier Label (Top Left) */
    .tier-label {
        font-size: 0.8em;
        font-weight: bold;
        color: #888888; /* Gray color */
        position: absolute;
        top: 5px;
        left: 5px;
    }
    /* Hide Streamlit footer and menu button */
    #MainMenu, footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

# --- PERSISTENCE & STORAGE FUNCTIONS (Simplified and Mocked) ---

def load_storage_tracker():
    """Loads user tier and usage stats (MOCK)."""
    # In a real app, this would load from a database or secure file.
    data = STORAGE_INITIAL.copy()
    
    # Simulate daily usage increase (ONLY for tiers that aren't unlimited)
    if data['tier'] != 'Unlimited':
        # Simplify: Add daily cost only to the main buckets for demonstration
        data['total_used_mb'] += DAILY_SAVED_DATA_COST_MB
        data['utility_used_mb'] += DAILY_SAVED_DATA_COST_MB * 0.4
        data['teacher_used_mb'] += DAILY_SAVED_DATA_COST_MB * 0.4
        data['general_used_mb'] += DAILY_SAVED_DATA_COST_MB * 0.2
        data['total_used_mb'] = data['utility_used_mb'] + data['teacher_used_mb'] + data['general_used_mb']

    return data

def save_storage_tracker(data):
    """Saves user tier and usage stats (MOCK)."""
    # In a real app, this would commit to the database.
    st.toast("💾 Storage state saved (Mocked)")
    # For this demo, we just update session state.
    st.session_state['storage'] = data

def check_storage_limit(action_area: str):
    """Checks if the user can perform an action based on their tier and usage."""
    current_tier = st.session_state.storage['tier']
    current_used = st.session_state.storage['total_used_mb']
    limit = TIER_LIMITS[current_tier]
    
    if current_tier == "Unlimited":
        return True, None
        
    # Logic to determine effective limit based on tier specialization
    effective_limit = limit
    used = current_used

    if action_area == 'utility_save':
        used = st.session_state.storage['utility_used_mb']
        # 28/1 Pro uses 3000MB limit for this category
        if current_tier == '28/1 Pro': effective_limit = TIER_LIMITS['28/1 Pro']
        # Other tiers use the general 500MB limit for this category
        elif current_tier != 'Universal Pro': effective_limit = TIER_LIMITS['Free Tier']

    elif action_area == 'teacher_save':
        used = st.session_state.storage['teacher_used_mb']
        # Teacher Pro uses 3000MB limit for this category
        if current_tier == 'Teacher Pro': effective_limit = TIER_LIMITS['Teacher Pro']
        # Other tiers use the general 500MB limit for this category
        elif current_tier != 'Universal Pro': effective_limit = TIER_LIMITS['Free Tier']
    
    # Universal Pro and Free Tier use the combined limit check
    
    # Final check
    if used + NEW_SAVE_COST_MB > effective_limit:
        return False, f"Storage limit reached for **{current_tier}** in this area ({used:.2f}MB / {effective_limit}MB)."
    
    return True, None


# --- INITIALIZATION BLOCK ---

if 'storage' not in st.session_state:
    st.session_state['storage'] = load_storage_tracker()
    
# Use current mode to set the correct sidebar highlight
if 'app_mode' not in st.session_state:
    st.session_state['app_mode'] = "Usage Dashboard" 
    
# Mock data for demonstration purposes
MOCK_TOP_USAGE = [
    {"Item": "Lesson Plan: Civil War", "Size": 25.5, "Type": "Teacher"},
    {"Item": "Schedule: Last Planner", "Size": 15.1, "Type": "28/1 Utility"},
    {"Item": "Quiz: Fractions", "Size": 10.0, "Type": "Teacher"},
    {"Item": "Recipe Improver Chat", "Size": 5.2, "Type": "28/1 Utility"},
]

# --- AI & CATEGORY DATA (Unchanged from original) ---
# NOTE: The full CATEGORIES_FEATURES dictionary and run_ai_generation function are assumed
# to be present here from the original code for the app to function. 
# They are omitted here for brevity.

CATEGORIES_FEATURES = {
     "🧠 Productivity": {"icon": "💡", "features": {
        "1. Calendar Creator": "tasks: write report, call client. Time: 9am-12pm.", 
        "2. Task Deconstruction Expert": "Vague goal: Start an online business.",
        "3. Get Unstuck Prompter": "Problem: I keep procrastinating on my final essay.",
        "4. Habit Breaker": "Bad habit: Checking my phone right when I wake up.",
        "5. One-Sentence Summarizer": "Text: The sun is a star at the center of the Solar System. It is a nearly perfect ball of hot plasma..."
    }},
    "💰 Finance": {"icon": "🧮", "features": { 
        "6. Tip & Split Calculator": "bill $85.50, 15% tip, 2 people.",
        "7. Unit Converter": "Convert 500 milliliters to pints.",
        "8. Priority Spending Advisor": "Goal: Save $10k. Planned purchase: $800 new gaming PC."
    }},
    # ... (rest of 28 features) ...
    "📚 School Expert AI": {"icon": "🎓", "features": {
        "22. Mathematics Expert AI": "Solve for x: (4x^2 + 5x = 9) and show steps.",
        "23. English & Literature Expert AI": "Critique this thesis: 'Hamlet is a play about procrastination.'",
        "24. History & Social Studies Expert AI": "Explain the causes and effects of the Cuban Missile Crisis.",
        "25. Foreign Language Expert AI": "Conjugate 'aller' en French, passé simple, nous.",
        "26. Science Expert AI": "Explain the concept of entropy in simple terms.",
        "27. Vocational & Applied Expert AI": "Code Debugger: 'for i in range(5) print(i)' (Python)",
        "28. Grade Calculator": "Input: Assignments 30% (85/100), Midterm 40% (92/100), Final 30% (78/100)."
    }}
}
# --- END AI & CATEGORY DATA ---


# --- APPLICATION PAGE RENDERERS ---

def render_usage_dashboard():
    """Renders the main landing page with storage visualization and plan information."""
    
    current_tier = st.session_state.storage['tier']
    total_used = st.session_state.storage['total_used_mb']
    limit = TIER_LIMITS[current_tier]
    
    # 1. Tier Label (Top Left)
    st.markdown(f'<div class="tier-label">{current_tier}</div>', unsafe_allow_html=True)
    st.title("📊 Usage Dashboard")
    st.markdown("---")
    
    # --- TOP ROW: Storage Visuals ---
    col_pie, col_bar = st.columns(2)
    
    with col_pie:
        # Pie Chart: Storage Left vs. Used (Lighter/Darker)
        st.subheader("Storage Utilization")
        
        if current_tier != 'Unlimited':
            # Calculate percentages
            used_percent = min(100, (total_used / limit) * 100) if limit != 0 else 0
            
            st.metric(label="Total Used (MB)", value=f"{total_used:.2f} MB", delta=f"{limit - total_used:.2f} MB Remaining")
            st.progress(used_percent / 100)
            st.markdown(f"**Limit:** {limit} MB")
        else:
            st.info("Storage is **Unlimited**.")

    with col_bar:
        # Bar Chart: Where Storage is Used Most
        st.subheader("Usage Breakdown")
        
        breakdown_data = pd.DataFrame({
            "Category": ["28/1 Utilities", "Teacher Aid", "General Data"],
            "Usage (MB)": [st.session_state.storage['utility_used_mb'], st.session_state.storage['teacher_used_mb'], st.session_state.storage['general_used_mb']]
        })
        
        # Use a bar chart for the breakdown
        st.bar_chart(breakdown_data, x="Category", y="Usage (MB)")


    st.markdown("---")
    
    # --- BOTTOM ROW: Storage Cleanup & Plan Info ---
    col_list, col_plans = st.columns(2)
    
    with col_list:
        # List: Specific Items Taking Most Storage
        st.subheader("🗑️ Data Cleanup (Top Usage)")
        
        for item in MOCK_TOP_USAGE:
            col_item, col_size, col_delete = st.columns([0.6, 0.2, 0.2])
            col_item.write(f"*{item['Type']}:* {item['Item']}")
            col_size.write(f"{item['Size']:.1f} MB")
            if col_delete.button("Delete", key=f"delete_{item['Item']}"):
                # Mock delete logic
                st.toast(f"🗑️ Deleted {item['Item']} (Simulated).")
                st.session_state.storage['total_used_mb'] -= item['Size'] # Mock update
                st.session_state['app_mode'] = 'Usage Dashboard' # Trigger rerun for update
                st.rerun()
                
        if not MOCK_TOP_USAGE:
            st.info("No large saved data items found.")

    with col_plans:
        # Bubble: Explain Each Plan
        st.subheader("⭐ Plan Benefits Overview")
        
        for tier, price in TIER_PRICES.items():
            st.markdown(f"##### **{tier}** ({price})")
            
            benefits = []
            if tier == "Free Tier": benefits.append(f"**{TIER_LIMITS[tier]} MB** Universal Storage.")
            elif tier == "28/1 Pro": benefits.append(f"**3 GB** Dedicated 28/1 Storage (Free Tier elsewhere).")
            elif tier == "Teacher Pro": benefits.append(f"**3 GB** Dedicated Teacher Aid Storage (Free Tier elsewhere).")
            elif tier == "Universal Pro": benefits.append(f"**5 GB** Total for ALL tools combined.")
            elif tier == "Unlimited": benefits.append("Truly Unlimited Storage and Features!")
            
            st.markdown(f"> * {'; '.join(benefits)}")

def render_main_dashboard():
    """Renders the split-screen selection for Teacher Aid and 28/1 Utilities."""
    
    # 1. Tier Label (Top Left)
    st.markdown(f'<div class="tier-label">{st.session_state.storage["tier"]}</div>', unsafe_allow_html=True)
    st.title("🖥️ Main Dashboard")
    st.caption("Access your two main application suites.")
    st.markdown("---")
    
    # Split screen (using two columns taking up equal space)
    col_teacher, col_utility = st.columns(2)
    
    with col_teacher:
        st.header("🎓 Teacher Aid")
        st.markdown("Access curriculum planning, resource generation, and saved materials management.")
        st.markdown("*(Takes up data in the Teacher Aid storage pool)*")
        if st.button("Launch Teacher Aid", key="launch_teacher_btn", use_container_width=True):
            st.session_state['app_mode'] = "Teacher Aid"
            st.rerun()

    with col_utility:
        st.header("💡 28/1 Utilities")
        st.markdown("Use 28 specialized AI tools for productivity, finance, health, and more.")
        st.markdown("*(Takes up data in the 28/1 Utilities storage pool)*")
        if st.button("Launch 28/1 Utilities", key="launch_utility_btn", use_container_width=True):
            st.session_state['app_mode'] = "28/1 Utilities"
            st.rerun()

def render_utility_hub_navigated():
    """Renders the utility hub with back button and internal navigation."""
    
    can_save, error_message = check_storage_limit('utility_save')

    # 1. Tier Label (Top Left)
    st.markdown(f'<div class="tier-label">{st.session_state.storage["tier"]}</div>', unsafe_allow_html=True)

    col_back, col_title, col_save_data = st.columns([0.15, 0.55, 0.3])
    
    # Back button logic
    if col_back.button("← Back", key="utility_back_btn"):
        st.session_state['app_mode'] = "Dashboard"
        st.rerun()

    col_title.title("💡 28/1 Utilities")

    # Save Data button
    if col_save_data.button("💾 Saved Data", key="utility_saved_data_btn", use_container_width=True):
        st.session_state['utility_view'] = 'saved'
    else:
        if st.session_state.get('utility_view') != 'main' and st.session_state.get('utility_view') != 'category':
             st.session_state['utility_view'] = 'main' # Default to main if not set

    st.markdown("---")

    if st.session_state.get('utility_view') == 'saved':
        st.header("💾 Saved Items Manager")
        st.warning("Note: Saving an item costs 1MB of your allowance + 1MB per day saved.")
        # [Saved data management logic here]
        
    else: # Main category view
        st.header("Select a Utility Category")
        
        # 8 boxes display (Description + 7 Categories)
        
        # Box 1: Explanation
        with st.container(border=True):
            st.subheader("📚 Explanation & Guide")
            st.markdown("Each category contains specialized AI tools. Select a category to proceed to the features within it.")
            
        # The 7 Category boxes (Grid format)
        categories = list(CATEGORIES_FEATURES.keys())
        cols = st.columns(3)
        
        for i, category in enumerate(categories):
            with cols[i % 3]:
                if st.button(f"{CATEGORIES_FEATURES[category]['icon']} {category}", key=f"cat_btn_{i}", use_container_width=True):
                    st.session_state['utility_active_category'] = category
                    st.session_state['utility_view'] = 'category' # Switch to feature list view
                    st.rerun()

        # If a category is selected, show its features
        if st.session_state.get('utility_view') == 'category' and 'utility_active_category' in st.session_state:
            st.markdown("---")
            st.subheader(f"Features in: {st.session_state['utility_active_category']}")
            
            # Mock save button availability
            if not can_save:
                st.error(f"🛑 {error_message}")
            else:
                 st.success("Saves are currently enabled!")

            # [Full feature rendering and execution logic goes here (similar to original render_utility_hub)]

def render_teacher_aid_navigated():
    """Renders the teacher aid app with internal navigation sidebar."""

    # 1. Tier Label (Top Left)
    st.markdown(f'<div class="tier-label">{st.session_state.storage["tier"]}</div>', unsafe_allow_html=True)
    st.title("🎓 Teacher Aid")

    # Internal Sidebar Navigation (as per your request)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎓 Teacher Aid Menu")
    
    teacher_mode = st.sidebar.radio(
        "Navigation:",
        options=["Dashboard", "Saved Data", "Data Management"],
        key="teacher_nav_radio"
    )
    st.sidebar.markdown("---")

    # Back button to the main dashboard
    if st.button("← Back to Main Dashboard", key="teacher_back_main_btn"):
        st.session_state['app_mode'] = "Dashboard"
        st.rerun()
        
    st.markdown("---")

    if teacher_mode == "Dashboard":
        st.header("Resource Generation Dashboard")
        st.info("This is the main screen for generating Unit Overviews, Lessons, Quizzes, etc. (Looks the same as your original code, without the data part).")
        # [Insert the full tab-based generation and viewing logic from the original render_teacher_aid]
        
    elif teacher_mode == "Saved Data":
        st.header("Saved Resources Manager")
        st.info("Here you can open dropdowns to access saved resources, edit their names, and manage them.")
        # [Logic to display saved data with editable names]

    elif teacher_mode == "Data Management":
        st.header("Data Management & Cleanup")
        st.info("This screen lets you manage what is taking up the most data within your Teacher Aid section, similar to the bottom-left quadrant of the Usage Dashboard.")
        # [Data management/cleanup logic for teacher resources]


def render_plan_manager():
    """Renders the plan selection, upgrade, and cancellation screen."""
    
    # 1. Tier Label (Top Left)
    st.markdown(f'<div class="tier-label">{st.session_state.storage["tier"]}</div>', unsafe_allow_html=True)
    st.title("💳 Plan Manager")
    st.header("Upgrade or Manage Your Subscription")
    st.markdown("---")
    
    cols = st.columns(5)
    tiers = list(TIER_LIMITS.keys())
    
    for i, tier in enumerate(tiers):
        with cols[i]:
            st.subheader(tier)
            st.markdown(f"## {TIER_PRICES[tier]}")
            st.markdown("---")
            
            # Display Benefits
            benefits = []
            if tier == "Free Tier": benefits.append("500MB Universal.")
            elif tier == "28/1 Pro": benefits.append("3GB Dedicated 28/1.")
            elif tier == "Teacher Pro": benefits.append("3GB Dedicated Teacher Aid.")
            elif tier == "Universal Pro": benefits.append("5GB Total Combined.")
            elif tier == "Unlimited": benefits.append("Unlimited Storage.")
            
            st.markdown(f"*{'; '.join(benefits)}*")
            st.markdown("---")

            # Action button
            if tier == st.session_state.storage['tier']:
                st.button("Current Plan", disabled=True, key=f"plan_current_{i}", use_container_width=True)
                st.button("Cancel Plan", key=f"plan_cancel_{i}", use_container_width=True)
            else:
                if st.button(f"Select {tier}", key=f"plan_upgrade_{i}", use_container_width=True):
                    # Mock upgrade logic
                    st.session_state.storage['tier'] = tier
                    save_storage_tracker(st.session_state.storage)
                    st.toast(f"✅ Upgraded to {tier}!")
                    st.rerun()


def render_data_cleanup():
    """Renders the utility for finding and cleaning up old or unused data."""
    
    # 1. Tier Label (Top Left)
    st.markdown(f'<div class="tier-label">{st.session_state.storage["tier"]}</div>', unsafe_allow_html=True)
    st.title("🧹 Data Clean Up")
    st.info("This tool helps find and purge old, large, or unused saved data across ALL tools to free up storage space.")
    st.markdown("---")
    
    st.subheader("Automated Suggestions")
    
    st.write("1. **Oldest Saves:** Found 5 items saved over 6 months ago (35.2 MB).")
    st.write("2. **Largest Saves:** Found 3 items larger than 50MB (182.1 MB).")
    st.write("3. **Unused Saves:** Found 12 items not accessed in the last 90 days (50.5 MB).")

    if st.button("Review and Delete Suggested Items", key="review_cleanup_btn", use_container_width=True):
        st.toast("Redirecting to detailed cleanup review (Mocked)...")


# --- MAIN APP LOGIC AND NAVIGATION CONTROL ---

# --- SIDEBAR NAVIGATION (Main Menu) ---
st.sidebar.image(ICON_SETTING, width=80)
st.sidebar.markdown(f"# {WEBSITE_TITLE}")
st.sidebar.markdown("---")

# Main Navigation Radio
menu_options = ["Usage Dashboard", "Dashboard", "Plan Manager", "Data Clean Up"]
mode_selection = st.sidebar.radio(
    "Application Menu:",
    options=menu_options,
    index=menu_options.index(st.session_state.get('app_mode', 'Usage Dashboard'))
)
st.session_state['app_mode'] = mode_selection # Update the state based on sidebar click


# --- TIER RESTRICTION CHECK (Runs on every page load) ---
limit_reached, error_msg = check_storage_limit('universal')
if limit_reached == False:
    st.error(f"🛑 **STORAGE LIMIT REACHED:** {error_msg}. You cannot save, type, or copy any active data until you upgrade your plan or clean up storage.")
    
    # Check if the current page is one of the management pages
    if st.session_state['app_mode'] not in ["Usage Dashboard", "Plan Manager", "Data Clean Up"]:
        st.session_state['app_mode'] = "Usage Dashboard" # Redirect them to the main management screen
        st.rerun() 
    
    # This prevents the AI functions, text inputs, and save buttons from being used
    # In the full code, you would disable all st.text_input, st.text_area, and st.button components
    # based on this 'limit_reached' flag.


# --- RENDERER DISPATCHER ---
if st.session_state['app_mode'] == "Usage Dashboard":
    render_usage_dashboard()
    
elif st.session_state['app_mode'] == "Dashboard":
    render_main_dashboard()

elif st.session_state['app_mode'] == "Plan Manager":
    render_plan_manager()
    
elif st.session_state['app_mode'] == "Data Clean Up":
    render_data_cleanup()
    
# Render the specific nested pages
elif st.session_state['app_mode'] == "28/1 Utilities":
    render_utility_hub_navigated()
    
elif st.session_state['app_mode'] == "Teacher Aid":
    render_teacher_aid_navigated()
