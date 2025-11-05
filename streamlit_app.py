import streamlit as st
import os
import pandas as pd
import numpy as np
import json
from PIL import Image
from io import BytesIO
from google import genai
from google.genai.errors import APIError 
from google.genai.types import HarmCategory, HarmBlockThreshold

# Import custom modules
from auth import render_login_page, logout, load_users
from storage_logic import (
    load_storage_tracker, save_storage_tracker, check_storage_limit, 
    calculate_mock_save_size, get_file_path, save_db_file, 
    UTILITY_DB_INITIAL, TEACHER_DB_INITIAL, TIER_LIMITS
)

# --- 0. CONFIGURATION AND PERSISTENCE FILE PATHS ---
WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash'
# ... (CATEGORIES_FEATURES and TIER_PRICES definitions remain the same) ...
CATEGORIES_FEATURES = {
    "Productivity": {"icon": "📝", "features": {"1. Smart Email Drafts": "Draft an email to a client regarding the Q3 budget review.", "2. Meeting Summarizer": "Summarize notes from a 30-minute standup meeting.", "3. Project Planner": "Create a 5-step plan for launching a new website."}},
    "Finance": {"icon": "💰", "features": {"4. Budget Tracker": "Analyze spending habits for the last month based on these transactions.", "5. Investment Idea Generator": "Suggest three low-risk investment ideas for a 30-year-old.", "6. Tax Explanation": "Explain the capital gains tax implications of selling stocks held for two years."}},
    "Health & Fitness": {"icon": "🏋️", "features": {"7. Workout Generator": "Generate a 45-minute full-body workout using only dumbbells.", "8. Meal Plan Creator": "Create a 7-day high-protein, low-carb meal plan.", "9. Image-to-Calorie Estimate": "Estimate calories and macros for the uploaded meal image."}},
    "Education": {"icon": "📚", "features": {"10. Study Guide Creator": "Create a study guide for linear algebra.", "11. Essay Outliner": "Outline an essay on climate change."}},
    "Coding": {"icon": "💻", "features": {"12. Code Debugger": "Find bugs in this Python script.", "13. Code Generator": "Write a simple JavaScript function."}},
    "Marketing": {"icon": "📈", "features": {"14. Ad Copy Generator": "Generate ad copy for a new coffee brand.", "15. Social Media Post": "Draft a tweet for a product launch."}},
    "Research": {"icon": "🔬", "features": {"16. Literature Review": "Summarize recent papers on AI ethics."}},
}
TIER_PRICES = {
    "Free Tier": "Free", "28/1 Pro": "$7/month", "Teacher Pro": "$7/month",
    "Universal Pro": "$12/month", "Unlimited": "$18/month"
}

# --- LOGO & ICON CONFIGURATION ---
LOGO_FILENAME = "image (13).png" 
ICON_SETTING = LOGO_FILENAME if os.path.exists(LOGO_FILENAME) else "💡"

# Set browser tab title, favicon, and layout.
st.set_page_config(
    page_title=WEBSITE_TITLE,
    page_icon=ICON_SETTING,
    layout="wide",
    initial_sidebar_state="auto"
)

