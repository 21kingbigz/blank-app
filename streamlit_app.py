import streamlit as st
import os
import pandas as pd
from PIL import Image
from io import BytesIO
from google import genai
from google.genai.errors import APIError 

# Import custom modules
from auth import render_login_page, logout, load_users
from storage_logic import (
    load_storage_tracker, save_storage_tracker, check_storage_limit, 
    calculate_mock_save_size, get_file_path, save_db_file, 
    UTILITY_DB_INITIAL, TEACHER_DB_INITIAL, TIER_LIMITS
)

# --- 0. CONFIGURATION AND CONSTANTS ---
WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash'
# Note: Ensure this image file exists, otherwise Streamlit will use the default icon.
LOGO_FILENAME = "image_fd0b7e.png" 
ICON_SETTING = LOGO_FILENAME if os.path.exists(LOGO_FILENAME) else "💡"

# AI client setup (Assume client setup is correct)
try:
    client = genai.Client()
except Exception:
    client = None 

try:
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    SYSTEM_INSTRUCTION = "You are a helpful and detailed assistant."
    
CATEGORIES_FEATURES = {
    "Productivity": {"icon": "📝", "features": {"1. Email Drafts": "Draft an email to a client...", "2. Summarizer": "Summarize notes...", "3. Planner": "Create a 5-step plan..."}},
    "Finance": {"icon": "💰", "features": {"4. Budget Tracker": "Analyze spending...", "5. Investment Idea": "Suggest three low-risk...", "6. Tax Explanation": "Explain the capital gains..."}},
    "Health & Fitness": {"icon": "🏋️", "features": {"7. Workout Generator": "Generate a 45-minute workout...", "8. Meal Plan Creator": "Create a 7-day high-protein...", "9. Image-to-Calorie": "Estimate calories and macros for the uploaded meal image."}},
    "Education": {"icon": "📚", "features": {"10. Study Guide": "Create a study guide...", "11. Essay Outliner": "Outline an essay..."}},
    "Coding": {"icon": "💻", "features": {"12. Code Debugger": "Find bugs in this Python script.", "13. Code Generator": "Write a simple JavaScript function."}},
}
TIER_PRICES = {
    "Free Tier": "Free", "28/1 Pro": "$7/month", "Teacher Pro": "$7/month",
    "Universal Pro": "$12/month", "Unlimited": "$18/month"
}

# Set browser tab title, favicon, and layout.
st.set_page_config(
    page_title=WEBSITE_TITLE,
    page_icon=ICON_SETTING,
    layout="wide",
    initial_sidebar_state="auto"
)

