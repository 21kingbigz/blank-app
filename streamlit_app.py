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

# Utility Hub Features (Required for 28/1 Utilities page)
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

# --- CRITICAL CSS FOR LAYOUT FIXES (Simplified for responsiveness) ---
st.markdown(
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
        padding-top: 20px;
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


# --- INITIALIZATION BLOCK ---

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

# AI client setup
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
    """Mocks AI generation if client fails, otherwise runs Gemini."""
    if not client:
        return f"MOCK RESPONSE: Generated output for prompt: '{prompt_text[:50]}...'. This would normally be a real AI response. (AI client not initialized)"
            
    # ... (rest of the run_ai_generation function remains the same)
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


# --- NAVIGATION RENDERER (Now uses st.sidebar with st.button) ---

def render_main_navigation_sidebar():
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
    
    # 1. Doughnut Chart Data (Storage Used vs. Left)
    if universal_limit == float('inf'):
        used_percent = 0 
        remaining_mb_display = "Unlimited"
        used_mb_display = f"{total_used:.2f}"
    else:
        # Use max(0) to prevent negative results if usage somehow slightly exceeds limit
        used_percent = min(100, (total_used / universal_limit) * 100)
        remaining_mb_display = f"{max(0, universal_limit - total_used):.2f}"
        used_mb_display = f"{total_used:.2f}"

    # 2. Top Left Bar Chart Data (Usage by Area - LIVE DATA)
    # CRITICAL FIX: Data starts at 0 and goes up with usage per person
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
                st.metric("Total Limit", f"{universal_limit if universal_limit != float('inf') else 'Unlimited'} MB")

            with col_donut:
                # Doughnut chart implementation (CSS visualization)
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; justify-content: center; height: 100px;">
                        <div style="width: 100px; height: 100px; position: relative;">
                            <div style="width: 100%; height: 100%; border-radius: 50%; background: conic-gradient(
                                #2D6BBE 0% {used_percent}%, 
                                #E0E0E0 {used_percent}% 100%
                            ); position: relative; display: flex; align-items: center; justify-content: center;">
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

                    # Delete logic
                    if col_delete.button("Delete", key=f"cleanup_del_{item['db_key']}_{item['index']}_{i}", use_container_width=True):
                        deleted_size = item['size_mb']
                        user_email = st.session_state.current_user
                        
                        # Handle deletion based on database key
                        if item['db_key'] == 'utility_db':
                            st.session_state.utility_db['saved_items'].pop(item['index'])
                            save_db_file(st.session_state.utility_db, get_file_path("utility_data_", user_email))
                            st.session_state.storage['utility_used_mb'] = max(0.0, st.session_state.storage['utility_used_mb'] - deleted_size)
                        else: # Teacher DB
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

    # --- BOTTOM RIGHT: Plan Explanations ---
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
    
    with col_teacher:
        with st.container(border=True):
            st.header("🎓 Teacher Aid")
            st.markdown("Access curriculum planning tools, resource generation, and student management features.")
            if st.button("Launch Teacher Aid", key="launch_teacher_btn", use_container_width=True):
                st.session_state['app_mode'] = "Teacher Aid"
                st.rerun()

    with col_utility:
        with st.container(border=True):
            st.header("💡 28/1 Utilities")
            st.markdown("Use 28 specialized AI tools for productivity, finance, health, and more.")
            if st.button("Launch 28/1 Utilities", key="launch_utility_btn", use_container_width=True):
                st.session_state['app_mode'] = "28/1 Utilities"
                st.rerun()

# --- Utility Hub RENDERERS (Abbreviated, relying on fixed storage logic) ---