# --- CRITICAL CSS FOR LAYOUT FIXES (Remains the same) ---
st.markdown(
    # ... (CSS from previous response) ...
    f"""
    <style>
    /* Global font and background */
    html, body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
        background-color: #FFFFFF;
        color: #333333;
    }}

    /* Streamlit's main app container */
    .stApp {{
        background-color: #FFFFFF;
    }}

    /* --- Streamlit Sidebar (Main Navigation) Styling --- */
    [data-testid="stSidebar"] {{
        background-color: #F0F2F6; 
        border-right: 1px solid #E0E0E0;
        padding-top: 20px; /* Adjust padding */
    }}

    /* Target st.button elements within the sidebar for navigation buttons */
    [data-testid="stSidebar"] .stButton > button {{
        width: 100%;
        text-align: left;
        padding: 12px 15px;
        border-radius: 8px;
        border: none;
        background-color: transparent; /* Default for non-active */
        color: #333333;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.2s, color 0.2s;
        margin-bottom: 5px; /* Spacing between nav items */
    }}
    
    [data-testid="stSidebar"] .stButton > button:hover:not(.active) {{
        background-color: #E0E0E0;
        color: #333333;
    }}
    
    /* Active button styling in sidebar */
    [data-testid="stSidebar"] .stButton > button.active {{
        background-color: #2D6BBE !important; /* Specific blue */
        color: white !important;
    }}

    /* Card-like containers for the Usage Dashboard and general use */
    div[data-testid="stVerticalBlock"] > div > div:nth-child(1) > div:has([data-testid="stMarkdownContainer"]) > div:first-child,
    div[data-testid="stColumn"] > div:nth-child(1) > [data-testid="stVerticalBlock"] > div > div:nth-child(1) {{
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        height: 100%; 
    }}

    /* Standard App Buttons (Primary/Darker Blue) - outside sidebar */
    .stButton>button {{
        background-color: #2D6BBE;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-weight: 600;
        transition: background-color 0.2s;
    }}
    .stButton>button:hover {{
        background-color: #255A9E;
        color: white;
    }}
    .stButton>button:disabled {{
        background-color: #A0A0A0;
        cursor: not-allowed;
        color: #E0E0E0 !important;
    }}

    /* Metrics and other styles remain the same */
    [data-testid="stMetric"] {{
        background-color: #F8F8F8;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #EAEAEA;
    }}
    [data-testid="stMetricValue"] {{
        color: #2D6BBE;
    }}
    
    .stProgress > div > div > div > div {{
        background-color: #2D6BBE;
    }}
    .stProgress > div > div > div {{
        background-color: #E0E0E0;
        border-radius: 5px;
    }}

    .tier-label {{
        color: #888888;
        background-color: transparent;
        padding: 0;
        font-size: 0.9em;
        font-weight: 600;
        margin-bottom: 15px;
        display: block;
    }}
    
    /* Hide Streamlit footer and default menu button (we'll keep the sidebar's expander) */
    #MainMenu, footer {{visibility: hidden;}}
    header {{visibility: hidden; height: 0;}} /* Ensure header is truly gone to reclaim space */

    </style>
    """,
    unsafe_allow_html=True
)

# --- INITIALIZATION BLOCK (Remains the same, relies on auth.py and storage_logic.py) ---

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    
if st.session_state.logged_in:
    user_email = st.session_state.current_user
    
    # 1. Load user-specific DBs and Storage (Fix ensures accurate calculation here)
    if 'storage' not in st.session_state:
        # Load user's profile to get current tier
        user_profile = load_users().get(user_email, {})
        
        # Load the storage tracker, which will internally update DBs and session state
        storage_data = load_storage_tracker(user_email)
        
        # Ensure the tier from the profile overrides the initial storage tier if it exists
        if user_profile.get('tier'):
            storage_data['tier'] = user_profile['tier']
        
        st.session_state['storage'] = storage_data
        
    # 2. Set default application mode
    if 'app_mode' not in st.session_state:
        st.session_state['app_mode'] = "Usage Dashboard" 
    if 'utility_view' not in st.session_state:
        st.session_state['utility_view'] = 'main'
    if 'teacher_mode' not in st.session_state: 
        st.session_state['teacher_mode'] = "Resource Dashboard" 

# AI client setup (Remains the same)
try:
    client = genai.Client()
except Exception:
    client = None 

try:
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    SYSTEM_INSTRUCTION = "You are a helpful and detailed assistant."


def run_ai_generation(prompt_text: str, uploaded_file: BytesIO = None, max_tokens=1500, temp=0.5):
    # ... (run_ai_generation remains the same) ...
    if not client:
        return f"MOCK RESPONSE: Generated output for prompt: '{prompt_text[:50]}...'. This would normally be a real AI response. (AI client not initialized)"
            
    config = {
        "system_instruction": SYSTEM_INSTRUCTION,
        "temperature": temp,
        "max_output_tokens": max_tokens,
        "safety_settings": [
            {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE},
            {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE},
            {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE},
            {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE},
        ]
    }
    
    contents = [prompt_text]
    if uploaded_file:
        try:
            img = Image.open(uploaded_file)
            contents.insert(0, img)
        except Exception:
            return "Error: Could not process the uploaded image."
            
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config
        )
        return response.text
    except APIError as e:
        return f"Gemini API Error: {e}"
    except Exception as e:
        return f"Error: An unexpected error occurred during generation: {e}"


# --- NAVIGATION RENDERER (Remains the same) ---