# --- CRITICAL CSS FOR LAYOUT FIXES (Simplified) ---
st.markdown(
    """
    <style>
    /* Ensure Streamlit's default style doesn't break custom components */
    .stButton>button {
        /* Standardize button appearance */
    }
    .css-1d391kg { /* Target for the main app container for responsive padding */
        padding-top: 2rem;
    }
    .tier-label {
        font-size: 0.8em;
        color: #888;
        margin-top: -15px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- AI GENERATION FUNCTION (Mocked if client fails) ---
def run_ai_generation(prompt_text: str, uploaded_file: BytesIO = None, max_tokens=1500, temp=0.5):
    if not client:
        return f"MOCK RESPONSE: Generated output for prompt: '{prompt_text[:50]}...'. (AI client not initialized)"
    
    config = {
        "temperature": temp,
        "max_output_tokens": max_tokens,
        "system_instruction": SYSTEM_INSTRUCTION
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


# --- INITIALIZATION BLOCK (CRITICAL FIX FOR PERSISTENCE) ---

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    
if st.session_state.logged_in:
    user_email = st.session_state.current_user
    
    # FIX: 1. Load user's profile FIRST to ensure we have the correct tier
    user_profile = load_users().get(user_email, {})
    
    # 2. Load user-specific DBs and Storage 
    if 'storage' not in st.session_state:
        
        storage_data = load_storage_tracker(user_email)
        
        # FIX: Force the tier from the users.json profile, which was set by auth.py
        if user_profile.get('tier'):
            storage_data['tier'] = user_profile['tier']
        
        st.session_state['storage'] = storage_data
        
    # 3. Set default application mode (Dashboard is the hub)
    if 'app_mode' not in st.session_state:
        st.session_state['app_mode'] = "Dashboard" 
    if 'utility_view' not in st.session_state:
        st.session_state['utility_view'] = 'main'
    if 'teacher_mode' not in st.session_state: 
        st.session_state['teacher_mode'] = "Resource Dashboard" 


# --- NAVIGATION RENDERER (Updated - REMOVED Teacher Aid and 28/1 Utilities tabs) ---

def render_main_navigation_sidebar():
    """Renders the main navigation using Streamlit's sidebar for responsiveness."""
    with st.sidebar:
        # Logo and Title
        col_logo, col_title = st.columns([0.25, 0.75])
        with col_logo:
            st.image(LOGO_FILENAME, width=30)
        with col_title:
            st.markdown(f"**{WEBSITE_TITLE}**")
        
        st.markdown("---")
        st.markdown(f"**User:** *{st.session_state.current_user}*")
        st.markdown(f"**Plan:** *{st.session_state.storage['tier']}*")
        st.markdown("---")

        menu_options = [
            {"label": "📊 Usage Dashboard", "mode": "Usage Dashboard"},
            {"label": "🖥️ Dashboard", "mode": "Dashboard"}, # This is the hub
            {"label": "💳 Plan Manager", "mode": "Plan Manager"},
            {"label": "🧹 Data Clean Up", "mode": "Data Clean Up"}
        ]
        
        # Use native st.button, and apply CSS class based on active mode
        for item in menu_options:
            mode = item["mode"]
            button_id = f"sidebar_nav_button_{mode.replace(' ', '_')}"
            
            if st.button(item["label"], key=button_id, use_container_width=True):
                st.session_state['app_mode'] = mode
                # Reset internal views when switching main mode
                st.session_state.pop('utility_view', None)
                st.session_state['teacher_mode'] = "Resource Dashboard"
                st.rerun()


# --- APPLICATION PAGE RENDERERS ---

def render_main_dashboard():
    """Renders the split-screen selection for Teacher Aid and 28/1 Utilities."""
    
    st.title("🖥️ Main Dashboard")
    st.caption("Access your two main application suites: **Teacher Aid** or **28/1 Utilities**.")
    st.markdown("---")
    
    col_teacher, col_utility = st.columns(2)
    
    # Navigation to Teacher Aid
    with col_teacher:
        with st.container(border=True):
            st.header("🎓 Teacher Aid")
            st.markdown("Access curriculum planning tools, resource generation, and student management features.")
            if st.button("Launch Teacher Aid", key="launch_teacher_btn", use_container_width=True):
                st.session_state['app_mode'] = "Teacher Aid"
                st.rerun()

    # Navigation to 28/1 Utilities
    with col_utility:
        with st.container(border=True):
            st.header("💡 28/1 Utilities")
            st.markdown("Use 28 specialized AI tools for productivity, finance, health, and more.")
            if st.button("Launch 28/1 Utilities", key="launch_utility_btn", use_container_width=True):
                st.session_state['app_mode'] = "28/1 Utilities"
                st.rerun()


def render_utility_hub_content(can_interact, universal_error_msg):
    """The 28/1 Utilities Hub (Feature generation and saving)"""
    
    st.title("💡 28/1 Utilities")
    st.caption(f"**Current Plan:** {st.session_state.storage['tier']}")
    st.markdown("---")
    
    if not can_interact:
        # FIX: Check if universal_error_msg is None before using it.
        display_msg = universal_error_msg if universal_error_msg else "Storage limit reached or plan data loading error."
        st.error(f"🛑 **ACCESS BLOCKED:** {display_msg}. Cannot interact with the application while over your universal limit.")
        if st.button("← Back to Dashboard", key="utility_back_btn_blocked"):
            st.session_state['app_mode'] = "Dashboard"
            st.rerun()
        return

    # Check for dedicated Utility save limit
    can_save_utility, utility_error_msg, utility_limit = check_storage_limit(st.session_state.storage, 'utility_save')

    col_category, col_main = st.columns([0.3, 0.7])
    
    # --- Category Selector (Left Sidebar) ---
    with col_category:
        st.subheader("Categories")
        category_options = list(CATEGORIES_FEATURES.keys())
        st.session_state.utility_active_category = st.radio(
            "Select a Category:", 
            options=category_options, 
            key="utility_category_radio",
            index=category_options.index(st.session_state.get('utility_active_category', category_options[0]))
        )
        
        st.markdown("---")
        # Utility Saved Items Viewer (always visible)
        st.subheader("Saved Items")
        if st.session_state.utility_db['saved_items']:
            st.info(f"Using {st.session_state.storage['utility_used_mb']:.2f} MB of {utility_limit:.0f} MB")
            
            # Simple list of saved items with view/delete
            for i, item in reversed(list(enumerate(st.session_state.utility_db['saved_items']))):
                
                with st.expander(f"**{item['name']}** - {item['size_mb']:.1f} MB"):
                    st.caption(f"Category: {item['category']}")
                    st.text_area("Saved Output", item['output'], height=150, disabled=True)
                    
                    # Delete button for saved item
                    if st.button("Delete This Item", key=f"del_util_{i}"):
                        deleted_size = item['size_mb']
                        st.session_state.utility_db['saved_items'].pop(i)
                        save_db_file(st.session_state.utility_db, get_file_path("utility_data_", st.session_state.current_user))
                        
                        # Update storage tracker
                        st.session_state.storage['utility_used_mb'] = max(0.0, st.session_state.storage['utility_used_mb'] - deleted_size)
                        st.session_state.storage['total_used_mb'] = max(0.0, st.session_state.storage['total_used_mb'] - deleted_size)
                        save_storage_tracker(st.session_state.storage, st.session_state.current_user)
                        st.toast(f"🗑️ Deleted {item['name']}!")
                        st.rerun()
        else:
            st.info("No items saved yet.")


    # --- Main Content Area (Right) ---
    with col_main:
        category = st.session_state.utility_active_category
        st.header(f"{CATEGORIES_FEATURES[category]['icon']} {category}")
        
        feature_options = CATEGORIES_FEATURES[category]['features']
        
        selected_feature = st.selectbox(
            "Select an AI Feature:", 
            options=list(feature_options.keys()), 
            format_func=lambda x: x.split(". ")[1]
        )
        
        prompt_prefix = feature_options[selected_feature]
        
        with st.form(key=f"utility_form_{selected_feature}"):
            st.subheader("Input")
            
            input_text = st.text_area(
                "Add Your Details (e.g., 'for a technology startup focusing on sustainability')",
                height=150
            )
            
            uploaded_file = None
            if 'Image-to-Calorie' in selected_feature:
                uploaded_file = st.file_uploader("Upload Image (Optional)", type=['jpg', 'jpeg', 'png'], key="utility_uploader")
            
            col_gen, col_save_status = st.columns([0.5, 0.5])
            generate_button = col_gen.form_submit_button("🚀 Generate Response", use_container_width=True)
            
            # Display save status
            if not can_save_utility:
                col_save_status.error(f"Save Blocked: {utility_error_msg.split(' ')[0]} limit reached.")
            else:
                col_save_status.success(f"Saving is enabled. Next save cost: {calculate_mock_save_size('MOCK'):.1f} MB")
        
        
        # --- Output and Saving Logic ---
        if generate_button:
            
            full_prompt = f"{prompt_prefix} {input_text}"
            
            with st.spinner("Generating response..."):
                ai_output = run_ai_generation(full_prompt, uploaded_file)
            
            st.session_state[f'utility_output_{selected_feature}'] = ai_output
            st.session_state[f'utility_prompt_{selected_feature}'] = full_prompt
            
        
        current_output = st.session_state.get(f'utility_output_{selected_feature}')
        current_prompt = st.session_state.get(f'utility_prompt_{selected_feature}')

        if current_output:
            st.subheader("AI Output")
            st.markdown(current_output)
            
            if st.button("Save Output", key=f"save_util_btn_{selected_feature}", disabled=not can_save_utility):
                
                # Check limit again before final save
                can_save, error_msg, _ = check_storage_limit(st.session_state.storage, 'utility_save')
                if not can_save:
                    st.error(error_msg)
                    st.rerun() # Rerun to refresh status
                
                # Perform Save
                save_size = calculate_mock_save_size(current_output)
                
                new_item = {
                    "name": selected_feature.split(". ")[1] + " - " + input_text[:30] + "...",
                    "category": category,
                    "prompt": current_prompt,
                    "output": current_output,
                    "size_mb": save_size
                }
                st.session_state.utility_db['saved_items'].append(new_item)
                save_db_file(st.session_state.utility_db, get_file_path("utility_data_", st.session_state.current_user))
                
                # Update storage tracker
                st.session_state.storage['utility_used_mb'] += save_size
                st.session_state.storage['total_used_mb'] += save_size
                save_storage_tracker(st.session_state.storage, st.session_state.current_user)
                
                st.success(f"Output saved! Used {save_size:.1f} MB.")
                st.rerun()


def render_teacher_aid_content(can_interact, universal_error_msg):
    """The Teacher Aid section (Resource generation and management)"""
    
    st.title("🎓 Teacher Aid")
    st.caption(f"**Current Plan:** {st.session_state.storage['tier']}")
    st.markdown("---")
    
    if not can_interact:
        # FIX: Check if universal_error_msg is None before using it.
        display_msg = universal_error_msg if universal_error_msg else "Storage limit reached or plan data loading error."
        st.error(f"🛑 **ACCESS BLOCKED:** {display_msg}. Cannot interact with the application while over your universal limit.")
        if st.button("← Back to Dashboard", key="teacher_back_btn_blocked"):
            st.session_state['app_mode'] = "Dashboard"
            st.rerun()
        return

    # Check for dedicated Teacher save limit
    can_save_teacher, teacher_error_msg, teacher_limit = check_storage_limit(st.session_state.storage, 'teacher_save')

    # --- Sidebar for Navigation ---
    teacher_nav = st.radio(
        "Teacher Tools",
        ["Resource Dashboard", "Generate New Resource"],
        key="teacher_mode_radio",
        index=0 if st.session_state['teacher_mode'] == "Resource Dashboard" else 1,
        format_func=lambda x: x.split(" ")[0], # Use only the first word for compact display
        horizontal=True
    )
    st.session_state['teacher_mode'] = teacher_nav
    st.markdown("---")
    
    # Display save status
    if not can_save_teacher:
        st.error(f"Save Blocked: {teacher_error_msg.split(' ')[0]} limit reached.")
    else:
        st.success(f"Saving is enabled. Next save cost: {calculate_mock_save_size('MOCK'):.1f} MB")

    
    # --- Content Dispatch ---
    
    if st.session_state['teacher_mode'] == "Resource Dashboard":
        st.subheader("Resource Dashboard")
        st.caption("Review, edit, and delete your saved teaching resources.")
        st.markdown(f"**Total Used for Teacher Aid:** {st.session_state.storage['teacher_used_mb']:.2f} MB of {teacher_limit:.0f} MB")
        
        # Resource Types: units, lessons, vocab, worksheets, quizzes, tests
        for resource_type in st.session_state.teacher_db.keys():
            if st.session_state.teacher_db[resource_type]:
                st.subheader(f"📁 {resource_type.title()}")
                
                for i, resource in reversed(list(enumerate(st.session_state.teacher_db[resource_type]))):
                    with st.expander(f"**{resource['name']}** - {resource['size_mb']:.1f} MB"):
                        st.caption(f"Topic: {resource['topic']}")
                        st.text_area("Content", resource['content'], height=200, disabled=True)
                        
                        # Delete button
                        if st.button("Delete Resource", key=f"del_teacher_{resource_type}_{i}"):
                            deleted_size = resource['size_mb']
                            st.session_state.teacher_db[resource_type].pop(i)
                            save_db_file(st.session_state.teacher_db, get_file_path("teacher_data_", st.session_state.current_user))
                            
                            # Update storage tracker
                            st.session_state.storage['teacher_used_mb'] = max(0.0, st.session_state.storage['teacher_used_mb'] - deleted_size)
                            st.session_state.storage['total_used_mb'] = max(0.0, st.session_state.storage['total_used_mb'] - deleted_size)
                            save_storage_tracker(st.session_state.storage, st.session_state.current_user)
                            st.toast(f"🗑️ Deleted {resource['name']}!")
                            st.rerun()
            else:
                st.info(f"No saved {resource_type} yet.")


    elif st.session_state['teacher_mode'] == "Generate New Resource":
        st.subheader("Generate New Resource")
        
        with st.form(key="teacher_gen_form"):
            col_type, col_topic = st.columns(2)
            
            resource_type = col_type.selectbox(
                "Select Resource Type",
                ["Lesson Plan", "Unit Outline", "Worksheet", "Quiz", "Vocabulary List", "Test"],
                key="resource_type"
            )
            
            topic = col_topic.text_input("Topic / Subject", key="resource_topic", placeholder="e.g., Photosynthesis or The US Civil War")
            
            grade = st.slider("Grade Level", 1, 12, 9)
            details = st.text_area("Specific Details / Learning Objectives", height=100)
            
            generate_button = st.form_submit_button("🎓 Generate Resource", use_container_width=True)

        
        # --- Generation and Save Logic ---
        if generate_button and topic:
            full_prompt = (
                f"Generate a detailed, ready-to-use {resource_type} for a {grade}th grade class "
                f"on the topic of '{topic}'. Specific requirements: {details}"
            )
            
            with st.spinner(f"Generating {resource_type} for {topic}..."):
                ai_output = run_ai_generation(full_prompt)
            
            st.session_state['teacher_gen_output'] = ai_output
            st.session_state['teacher_gen_resource_type'] = resource_type
            st.session_state['teacher_gen_topic'] = topic
            
        current_output = st.session_state.get('teacher_gen_output')
        
        if current_output:
            st.subheader("Generated Resource")
            st.markdown(current_output)
            
            if st.button("Save Resource", key="save_teacher_btn", disabled=not can_save_teacher):
                
                # Check limit again before final save
                can_save, error_msg, _ = check_storage_limit(st.session_state.storage, 'teacher_save')
                if not can_save:
                    st.error(error_msg)
                    st.rerun() 
                    
                # Perform Save
                save_size = calculate_mock_save_size(current_output)
                resource_key = st.session_state['teacher_gen_resource_type'].lower().replace(" ", "")
                
                # Map to correct DB key (lessons/units/vocab/worksheets/quizzes/tests)
                resource_db_key = {
                    'lessonplan': 'lessons', 'unitoutline': 'units', 'vocabularylist': 'vocab', 
                    'worksheet': 'worksheets', 'quiz': 'quizzes', 'test': 'tests'
                }.get(resource_key, 'lessons') # Default to lessons
                
                new_resource = {
                    "name": f"{st.session_state['teacher_gen_topic']} - {st.session_state['teacher_gen_resource_type']}",
                    "topic": st.session_state['teacher_gen_topic'],
                    "content": current_output,
                    "size_mb": save_size
                }
                st.session_state.teacher_db[resource_db_key].append(new_resource)
                save_db_file(st.session_state.teacher_db, get_file_path("teacher_data_", st.session_state.current_user))
                
                # Update storage tracker
                st.session_state.storage['teacher_used_mb'] += save_size
                st.session_state.storage['total_used_mb'] += save_size
                save_storage_tracker(st.session_state.storage, st.session_state.current_user)
                
                st.success(f"Resource saved! Used {save_size:.1f} MB.")
                st.rerun()


def render_usage_dashboard():
    """Renders the main landing page structure with functional storage graphs."""
    
    st.title("📊 Usage Dashboard")
    st.caption("Monitor your storage usage and plan benefits.")
    st.markdown("---")
    
    storage = st.session_state.storage
    
    # Check the universal limit for the current tier
    can_proceed, _, universal_limit_for_calc = check_storage_limit(storage, 'universal')
    
    # --- Prepare Data for Charts ---
    total_used = storage['total_used_mb']
    
    # FIX: Handle Unlimited tier correctly for display
    if storage['tier'] == 'Unlimited':
        used_percent = 0 
        remaining_mb_display = "Unlimited"
        total_limit_display = "Unlimited"
        universal_limit_for_calc = 10000.0 
    else:
        # Calculate the correct universal limit based on the actual tier
        current_tier = storage['tier']
        if current_tier == 'Universal Pro':
             limit = TIER_LIMITS['Universal Pro']
        elif current_tier in ['28/1 Pro', 'Teacher Pro', 'Free Tier']:
             limit = TIER_LIMITS['Free Tier']
        else:
             limit = TIER_LIMITS['Free Tier']
             
        universal_limit_for_calc = limit 
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
            st.markdown("##### 🗑️ Top Storage Consumers (Click to Delete)")
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
                        
                        # Re-load DB for thread safety before pop, as index might change on a fresh load
                        st.session_state['utility_db'] = load_db_file(get_file_path("utility_data_", user_email), UTILITY_DB_INITIAL)
                        st.session_state['teacher_db'] = load_db_file(get_file_path("teacher_data_", user_email), TEACHER_DB_INITIAL)
                        
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


def render_plan_manager():
    st.title("💳 Plan Manager")
    st.caption("Upgrade or manage your subscription plan.")
    st.markdown("---")
    
    current_tier = st.session_state.storage['tier']
    
    st.subheader(f"Your Current Plan: **{current_tier}**")
    st.markdown(f"**Monthly Price:** {TIER_PRICES.get(current_tier, 'N/A')}")
    st.markdown("---")
    
    # Simple list of upgrade options
    st.subheader("Upgrade Options")
    
    tier_order = ["Free Tier", "28/1 Pro", "Teacher Pro", "Universal Pro", "Unlimited"]
    
    # FIX: Use expander to ensure content is visible and structured
    for i, tier in enumerate(tier_order):
        price = TIER_PRICES[tier]
        limit_mb = TIER_LIMITS.get(tier, 0)
        
        if tier == 'Unlimited':
            limit_display = "Truly Unlimited Storage"
            benefit_detail = "All features enabled with no storage limits."
        else:
            limit_display = f"{limit_mb} MB"
            benefit_detail = f"Dedicated storage for {tier.split(' ')[0]} features."
            
        is_current = tier == current_tier
        
        with st.expander(f"**{tier}** - {price} {'(Current Plan)' if is_current else ''}", expanded=True):
            
            st.markdown(f"**Storage Limit:** *{limit_display}*")
            st.markdown(f"**Key Benefit:** {benefit_detail}")
            
            if is_current:
                st.success("This is your active plan.")
            else:
                st.button("Select Plan", key=f"select_plan_{tier}", disabled=True, help="Billing integration coming soon.")


def render_data_cleanup():
    st.title("🧹 Data Clean Up")
    st.caption("Review your saved data items for deletion.")
    st.markdown("---")
    
    # FIX: Direct user to the correct, single location for deletion
    st.info("To clean up specific data items and immediately reduce your storage usage, please navigate to the **📊 Usage Dashboard** and use the **🗑️ Top Storage Consumers** panel.")
    st.markdown("This section will be used for future bulk deletion and automated cleanup tools.")

# --- MAIN APP EXECUTION ---

if not st.session_state.logged_in:
    render_login_page()
else:
    # 1. RENDER MAIN NAVIGATION IN STREAMLIT'S SIDEBAR
    render_main_navigation_sidebar()

    # --- GLOBAL TIER RESTRICTION CHECK ---
    # This checks the total usage against the overall tier limit (Free Tier limit or Universal Pro limit)
    universal_limit_reached, universal_error_msg, _ = check_storage_limit(st.session_state.storage, 'universal')
    can_interact_universally = not universal_limit_reached

    # Render the tier label at the top of the main content area
    st.markdown(f'<p class="tier-label">Current Plan: {st.session_state.storage["tier"]}</p>', unsafe_allow_html=True)


    # --- RENDERER DISPATCHER ---
    if st.session_state['app_mode'] == "Usage Dashboard":
        render_usage_dashboard()
        
    elif st.session_state['app_mode'] == "Dashboard":
        render_main_dashboard()
        
    # NOTE: The following two modes are only reached via buttons on the Main Dashboard
    elif st.session_state['app_mode'] == "Teacher Aid":
        render_teacher_aid_content(can_interact_universally, universal_error_msg)
    
    elif st.session_state['app_mode'] == "28/1 Utilities":
        render_utility_hub_content(can_interact_universally, universal_error_msg)

    elif st.session_state['app_mode'] == "Plan Manager":
        render_plan_manager()
        
    elif st.session_state['app_mode'] == "Data Clean Up":
        render_data_cleanup()