def render_utility_hub_content(can_interact, universal_error_msg):
    # Check dedicated limit for utility saves
    can_save_dedicated, error_message_dedicated, _ = check_storage_limit(st.session_state.storage, 'utility_save')
    user_email = st.session_state.current_user
    
    # Back button logic
    if st.button("← Back to Dashboard", key="utility_back_btn"):
        st.session_state['app_mode'] = "Dashboard"
        st.session_state['utility_view'] = 'main'
        st.session_state.pop('utility_active_category', None)
        st.rerun()

    st.title("💡 28/1 Utilities")
    st.markdown("---")

    col_main, col_save = st.columns([0.7, 0.3])
    with col_save:
        if st.button("💾 Saved Data", key="utility_saved_data_btn", use_container_width=True, disabled=not can_interact):
            st.session_state['utility_view'] = 'saved'
            
    is_fully_blocked_for_generation_save = not can_interact or not can_save_dedicated
    block_message_for_generation_save = universal_error_msg if not can_interact else error_message_dedicated
    
    if is_fully_blocked_for_generation_save and st.session_state.get('utility_view') != 'saved':
        st.error(f"🛑 **ACTION BLOCKED:** {block_message_for_generation_save} New generation and saving are disabled.")
    
    # --- RENDER SAVED DATA VIEW ---
    if st.session_state.get('utility_view') == 'saved':
        st.header("💾 Saved 28/1 Utility Items")
        # ... (Saved data rendering logic - deletion uses corrected storage logic)
        if not can_interact: # Can't even see saved data if universal limit hit
            st.error(f"🛑 {universal_error_msg} Cannot access saved items.")
        elif not st.session_state.utility_db['saved_items']:
            st.info("No 28/1 utility items saved yet.")
        else:
            items_to_display = st.session_state.utility_db['saved_items']
            for i in range(len(items_to_display)):
                item = items_to_display[i]
                current_index = i 
                with st.expander(f"**{item.get('name', f'Saved Item #{i+1}')}** ({item.get('category', 'N/A')}) - {item.get('size_mb', 0.0):.1f}MB"):
                    if not can_interact: 
                        st.warning("Data content hidden while over universal storage limit.")
                    else:
                        st.code(item['content'], language='markdown')
                        
                        # Update name logic
                        # ...
                        
                        if st.button("🗑️ Delete This Save", key=f"delete_util_item_{current_index}"):
                            deleted_size = st.session_state.utility_db['saved_items'][current_index]['size_mb']
                            st.session_state.storage['utility_used_mb'] = max(0.0, st.session_state.storage['utility_used_mb'] - deleted_size)
                            st.session_state.storage['total_used_mb'] = max(0.0, st.session_state.storage['total_used_mb'] - deleted_size)
                            st.session_state.utility_db['saved_items'].pop(current_index)
                            save_db_file(st.session_state.utility_db, get_file_path("utility_data_", user_email))
                            save_storage_tracker(st.session_state.storage, user_email)
                            st.toast("Item deleted!")
                            st.rerun()

    # --- RENDER CATEGORY SELECTION VIEW ---
    elif st.session_state.get('utility_view') == 'main':
        st.header("Select a Utility Category")
        
        # ... (Category selection logic)

    # --- RENDER FEATURE INPUT/OUTPUT VIEW ---
    elif st.session_state.get('utility_view') == 'category' and 'utility_active_category' in st.session_state:
        # ... (Feature selection logic)
        
        selected_feature = st.selectbox(
            "Choose a specific feature:",
            options=["Select a Feature to Use"] + list(CATEGORIES_FEATURES[st.session_state['utility_active_category']]["features"].keys()),
            key="hub_feature_select",
            disabled=not can_interact
        )
        
        # ... (Input fields)

        if st.button(f"EXECUTE: {selected_feature}", key="hub_execute_btn", disabled=is_fully_blocked_for_generation_save):
            # ... (Generation logic)
            final_prompt = f"UTILITY HUB: {selected_feature}: {st.session_state.hub_text_input}"
            with st.spinner(f'🎯 Running {selected_feature}...'):
                result = run_ai_generation(final_prompt, st.session_state.calorie_image_upload_area)
                st.session_state['hub_result'] = result
                st.session_state['hub_last_feature_used'] = selected_feature
                st.session_state['hub_category'] = st.session_state['utility_active_category']
        
        if 'hub_result' in st.session_state and st.session_state.hub_last_feature_used == selected_feature:
            output_content = st.session_state['hub_result']
            st.code(output_content, language='markdown')

            if st.button("💾 Save Output", key="save_hub_output_btn", disabled=is_fully_blocked_for_generation_save):
                save_size = calculate_mock_save_size(output_content)
                
                if can_save_dedicated: # Re-check dedicated save limit right before saving
                    st.session_state.utility_db['saved_items'].append({
                        "name": f"{st.session_state.hub_last_feature_used} - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
                        "content": output_content,
                        "size_mb": save_size, # Guaranteed size_mb attribute
                        "category": st.session_state.hub_category
                    })
                    st.session_state.storage['utility_used_mb'] += save_size
                    st.session_state.storage['total_used_mb'] += save_size
                    save_db_file(st.session_state.utility_db, get_file_path("utility_data_", user_email))
                    save_storage_tracker(st.session_state.storage, user_email)
                    st.toast(f"Saved {st.session_state.hub_last_feature_used} ({save_size:.1f}MB)!")
                else:
                    st.error(f"🛑 Cannot save: {block_message_for_generation_save}")