def render_main_navigation_sidebar():
    # ... (render_main_navigation_sidebar remains the same) ...
    """Renders the main navigation using Streamlit's sidebar for responsiveness."""
    with st.sidebar:
        # Logo and Title
        col_logo, col_title = st.columns([0.25, 0.75])
        with col_logo:
            st.image(ICON_SETTING, width=30)
        with col_title:
            st.markdown(f"**{WEBSITE_TITLE}**")
        
        st.markdown("---")
        st.markdown(f"**User:** *{st.session_state.current_user}*")
        st.markdown(f"**Plan:** *{st.session_state.storage['tier']}*")
        st.markdown("---")

        menu_options = [
            {"label": "📊 Usage Dashboard", "mode": "Usage Dashboard"},
            {"label": "🖥️ Dashboard", "mode": "Dashboard"},
            {"label": "🎓 Teacher Aid", "mode": "Teacher Aid"},
            {"label": "💡 28/1 Utilities", "mode": "28/1 Utilities"},
            {"label": "💳 Plan Manager", "mode": "Plan Manager"},
            {"label": "🧹 Data Clean Up", "mode": "Data Clean Up"}
        ]
        
        # Use native st.button, and apply CSS class based on active mode
        for item in menu_options:
            mode = item["mode"]
            button_id = f"sidebar_nav_button_{mode.replace(' ', '_')}"
            
            if st.button(item["label"], key=button_id):
                st.session_state['app_mode'] = mode
                # Reset internal views when switching main mode
                st.session_state.pop('utility_view', None)
                st.session_state.pop('utility_active_category', None)
                st.session_state['teacher_mode'] = "Resource Dashboard"
                st.rerun()
            
            # This hack injects the 'active' class using JavaScript after rendering.
            if st.session_state['app_mode'] == mode:
                st.markdown(
                    f"""
                    <script>
                        var buttons = window.parent.document.querySelectorAll('button');
                        buttons.forEach(function(btn) {{
                            if(btn.innerText.includes('{item['label']}')) {{
                                btn.classList.add('active');
                            }}
                        }});
                    </script>
                    """,
                    unsafe_allow_html=True
                )
        
        st.markdown("---")
        if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
            logout()


# --- APPLICATION PAGE RENDERERS ---

def render_usage_dashboard():
    """Renders the main landing page structure with functional storage graphs."""
    
    st.title("📊 Usage Dashboard")
    st.caption("Monitor your storage usage and plan benefits.")
    st.markdown("---")
    
    storage = st.session_state.storage
    
    # Check the universal limit for the current tier
    can_proceed, _, universal_limit = check_storage_limit(storage, 'universal')
    
    # --- Prepare Data for Charts ---
    total_used = storage['total_used_mb']
    
    # FIX: Handle Unlimited tier correctly for display
    if storage['tier'] == 'Unlimited':
        used_percent = 0 
        remaining_mb_display = "Unlimited"
        total_limit_display = "Unlimited"
        # Use a mock limit for the progress bar calculation if you insist on showing a visual, 
        # but in this fix, we'll just show the usage metrics cleanly.
        universal_limit_for_calc = 10000.0 # Arbitrary large number for visual comparison if needed
    else:
        universal_limit_for_calc = TIER_LIMITS[storage['tier']] if storage['tier'] == 'Universal Pro' else TIER_LIMITS['Free Tier']
        # Use max(0) to prevent negative results if usage somehow slightly exceeds limit
        used_percent = min(100, (total_used / universal_limit_for_calc) * 100)
        remaining_mb_display = f"{max(0, universal_limit_for_calc - total_used):.2f}"
        total_limit_display = f"{universal_limit_for_calc}"
    
    used_mb_display = f"{total_used:.2f}"

    # 2. Top Left Bar Chart Data (Usage by Area - LIVE DATA)
    data_area = pd.DataFrame({
        'Category': ['28/1 Utilities', 'Teacher Aid', 'General App Data'],
        'Used (MB)': [
            storage['utility_used_mb'], 
            storage['teacher_used_mb'], 
            storage['general_used_mb']
        ]
    }).set_index('Category')
    
    # 3. Bottom Left List Data (Specific Data Consumers)
    all_data_list = []
    # Utility data
    for i, item in enumerate(st.session_state.utility_db['saved_items']):
        all_data_list.append({"name": item.get('name', f"Utility Item #{i+1}"), "size_mb": item.get('size_mb', 0.0), "category": f"28/1 ({item.get('category', 'N/A')})", "db_key": "utility_db", "index": i})
    # Teacher data
    for db_key, resources in st.session_state.teacher_db.items():
        for i, resource in enumerate(resources):
            all_data_list.append({"name": resource.get('name', f"{db_key.title()} #{i+1}"), "size_mb": resource.get('size_mb', 0.0), "category": f"Teacher ({db_key.title()})", "db_key": db_key, "index": i})
            
    # Sort by size descending
    all_data_list_sorted = sorted(all_data_list, key=lambda x: x['size_mb'], reverse=True)


    # --- MAIN STRUCTURE ---
    col1, col2 = st.columns(2)
    
    # --- TOP LEFT: Usage by Area ---
    with col1:
        with st.container(border=True):
            st.markdown("##### 🌍 Storage Used by Area")
            st.bar_chart(data_area, use_container_width=True, height=250)

    # --- TOP RIGHT: Storage Left/Used Doughnut Chart ---
    with col2:
        with st.container(border=True):
            st.markdown("##### 💾 Universal Storage Overview")
            
            col_metric, col_donut = st.columns([0.4, 0.6])
            
            with col_metric:
                st.metric("Total Used", f"{used_mb_display} MB")
                st.metric("Total Limit", f"{total_limit_display} MB")

            with col_donut:
                # Doughnut chart implementation (CSS visualization)
                if storage['tier'] == 'Unlimited':
                    st.success("You have **Unlimited Storage**! No limits to track.")
                    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; justify-content: center; height: 100px;">
                            <div style="width: 100px; height: 100px; position: relative;">
                                <div style="width: 100%; height: 100%; border-radius: 50%; background: conic-gradient(
                                    #2D6BBE 0% {used_percent}%, 
                                    #E0E0E0 {used_percent}% 100%
                                ); position: relative; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #333; font-size: 1.2em;">
                                    <div style="width: 60%; height: 60%; border-radius: 50%; background: white; text-align: center; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #333; font-size: 1.2em;">
                                        {round(used_percent)}%
                                    </div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown(f"<p style='text-align: center; font-size: 0.9em; color: #888;'>Remaining: **{remaining_mb_display} MB**</p>", unsafe_allow_html=True)


    # --- BOTTOM ROW ---
    col3, col4 = st.columns(2)

    # --- BOTTOM LEFT: List of Specific Data Consumers (Delete Option) ---
    with col3:
        with st.container(border=True):
            st.markdown("##### 🗑️ Top Storage Consumers")
            if not all_data_list_sorted:
                st.info("No saved data found.")
            else:
                st.markdown("---")
                # Max 10 items for display
                for i, item in enumerate(all_data_list_sorted[:10]):
                    col_item, col_size, col_delete = st.columns([0.5, 0.25, 0.25])
                    
                    # Display item details
                    col_item.caption(f"{item['category']}")
                    col_item.markdown(f"**{item['name']}**")
                    col_size.write(f"{item['size_mb']:.1f} MB")

                    # Delete logic (Remains the same, but uses fixed storage logic)
                    if col_delete.button("Delete", key=f"cleanup_del_{item['db_key']}_{item['index']}_{i}", use_container_width=True):
                        deleted_size = item['size_mb']
                        user_email = st.session_state.current_user
                        
                        if item['db_key'] == 'utility_db':
                            st.session_state.utility_db['saved_items'].pop(item['index'])
                            save_db_file(st.session_state.utility_db, get_file_path("utility_data_", user_email))
                            st.session_state.storage['utility_used_mb'] = max(0.0, st.session_state.storage['utility_used_mb'] - deleted_size)
                        else: # Teacher DB
                            # Safety check for index deletion (in case of reruns)
                            if item['index'] < len(st.session_state.teacher_db[item['db_key']]):
                                st.session_state.teacher_db[item['db_key']].pop(item['index'])
                                save_db_file(st.session_state.teacher_db, get_file_path("teacher_data_", user_email))
                                st.session_state.storage['teacher_used_mb'] = max(0.0, st.session_state.storage['teacher_used_mb'] - deleted_size)
                            else:
                                st.error(f"Error: Could not find item to delete: {item['name']}")
                            
                        # Update universal usage and save tracker
                        st.session_state.storage['total_used_mb'] = max(0.0, st.session_state.storage['total_used_mb'] - deleted_size)
                        save_storage_tracker(st.session_state.storage, user_email)
                        st.toast(f"🗑️ Deleted {item['name']}!")
                        st.rerun()

    # --- BOTTOM RIGHT: Plan Explanations (Remains the same) ---
    with col4:
        with st.container(border=True):
            st.markdown("##### 📝 Plan Benefits Overview")
            st.markdown("---")
            
            PLAN_EXPLANATIONS = {
                "Free Tier": "500 MB **Universal Storage** across all features.",
                "28/1 Pro": "3 GB **Dedicated Storage** for 28/1 Utilities (Free Tier for Teacher Aid and General Data).",
                "Teacher Pro": "3 GB **Dedicated Storage** for Teacher Aid (Free Tier for 28/1 Utilities and General Data).",
                "Universal Pro": "5 GB **Total Storage** for all tools combined.",
                "Unlimited": "Truly **Unlimited Storage** and all features enabled."
            }

            for tier, benefit in PLAN_EXPLANATIONS.items():
                st.info(f"**{tier}:** {benefit}")