# --- Teacher Aid RENDERERS (Abbreviated, relying on fixed storage logic) ---

def render_teacher_aid_content(can_interact, universal_error_msg):
    # Check dedicated limit for teacher saves
    can_save_dedicated, error_message_dedicated, _ = check_storage_limit(st.session_state.storage, 'teacher_save')
    user_email = st.session_state.current_user

    # ... (Back button, Title, etc.)
    
    tab_titles = ["Resource Dashboard", "Saved Data", "Data Management"]
    tabs = st.tabs(tab_titles)

    def render_teacher_resource_dashboard(tab_object):
        # ... (Dashboard logic)
        is_fully_blocked_for_gen_save_inner = not can_interact or not can_save_dedicated
        block_message_for_generation_save = universal_error_msg if not can_interact else error_message_dedicated
        
        # ... (Resource map definition)
        
        def generate_and_save_resource(tab_object, tab_name, ai_tag, db_key, ai_instruction_placeholder, is_blocked_for_gen_save_inner, block_msg):
            with tab_object:
                # ... (Input fields)
                
                if st.button(f"Generate {tab_name}", key=f"generate_{db_key}_btn", disabled=is_blocked_for_gen_save_inner):
                    if prompt:
                        final_prompt = f"TEACHER'S AID RESOURCE TAG: {ai_tag}: {prompt}"
                        with st.spinner(f'Building {tab_name} using tag "{ai_tag}"...'):
                            result = run_ai_generation(final_prompt)
                            save_size = calculate_mock_save_size(result)

                            if not is_blocked_for_gen_save_inner: 
                                st.session_state['teacher_db'][db_key].append({
                                    "name": f"{tab_name} from '{prompt[:20]}...' - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
                                    "content": result,
                                    "size_mb": save_size # Guaranteed size_mb attribute
                                })
                                st.session_state.storage['teacher_used_mb'] += save_size
                                st.session_state.storage['total_used_mb'] += save_size
                                save_db_file(st.session_state['teacher_db'], get_file_path("teacher_data_", user_email))
                                save_storage_tracker(st.session_state.storage, user_email)
                                st.success(f"{tab_name} Generated and Saved Permanently! ({save_size:.1f}MB)!")
                                st.rerun()
                            else:
                                st.error(f"🛑 Generation Blocked: {block_msg}")
                    else:
                        st.warning("Please provide a prompt to generate.")
        
        # ... (Loop through resources and call generate_and_save_resource)

    # ... (render_teacher_saved_data and render_teacher_data_management logic - adjusted for user-specific files)
    
def render_plan_manager():
    """Renders the plan selection, upgrade, and cancellation screen."""
    
    st.title("💳 Plan Manager")
    st.header("Upgrade or Manage Your Subscription")
    st.markdown("---")
    
    user_email = st.session_state.current_user
    current_tier = st.session_state.storage['tier']
    users = load_users()
    
    cols = st.columns(5)
    tiers = list(TIER_LIMITS.keys())
    
    for i, tier in enumerate(tiers):
        with cols[i]:
            with st.container(border=True):
                # ... (Plan display)

                if tier == current_tier:
                    st.button("Current Plan", disabled=True, key=f"plan_current_{i}", use_container_width=True)
                    if tier != "Free Tier" and st.button("Cancel Plan", key=f"plan_cancel_{i}", use_container_width=True):
                        # CANCELLATION
                        st.session_state.storage['tier'] = "Free Tier"
                        users[user_email]['tier'] = "Free Tier"
                        save_users(users)
                        save_storage_tracker(st.session_state.storage, user_email)
                        st.toast("🚫 Plan cancelled. Downgraded to Free Tier.")
                        st.rerun()
                else:
                    if st.button(f"Upgrade to {tier}", key=f"plan_upgrade_{i}", use_container_width=True):
                        # UPGRADE
                        st.session_state.storage['tier'] = tier
                        users[user_email]['tier'] = tier
                        save_users(users)
                        save_storage_tracker(st.session_state.storage, user_email)
                        st.toast(f"✅ Upgraded to {tier}!")
                        st.rerun()

def render_data_cleanup():
    """Renders the utility for finding and cleaning up old or unused data."""
    # ... (Cleanup logic - ensured it uses user-specific files)
    pass


# --- MAIN APP LOGIC AND NAVIGATION CONTROL ---

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