def render_main_dashboard():
    """Renders the split-screen selection for Teacher Aid and 28/1 Utilities."""
    
    st.title("🖥️ Main Dashboard")
    st.caption("Access your two main application suites.")
    st.markdown("---")
    
    col_teacher, col_utility = st.columns(2)
    
    # FIX: Navigation to Teacher Aid
    with col_teacher:
        with st.container(border=True):
            st.header("🎓 Teacher Aid")
            st.markdown("Access curriculum planning tools, resource generation, and student management features.")
            if st.button("Launch Teacher Aid", key="launch_teacher_btn", use_container_width=True):
                st.session_state['app_mode'] = "Teacher Aid"
                st.rerun()

    # FIX: Navigation to 28/1 Utilities
    with col_utility:
        with st.container(border=True):
            st.header("💡 28/1 Utilities")
            st.markdown("Use 28 specialized AI tools for productivity, finance, health, and more.")
            if st.button("Launch 28/1 Utilities", key="launch_utility_btn", use_container_width=True):
                st.session_state['app_mode'] = "28/1 Utilities"
                st.rerun()

# --- Other render functions (Teacher Aid, 28/1 Utilities, Plan Manager, Data Cleanup) remain structurally the same, 
# relying on the fixed logic in storage_logic.py and the corrected authentication. ---

def render_utility_hub_content(can_interact, universal_error_msg):
    # ... (Content remains the same, relying on fixed storage logic) ...
    pass

def render_teacher_aid_content(can_interact, universal_error_msg):
    # ... (Content remains the same, relying on fixed storage logic) ...
    pass

def render_plan_manager():
    # ... (Content remains the same, relying on fixed storage logic) ...
    pass
    
def render_data_cleanup():
    st.title("🧹 Data Clean Up")
    st.caption("Review your saved data items for deletion.")
    st.markdown("---")
    st.warning("Note: Deleting saved items reduces your **utility** and **teacher** usage, which affects your total storage shown in the Usage Dashboard.")
    
    # --- FIX: Content now directs to the specific deletion UI on Usage Dashboard ---
    st.info("To clean up specific data items, please navigate to the **📊 Usage Dashboard** and use the **🗑️ Top Storage Consumers** panel, which provides a list of your largest items and a delete button for each one.")
    
    # Placeholder for future bulk deletion features
    st.subheader("Future Tools:")
    st.markdown("* Automated deletion of items older than 6 months (Pro feature)")
    st.markdown("* Bulk deletion by category")

# --- MAIN APP LOGIC AND NAVIGATION CONTROL (Remains the same) ---

if not st.session_state.logged_in:
    render_login_page()
else:
    # 1. RENDER MAIN NAVIGATION IN STREAMLIT'S SIDEBAR
    render_main_navigation_sidebar()

    # --- GLOBAL TIER RESTRICTION CHECK (Runs on every page load) ---
    universal_limit_reached, universal_error_msg, _ = check_storage_limit(st.session_state.storage, 'universal')
    can_interact_universally = not universal_limit_reached

    # Render the tier label at the top of the main content area
    st.markdown(f'<p class="tier-label">Current Plan: {st.session_state.storage["tier"]}</p>', unsafe_allow_html=True)


    # --- RENDERER DISPATCHER ---
    if st.session_state['app_mode'] == "Usage Dashboard":
        render_usage_dashboard()
        
    elif st.session_state['app_mode'] == "Dashboard":
        render_main_dashboard()
        
    # Redirect Teacher/Utility launches to dedicated pages
    elif st.session_state['app_mode'] == "Teacher Aid":
        if not can_interact_universally:
            st.title("🎓 Teacher Aid")
            st.error(f"🛑 **ACCESS BLOCKED:** {universal_error_msg}. Cannot interact with the application while over your universal limit.")
            if st.button("← Back to Dashboard", key="teacher_back_btn_blocked"):
                st.session_state['app_mode'] = "Dashboard"
                st.rerun()
        else:
            render_teacher_aid_content(can_interact_universally, universal_error_msg)
    
    elif st.session_state['app_mode'] == "28/1 Utilities":
        if not can_interact_universally:
            st.title("💡 28/1 Utilities")
            st.error(f"🛑 **ACCESS BLOCKED:** {universal_error_msg}. Cannot interact with the application while over your universal limit.")
            if st.button("← Back to Dashboard", key="utility_back_btn_blocked"):
                st.session_state['app_mode'] = "Dashboard"
                st.rerun()
        else:
            render_utility_hub_content(can_interact_universally, universal_error_msg)

    elif st.session_state['app_mode'] == "Plan Manager":
        render_plan_manager()
        
    elif st.session_state['app_mode'] == "Data Clean Up":
        render_data_cleanup()
