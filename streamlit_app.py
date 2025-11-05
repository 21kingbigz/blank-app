import streamlit as st
import os
import json
import math
import pandas as pd
import numpy as np
from google import genai
from PIL import Image
from io import BytesIO
from google.genai.errors import APIError 
from google.genai.types import HarmCategory, HarmBlockThreshold

# --- 0. CONFIGURATION AND PERSISTENCE FILE PATHS ---
WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash'
# File names for permanent storage (Mocked with JSON files for persistence)
TEACHER_DATA_FILE = "teacher_data.json" 
UTILITY_DATA_FILE = "utility_data.json" 
STORAGE_TRACKER_FILE = "storage_tracker.json" 

# Utility Hub Features (Required for 28/1 Utilities page)
CATEGORIES_FEATURES = {
    "Productivity": {"icon": "📝", "features": {"1. Smart Email Drafts": "Draft an email to a client regarding the Q3 budget review.", "2. Meeting Summarizer": "Summarize notes from a 30-minute standup meeting.", "3. Project Planner": "Create a 5-step plan for launching a new website."}},
    "Finance": {"icon": "💰", "features": {"4. Budget Tracker": "Analyze spending habits for the last month based on these transactions.", "5. Investment Idea Generator": "Suggest three low-risk investment ideas for a 30-year-old.", "6. Tax Explanation": "Explain the capital gains tax implications of selling stocks held for two years."}},
    "Health & Fitness": {"icon": "🏋️", "features": {"7. Workout Generator": "Generate a 45-minute full-body workout using only dumbbells.", "8. Meal Plan Creator": "Create a 7-day high-protein, low-carb meal plan.", "9. Image-to-Calorie Estimate": "Estimate calories and macros for the uploaded meal image."}},
    # Added more categories to demonstrate the "8 boxes" concept, even if they have mock features
    "Education": {"icon": "📚", "features": {"10. Study Guide Creator": "Create a study guide for linear algebra.", "11. Essay Outliner": "Outline an essay on climate change."}},
    "Coding": {"icon": "💻", "features": {"12. Code Debugger": "Find bugs in this Python script.", "13. Code Generator": "Write a simple JavaScript function."}},
    "Marketing": {"icon": "📈", "features": {"14. Ad Copy Generator": "Generate ad copy for a new coffee brand.", "15. Social Media Post": "Draft a tweet for a product launch."}},
    "Research": {"icon": "🔬", "features": {"16. Literature Review": "Summarize recent papers on AI ethics."}},
}

# --- TIER DEFINITIONS AND STORAGE LIMITS (in MB) ---
TIER_LIMITS = {
    "Free Tier": 500,       # 500 MB universal
    "28/1 Pro": 3000,      # 3000 MB dedicated for 28/1, 500 MB for Teacher/General
    "Teacher Pro": 3000,   # 3000 MB dedicated for Teacher, 500 MB for 28/1/General
    "Universal Pro": 5000, # 5000 MB universal
    "Unlimited": float('inf')
}
TIER_PRICES = {
    "Free Tier": "Free", "28/1 Pro": "$7/month", "Teacher Pro": "$7/month",
    "Universal Pro": "$12/month", "Unlimited": "$18/month"
}

# Data consumption (simulated)
DAILY_SAVED_DATA_COST_MB = 1.0  # Saved data increases by 1MB per day for each day passed
NEW_SAVE_COST_BASE_MB = 10.0    # Base cost for a new permanent save (10MB)

# Initial structure for databases
TEACHER_DB_INITIAL = {"units": [], "lessons": [], "vocab": [], "worksheets": [], "quizzes": [], "tests": []}
UTILITY_DB_INITIAL = {"saved_items": []} # [{"name": "item_name", "content": "ai_output", "size_mb": 10, "category": "Productivity"}]
STORAGE_INITIAL = {
    "tier": "Free Tier", 
    "total_used_mb": 50.0,
    "utility_used_mb": 15.0, 
    "teacher_used_mb": 20.0,
    "general_used_mb": 15.0, # This simulates other general app usage not tied to specific saves
    "last_load_timestamp": pd.Timestamp.now().isoformat()
}

# --- LOGO & ICON CONFIGURATION ---
LOGO_FILENAME = "image (13).png" # Ensure this file exists or use a default
ICON_SETTING = LOGO_FILENAME if os.path.exists(LOGO_FILENAME) else "💡"

# Set browser tab title, favicon, and layout.
st.set_page_config(
    page_title=WEBSITE_TITLE,
    page_icon=ICON_SETTING,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CRITICAL CSS FOR THEME (White background, dark blue accents) ---
st.markdown(
    f"""
    <style>
    /* Global font and background */
    html, body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
        background-color: #FFFFFF; /* Pure white background */
        color: #333333; /* Dark gray for text */
    }}

    /* Streamlit's main app container */
    .stApp {{
        background-color: #FFFFFF;
        padding-top: 20px;
        padding-left: 30px;
        padding-right: 30px;
    }}

    /* Sidebar Styling (mimicking the image's clean, light sidebar) */
    .stSidebar {{
        background-color: #F0F2F6; /* Light gray background for sidebar */
        padding-top: 20px;
        border-right: 1px solid #E0E0E0; /* Subtle border */
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
        height: 100%; /* Ensure uniform height within columns */
    }}

    /* Buttons (Primary/Darker Blue) */
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

    /* Metrics (for storage display) */
    [data-testid="stMetric"] {{
        background-color: #F8F8F8;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #EAEAEA;
    }}
    [data-testid="stMetricValue"] {{
        color: #2D6BBE;
    }}
    
    /* Progress Bar (for storage) - make sure it's visible */
    .stProgress > div > div > div > div {{
        background-color: #2D6BBE;
    }}
    .stProgress > div > div > div {{
        background-color: #E0E0E0;
        border-radius: 5px;
    }}

    /* Custom tier label (top left of content area) */
    .tier-label {{
        color: #888888;
        background-color: transparent;
        padding: 0;
        font-size: 0.9em;
        font-weight: 600;
        margin-bottom: 15px;
        display: block;
    }}
    /* Hide Streamlit footer and menu button */
    #MainMenu, footer {{visibility: hidden;}}

    /* Custom styles for the 28/1 Utilities category buttons */
    .st-emotion-cache-1r6dmc3 {{ /* This targets the outer div of st.button */
        margin-bottom: 1rem; /* Adjust as needed for spacing between buttons */
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# --- PERSISTENCE & STORAGE FUNCTIONS (Working Logic) ---

def load_db_file(filename, initial_data):
    """Loads data from a JSON file (persistence)."""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, type(initial_data)) else initial_data
        except (json.JSONDecodeError, FileNotFoundError):
            return initial_data
    return initial_data

def save_db_file(data, filename):
    """Saves data to a JSON file (persistence)."""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        st.error(f"Error saving {filename}: {e}")

def load_storage_tracker():
    """Loads user tier and usage stats and applies daily cost."""
    data = load_db_file(STORAGE_TRACKER_FILE, STORAGE_INITIAL)
    
    # Calculate days passed since last load
    last_load = pd.Timestamp(data.get('last_load_timestamp', pd.Timestamp.now().isoformat()))
    time_delta = pd.Timestamp.now() - last_load
    days_passed = math.floor(time_delta.total_seconds() / (24 * 3600))
    
    if days_passed >= 1 and data['tier'] != 'Unlimited':
        # Apply daily usage increase to *all saved items*
        # This will need to iterate through actual saved items for true accuracy
        # For simulation, we'll apply it to the general usage counters for simplicity
        
        # Calculate total saved items from both databases
        total_utility_items = len(st.session_state.get('utility_db', UTILITY_DB_INITIAL)['saved_items'])
        total_teacher_items = sum(len(v) for v in st.session_state.get('teacher_db', TEACHER_DB_INITIAL).values())
        total_saved_items = total_utility_items + total_teacher_items

        if total_saved_items > 0:
            # Distribute the daily cost evenly or based on current distribution
            daily_cost_per_item = (days_passed * DAILY_SAVED_DATA_COST_MB) / total_saved_items if total_saved_items > 0 else 0
            
            # Apply to utility items
            for item in st.session_state.get('utility_db', UTILITY_DB_INITIAL)['saved_items']:
                item['size_mb'] += daily_cost_per_item
            
            # Apply to teacher items
            for db_key in st.session_state.get('teacher_db', UTILITY_DB_INITIAL).keys():
                for item in st.session_state.get('teacher_db', UTILITY_DB_INITIAL)[db_key]:
                    item['size_mb'] += daily_cost_per_item
            
            # Recalculate totals
            data['utility_used_mb'] = sum(item['size_mb'] for item in st.session_state.get('utility_db', UTILITY_DB_INITIAL)['saved_items'])
            data['teacher_used_mb'] = sum(item['size_mb'] for db_key in st.session_state.get('teacher_db', UTILITY_DB_INITIAL).keys() for item in st.session_state.get('teacher_db', UTILITY_DB_INITIAL)[db_key])
            data['total_used_mb'] = data['utility_used_mb'] + data['teacher_used_mb'] + data['general_used_mb']
            
            # Save the updated item sizes back to the files
            save_db_file(st.session_state.get('utility_db', UTILITY_DB_INITIAL), UTILITY_DATA_FILE)
            save_db_file(st.session_state.get('teacher_db', TEACHER_DB_INITIAL), TEACHER_DATA_FILE)
        
    data['last_load_timestamp'] = pd.Timestamp.now().isoformat()
    return data

def save_storage_tracker(data):
    """Saves user tier and usage stats."""
    save_db_file(data, STORAGE_TRACKER_FILE)
    st.session_state['storage'] = data


def check_storage_limit(action_area: str):
    """Checks if the user can perform an action based on their tier and usage.
    Returns (can_proceed: bool, error_message: str, effective_limit_mb: float).
    """
    storage = st.session_state.storage
    current_tier = storage['tier']
    
    if current_tier == "Unlimited":
        return True, None, float('inf')
        
    # --- Universal Limit Check (Most restrictive for Free/Universal) ---
    universal_limit = TIER_LIMITS[current_tier]
    
    if action_area == 'universal':
        used_mb = storage['total_used_mb']
        if used_mb >= universal_limit:
            return False, f"Total storage limit reached ({used_mb:.2f}MB / {universal_limit}MB). Please upgrade or clean up data.", universal_limit
        return True, None, universal_limit

    # --- Tiered/Dedicated Limit Check ---
    used_mb = 0.0
    effective_limit = 0.0
    
    if action_area == 'utility_save':
        used_mb = storage['utility_used_mb']
        if current_tier == '28/1 Pro': 
            effective_limit = TIER_LIMITS['28/1 Pro'] # Dedicated 3GB for 28/1
        elif current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] # Universal limit applies
        else: # Free Tier or Teacher Pro tier uses the Free Tier limit for Utility
            effective_limit = TIER_LIMITS['Free Tier']
        
    elif action_area == 'teacher_save':
        used_mb = storage['teacher_used_mb']
        if current_tier == 'Teacher Pro':
            effective_limit = TIER_LIMITS['Teacher Pro'] # Dedicated 3GB for Teacher
        elif current_tier == 'Universal Pro':
            effective_limit = TIER_LIMITS['Universal Pro'] # Universal limit applies
        else: # Free Tier or 28/1 Pro tier uses the Free Tier limit for Teacher
            effective_limit = TIER_LIMITS['Free Tier']
    
    # Check if the next save would exceed the limit
    if used_mb + NEW_SAVE_COST_BASE_MB > effective_limit:
        return False, f"Storage limit reached ({used_mb:.2f}MB / {effective_limit}MB) for your current plan's {action_area.replace('_save', '').title()} section.", effective_limit
    
    return True, None, effective_limit


# --- INITIALIZATION BLOCK ---

# Load DBs first so `load_storage_tracker` can use their sizes
if 'utility_db' not in st.session_state:
    st.session_state['utility_db'] = load_db_file(UTILITY_DATA_FILE, UTILITY_DB_INITIAL)
if 'teacher_db' not in st.session_state:
    st.session_state['teacher_db'] = load_db_file(TEACHER_DATA_FILE, TEACHER_DB_INITIAL)

# Now load storage, which will update sizes based on loaded DBs and daily cost
if 'storage' not in st.session_state:
    st.session_state['storage'] = load_storage_tracker()

if 'app_mode' not in st.session_state:
    st.session_state['app_mode'] = "Usage Dashboard" 

if 'utility_view' not in st.session_state:
    st.session_state['utility_view'] = 'main'
    
# AI client setup (Assume system_instruction.txt exists or use default)
try:
    client = genai.Client()
except Exception as e:
    # st.error(f"❌ ERROR: Gemini Client initialization failed. Check API Key: {e}")
    client = None # Set to None if initialization fails

try:
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    SYSTEM_INSTRUCTION = "You are a helpful and detailed assistant."


# --- CORE AI GENERATION FUNCTION (Mocked/Live Integration) ---
def run_ai_generation(prompt_text: str, uploaded_file: BytesIO = None, max_tokens=1500, temp=0.5):
    """Mocks AI generation if client fails, otherwise runs Gemini."""
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
        except Exception as e:
            st.error(f"Error processing image: {e}")
            return "Error: Could not process the uploaded image."
            
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config
        )
        return response.text
    except APIError as e:
        st.error(f"Gemini API Error: {e}")
        return "Error: The AI model failed to generate a response."
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred during generation."


def calculate_mock_save_size(content: str) -> float:
    """Calculates a save size based on content length, with a minimum base cost."""
    # Size in MB: Base cost + (Text length / 5000 chars per MB)
    size = NEW_SAVE_COST_BASE_MB + (len(content) / 5000.0)
    return round(size, 2)


# --- APPLICATION PAGE RENDERERS ---

def render_usage_dashboard():
    """Renders the main landing page structure with functional storage graphs."""
    
    st.title("📊 Usage Dashboard")
    st.caption("Monitor your storage usage and plan benefits.")
    st.markdown("---")
    
    storage = st.session_state.storage
    current_tier = storage['tier']
    
    # Check the universal limit for the current tier
    universal_limit = TIER_LIMITS[current_tier]
    
    # --- Prepare Data for Charts ---
    total_used = storage['total_used_mb']
    
    # 1. Doughnut Chart Data (Storage Used vs. Left)
    if universal_limit == float('inf'):
        used_percent = 0 # Cannot calculate percentage for unlimited, show 0% used
        remaining_mb_display = "Unlimited"
        used_mb_display = f"{total_used:.2f}"
    else:
        used_percent = min(100, (total_used / universal_limit) * 100)
        remaining_mb_display = f"{max(0, universal_limit - total_used):.2f}"
        used_mb_display = f"{total_used:.2f}"

    # 2. Top Left Graph Data (Usage by Area)
    data_area = pd.DataFrame({
        'Category': ['28/1 Utilities', 'Teacher Aid', 'General App Data'],
        'Used (MB)': [storage['utility_used_mb'], storage['teacher_used_mb'], storage['general_used_mb']]
    }).set_index('Category')
    
    # 3. Bottom Left List Data (Specific Data Consumers)
    all_data_list = []
    # Utility data
    for i, item in enumerate(st.session_state.utility_db['saved_items']):
        all_data_list.append({"name": item.get('name', f"Utility Item #{i+1}"), "size_mb": item.get('size_mb', 0), "category": f"28/1 ({item.get('category', 'N/A')})", "db_key": "utility_db", "index": i})
    # Teacher data
    for db_key, resources in st.session_state.teacher_db.items():
        for i, resource in enumerate(resources):
            all_data_list.append({"name": resource.get('name', f"{db_key.title()} #{i+1}"), "size_mb": resource.get('size_mb', 0), "category": f"Teacher ({db_key.title()})", "db_key": db_key, "index": i})
            
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
                # Doughnut chart implementation
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
                        
                        # Handle deletion based on database key
                        if item['db_key'] == 'utility_db':
                            st.session_state.utility_db['saved_items'].pop(item['index'])
                            save_db_file(st.session_state.utility_db, UTILITY_DATA_FILE)
                            st.session_state.storage['utility_used_mb'] = max(0, st.session_state.storage['utility_used_mb'] - deleted_size)
                        else: # Teacher DB
                            # Need to find the correct item based on its original index in the specific category list
                            # The 'item['index']' here refers to its index in the *original* list for its category
                            if item['index'] < len(st.session_state.teacher_db[item['db_key']]):
                                st.session_state.teacher_db[item['db_key']].pop(item['index'])
                                save_db_file(st.session_state.teacher_db, TEACHER_DATA_FILE)
                                st.session_state.storage['teacher_used_mb'] = max(0, st.session_state.storage['teacher_used_mb'] - deleted_size)
                            else:
                                st.error(f"Error: Could not find item to delete: {item['name']}")
                            
                        # Update universal usage
                        st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - deleted_size)
                        save_storage_tracker(st.session_state.storage)
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
    
    # Combined space layout (as requested: top-left/bottom-left combined for Teacher, top-right/bottom-right combined for 28/1)
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


def render_utility_hub_navigated(can_interact, universal_error_msg):
    """Renders the utility hub with back button and internal navigation."""
    
    # Check dedicated limit for utility saves
    can_save_dedicated, error_message_dedicated, _ = check_storage_limit('utility_save')
    
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
            
    # Determine if *any* interaction within this section (generation/saving) is blocked
    is_fully_blocked_for_generation_save = not can_interact or not can_save_dedicated
    block_message_for_generation_save = universal_error_msg if not can_interact else error_message_dedicated
    
    if is_fully_blocked_for_generation_save and st.session_state.get('utility_view') != 'saved':
        st.error(f"🛑 **ACTION BLOCKED:** {block_message_for_generation_save} New generation and saving are disabled.")
    
    # --- RENDER SAVED DATA VIEW ---
    if st.session_state.get('utility_view') == 'saved':
        st.header("💾 Saved 28/1 Utility Items")
        if not can_interact: # Can't even see saved data if universal limit hit
            st.error(f"🛑 {universal_error_msg} Cannot access saved items.")
        elif not st.session_state.utility_db['saved_items']:
            st.info("No 28/1 utility items saved yet.")
        else:
            items_to_display = st.session_state.utility_db['saved_items']
            for i in range(len(items_to_display)):
                item = items_to_display[i]
                current_index = i 
                with st.expander(f"**{item.get('name', f'Saved Item #{i+1}')}** ({item.get('category', 'N/A')}) - {item.get('size_mb', 0):.1f}MB"):
                    # Blocking data display if universal limit hit (only for content, names are fine)
                    if not can_interact: 
                        st.warning("Data content hidden while over universal storage limit.")
                    else:
                        st.code(item['content'], language='markdown')
                        
                        new_name = st.text_input("Edit Save Name:", value=item.get('name', ''), key=f"edit_util_name_{current_index}", disabled=not can_interact)
                        
                        if new_name != item.get('name', '') and st.button("Update Name", key=f"update_util_name_btn_{current_index}", disabled=not can_interact):
                            st.session_state.utility_db['saved_items'][current_index]['name'] = new_name
                            save_db_file(st.session_state.utility_db, UTILITY_DATA_FILE)
                            st.toast("Name updated!")
                            st.rerun()
                        
                        if st.button("🗑️ Delete This Save", key=f"delete_util_item_{current_index}"):
                            deleted_size = st.session_state.utility_db['saved_items'][current_index]['size_mb']
                            st.session_state.storage['utility_used_mb'] = max(0, st.session_state.storage['utility_used_mb'] - deleted_size)
                            st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - deleted_size)
                            st.session_state.utility_db['saved_items'].pop(current_index)
                            save_db_file(st.session_state.utility_db, UTILITY_DATA_FILE)
                            save_storage_tracker(st.session_state.storage)
                            st.toast("Item deleted!")
                            st.rerun()

    # --- RENDER CATEGORY SELECTION VIEW ---
    elif st.session_state.get('utility_view') == 'main':
        st.header("Select a Utility Category")
        
        with st.container(border=True):
            st.subheader("📚 Explanation & Guide")
            st.markdown("Each category contains specialized AI tools. Select a category to proceed to the features within it.")
            
        categories = list(CATEGORIES_FEATURES.keys())
        # Use columns for "8 boxes" layout (dynamically adjusts for more/fewer)
        num_cols = 3 
        cols = st.columns(num_cols)
        
        for i, category in enumerate(categories):
            with cols[i % num_cols]:
                if st.button(f"{CATEGORIES_FEATURES[category]['icon']} {category}", key=f"cat_btn_{i}", use_container_width=True, disabled=not can_interact):
                    st.session_state['utility_active_category'] = category
                    st.session_state['utility_view'] = 'category'
                    st.rerun()

    # --- RENDER FEATURE INPUT/OUTPUT VIEW ---
    elif st.session_state.get('utility_view') == 'category' and 'utility_active_category' in st.session_state:
        st.markdown("---")
        active_category = st.session_state['utility_active_category']
        st.subheader(f"Features in: {active_category}")
        
        category_data = CATEGORIES_FEATURES[active_category]
        features = list(category_data["features"].keys())

        # Back button for category view
        if st.button("← Back to Categories", key="back_to_categories_btn"):
            st.session_state['utility_view'] = 'main'
            st.session_state.pop('utility_active_category', None)
            st.rerun()
            
        selected_feature = st.selectbox(
            "Choose a specific feature:",
            options=["Select a Feature to Use"] + features,
            key="hub_feature_select",
            disabled=not can_interact
        )
        
        user_input = ""
        uploaded_file = None
        image_needed = (selected_feature == "9. Image-to-Calorie Estimate")
        
        if selected_feature != "Select a Feature to Use":
            
            if image_needed:
                uploaded_file = st.file_uploader("Upload Meal Photo (Feature 9 Only)", type=["jpg", "jpeg", "png"], key="calorie_image_upload_area", disabled=not can_interact)
                if uploaded_file:
                    st.image(Image.open(uploaded_file), caption="Meal to Analyze", width=250)
                    
            example_prompt = category_data["features"][selected_feature]
            st.info(f"💡 **Example Input:** `{example_prompt}`")

            user_input = st.text_area(
                "Enter your required data:",
                value="",
                placeholder=example_prompt,
                key="hub_text_input",
                disabled=is_fully_blocked_for_generation_save # Block typing if over limit
            )

            if st.button(f"EXECUTE: {selected_feature}", key="hub_execute_btn", disabled=is_fully_blocked_for_generation_save):
                if image_needed and uploaded_file is None:
                    st.error("Please upload an image.")
                elif not user_input and not image_needed:
                     st.error("Please provide text input.")
                else:
                    final_prompt = f"UTILITY HUB: {selected_feature}: {user_input}"
                    with st.spinner(f'🎯 Running {selected_feature}...'):
                        result = run_ai_generation(final_prompt, uploaded_file)
                        st.session_state['hub_result'] = result
                        st.session_state['hub_last_feature_used'] = selected_feature
                        st.session_state['hub_category'] = active_category
            
            st.markdown("---")
            st.subheader("Hub Output")

            if 'hub_result' in st.session_state and st.session_state.hub_last_feature_used == selected_feature:
                st.markdown(f"##### Result for: **{st.session_state.hub_last_feature_used}**")
                output_content = st.session_state['hub_result']
                st.code(output_content, language='markdown')

                if st.button("💾 Save Output", key="save_hub_output_btn", disabled=is_fully_blocked_for_generation_save):
                    save_size = calculate_mock_save_size(output_content)
                    
                    if can_save_dedicated: # Re-check dedicated save limit right before saving
                        st.session_state.utility_db['saved_items'].append({
                            "name": f"{st.session_state.hub_last_feature_used} - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
                            "content": output_content,
                            "size_mb": save_size,
                            "category": st.session_state.hub_category
                        })
                        st.session_state.storage['utility_used_mb'] += save_size
                        st.session_state.storage['total_used_mb'] += save_size
                        save_db_file(st.session_state.utility_db, UTILITY_DATA_FILE)
                        save_storage_tracker(st.session_state.storage)
                        st.toast(f"Saved {st.session_state.hub_last_feature_used} ({save_size:.1f}MB)!")
                    else:
                        st.error(f"🛑 Cannot save: {block_message_for_generation_save}")


def render_teacher_aid_navigated(can_interact, universal_error_msg):
    """Renders the teacher aid app with internal navigation sidebar."""
    
    # Check dedicated limit for teacher saves
    can_save_dedicated, error_message_dedicated, _ = check_storage_limit('teacher_save')
    
    # Back button logic
    if st.button("← Back to Dashboard", key="teacher_back_main_btn"):
        st.session_state['app_mode'] = "Dashboard"
        st.rerun()

    st.title("🎓 Teacher Aid")
    st.caption("Curriculum manager and resource generator.")
    
    st.markdown("---")
    
    # Internal sidebar for Teacher Aid (as requested)
    teacher_mode = st.sidebar.radio(
        "Teacher Aid Menu:",
        options=["Resource Dashboard", "Saved Data", "Data Management"],
        key="teacher_nav_radio"
    )

    # Determine if *any* interaction within this section (generation/saving) is blocked
    is_fully_blocked_for_generation_save = not can_interact or not can_save_dedicated
    block_message_for_generation_save = universal_error_msg if not can_interact else error_message_dedicated
    
    if is_fully_blocked_for_generation_save and teacher_mode == "Resource Dashboard":
        st.error(f"🛑 **ACTION BLOCKED:** {block_message_for_generation_save} New generation and saving are disabled.")
        
    # --- RENDER RESOURCE DASHBOARD ---
    if teacher_mode == "Resource Dashboard":
        st.header("Resource Generation Dashboard")
        st.info("Generate new units, lessons, quizzes, and more. All resources are saved permanently.")
        
        RESOURCE_MAP = {
            "Unit Overview": {"tag": "Unit Overview", "key": "units", "placeholder": "Generate a detailed unit plan for a 10th-grade World History class on the Renaissance."},
            "Lesson Plan": {"tag": "Lesson Plan", "key": "lessons", "placeholder": "Create a 45-minute lesson plan on Newton's First Law of Motion for 9th-grade science."},
            "Vocabulary List": {"tag": "Vocabulary List", "key": "vocab", "placeholder": "Generate 10 vocabulary words for a 5th-grade math lesson on fractions."},
            "Worksheet": {"tag": "Worksheet", "key": "worksheets", "placeholder": "Create a 10-question worksheet on subject-verb agreement for 7th-grade English."},
            "Quiz": {"tag": "Quiz", "key": "quizzes", "placeholder": "Generate a 5-question multiple-choice quiz on the causes of the American Civil War."},
            "Test": {"tag": "Test", "key": "tests", "placeholder": "Design a comprehensive end-of-unit test for a high school economics class on supply and demand."}
        }
        
        tab_titles = list(RESOURCE_MAP.keys())
        tabs = st.tabs(tab_titles)

        def generate_and_save_resource(tab_object, tab_name, ai_tag, db_key, ai_instruction_placeholder, can_save_flag, error_msg_flag, is_blocked_for_gen_save):
            with tab_object:
                st.subheader(f"1. Generate {tab_name}")
                prompt = st.text_area(
                    f"Enter details for the {tab_name.lower()}:",
                    placeholder=ai_instruction_placeholder,
                    key=f"{db_key}_prompt",
                    height=150,
                    disabled=is_blocked_for_gen_save # Block typing if over limit
                )
                if st.button(f"Generate {tab_name}", key=f"generate_{db_key}_btn", disabled=is_blocked_for_gen_save):
                    if prompt:
                        final_prompt = f"TEACHER'S AID RESOURCE TAG: {ai_tag}: {prompt}"
                        with st.spinner(f'Building {tab_name} using tag "{ai_tag}"...'):
                            result = run_ai_generation(final_prompt)
                            save_size = calculate_mock_save_size(result)

                            if can_save_flag and not is_blocked_for_gen_save: # Re-check dedicated save limit right before saving
                                st.session_state['teacher_db'][db_key].append({
                                    "name": f"{tab_name} from '{prompt[:20]}...' - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
                                    "content": result,
                                    "size_mb": save_size
                                })
                                st.session_state.storage['teacher_used_mb'] += save_size
                                st.session_state.storage['total_used_mb'] += save_size
                                save_db_file(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                                save_storage_tracker(st.session_state.storage)
                                st.success(f"{tab_name} Generated and Saved Permanently! ({save_size:.1f}MB)!")
                                st.rerun()
                            elif is_blocked_for_gen_save:
                                st.error(f"🛑 Generation Blocked: {block_message_for_generation_save}")
                            else:
                                st.error(f"🛑 Cannot save {tab_name}: {error_msg_flag}")
                    else:
                        st.warning("Please provide a prompt to generate.")


        for i, (name, data) in enumerate(RESOURCE_MAP.items()):
            generate_and_save_resource(tabs[i], name, data["tag"], data["key"], data["placeholder"], can_save_dedicated, error_message_dedicated, is_fully_blocked_for_generation_save)

    # --- RENDER SAVED DATA VIEW ---
    elif teacher_mode == "Saved Data":
        st.header("Saved Resources Manager")
        st.info("View, edit, or delete all your generated Teacher Aid resources.")
        
        if not can_interact: # Can't even see saved data if universal limit hit
            st.error(f"🛑 {universal_error_msg} Cannot access saved items.")
        else:
            # Dropdown menu to select category (as requested)
            category_options = list(st.session_state['teacher_db'].keys())
            selected_category = st.selectbox("Choose a resource category:", category_options)
            
            resources = st.session_state['teacher_db'].get(selected_category, [])

            if not resources:
                st.info(f"No saved {selected_category.title()} data found.")
                return

            # Display saved items
            for i in range(len(resources)):
                resource_item = resources[i]
                current_index = i
                expander_label = f"**{resource_item.get('name', f'{selected_category.title()} #{i+1}')}** - {resource_item.get('size_mb', 0):.1f}MB"
                with st.expander(expander_label):
                    # Blocking data display if universal limit hit (only for content, names are fine)
                    if not can_interact: 
                        st.warning("Data content hidden while over universal storage limit.")
                    else:
                        st.code(resource_item['content'], language='markdown')
                        
                        # Editable Save Name (as requested)
                        new_name = st.text_input("Edit Save Name:", value=resource_item.get('name', ''), key=f"edit_saved_teacher_name_{selected_category}_{current_index}", disabled=not can_interact)
                        
                        if new_name != resource_item.get('name', '') and st.button("Update Name", key=f"update_teacher_name_btn_{selected_category}_{current_index}", disabled=not can_interact):
                            st.session_state['teacher_db'][selected_category][current_index]['name'] = new_name
                            save_db_file(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                            st.toast("Name updated!")
                            st.rerun()
                        
                        if st.button("🗑️ Delete This Save", key=f"delete_saved_teacher_{selected_category}_{current_index}"):
                            deleted_size = st.session_state['teacher_db'][selected_category][current_index]['size_mb']
                            st.session_state.storage['teacher_used_mb'] = max(0, st.session_state.storage['teacher_used_mb'] - deleted_size)
                            st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - deleted_size)
                            st.session_state['teacher_db'][selected_category].pop(current_index)
                            save_db_file(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                            save_storage_tracker(st.session_state.storage)
                            st.toast("Resource deleted!")
                            st.rerun()

    # --- RENDER DATA MANAGEMENT VIEW ---
    elif teacher_mode == "Data Management":
        st.header("Data Management & Cleanup")
        st.info("Manage what's taking up the most space in your Teacher Aid section.")
        
        if not can_interact: # Can't even see data management if universal limit hit
            st.error(f"🛑 {universal_error_msg} Cannot access data management.")
        else:
            teacher_data_list = []
            for db_key, resources in st.session_state['teacher_db'].items():
                for i, resource in enumerate(resources):
                    teacher_data_list.append({
                        "name": resource.get('name', f"{db_key.title()} #{i+1}"),
                        "size_mb": resource.get('size_mb', 0),
                        "category": db_key,
                        "index": i # Store original index for direct deletion
                    })
            
            teacher_data_list_sorted = sorted(teacher_data_list, key=lambda x: x['size_mb'], reverse=True)
            total_teacher_mb = sum(item['size_mb'] for item in teacher_data_list_sorted)

            st.metric("Total Teacher Aid Usage", f"{total_teacher_mb:.2f} MB")
            
            if teacher_data_list_sorted:
                st.subheader("All Teacher Aid Data Consumers")
                for i, item in enumerate(teacher_data_list_sorted):
                    col_item, col_size, col_delete = st.columns([0.6, 0.2, 0.2])
                    col_item.write(f"*{item['category'].title()}:* **{item['name']}**")
                    col_size.write(f"{item['size_mb']:.1f} MB")

                    if col_delete.button("Delete", key=f"clean_teacher_{item['category']}_{item['index']}_{i}"):
                        # Use the stored original index to pop from the correct list
                        if item['index'] < len(st.session_state['teacher_db'][item['category']]):
                            deleted_size = item['size_mb']
                            st.session_state.storage['teacher_used_mb'] = max(0, st.session_state.storage['teacher_used_mb'] - deleted_size)
                            st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - deleted_size)
                            st.session_state['teacher_db'][item['category']].pop(item['index'])
                            save_db_file(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                            save_storage_tracker(st.session_state.storage)
                            st.toast(f"🗑️ Deleted {item['name']}!")
                            st.rerun()
                        else:
                            st.error(f"Error finding item for deletion: {item['name']}")
            else:
                st.info("No saved Teacher Aid data to manage.")


def render_plan_manager():
    """Renders the plan selection, upgrade, and cancellation screen."""
    
    st.title("💳 Plan Manager")
    st.header("Upgrade or Manage Your Subscription")
    st.markdown("---")
    
    cols = st.columns(5)
    tiers = list(TIER_LIMITS.keys())
    
    for i, tier in enumerate(tiers):
        with cols[i]:
            with st.container(border=True):
                st.subheader(tier)
                st.markdown(f"## {TIER_PRICES[tier]}")
                st.markdown("---")
                
                # Benefits structure as requested
                benefits = []
                if tier == "Free Tier": benefits.append(f"**{TIER_LIMITS[tier]} MB** Universal Storage.")
                elif tier == "28/1 Pro": benefits.append(f"**3 GB** Dedicated 28/1 Storage (Free Tier for Teacher Aid and General Data).")
                elif tier == "Teacher Pro": benefits.append(f"**3 GB** Dedicated Teacher Aid Storage (Free Tier for 28/1 Utilities and General Data).")
                elif tier == "Universal Pro": benefits.append(f"**5 GB** Total Storage for all tools combined.")
                elif tier == "Unlimited": benefits.append("Truly **Unlimited Storage** and all features enabled.")
                
                for benefit in benefits:
                    st.markdown(f"- {benefit}")
                st.markdown("---")

                if tier == st.session_state.storage['tier']:
                    st.button("Current Plan", disabled=True, key=f"plan_current_{i}", use_container_width=True)
                    if tier != "Free Tier" and st.button("Cancel Plan", key=f"plan_cancel_{i}", use_container_width=True):
                        # MOCK CANCELLATION
                        st.session_state.storage['tier'] = "Free Tier"
                        save_storage_tracker(st.session_state.storage)
                        st.toast("🚫 Plan cancelled. Downgraded to Free Tier.")
                        st.rerun()
                else:
                    if st.button(f"Upgrade to {tier}", key=f"plan_upgrade_{i}", use_container_width=True):
                        # DEMO ONLY: Simulate immediate upgrade
                        st.session_state.storage['tier'] = tier
                        save_storage_tracker(st.session_state.storage)
                        st.toast(f"✅ Simulated upgrade to {tier}!")
                        st.rerun()


def render_data_cleanup():
    """Renders the utility for finding and cleaning up old or unused data."""
    
    st.title("🧹 Data Clean Up")
    st.info("This tool helps find and purge old, large, or unused saved data across ALL tools to free up storage space.")
    st.markdown("---")
    
    # Simple check for universal access
    can_proceed, error_msg, _ = check_storage_limit('universal')
    
    st.subheader("Storage Utilization")
    total_used = st.session_state.storage['total_used_mb']
    limit = TIER_LIMITS[st.session_state.storage['tier']]
    used_percent = min(100, (total_used / limit) * 100) if limit != float('inf') and limit > 0 else 0
    st.metric(label="Total Storage Used", value=f"{total_used:.2f} MB", delta=f"{limit if limit != float('inf') else 'Unlimited'} MB Total")
    if limit != float('inf'):
        st.progress(used_percent / 100)
    
    st.markdown("---")
    
    if not can_proceed:
        st.error(f"🛑 {error_msg} You must clean up data or upgrade before saving more.")
        
    st.subheader("Automated Suggestions (Simulated)")
    
    total_utility_items = len(st.session_state.utility_db['saved_items'])
    total_teacher_items = sum(len(v) for v in st.session_state.teacher_db.values())
    total_saved_items = total_utility_items + total_teacher_items

    total_mb_from_saves = st.session_state.storage['utility_used_mb'] + st.session_state.storage['teacher_used_mb']
    
    st.write(f"1. **Total Saved Items:** Found **{total_saved_items}** items saved (**{total_mb_from_saves:.2f} MB**).")
    st.write("2. **Oldest Saves:** Items saved over 6 months ago (Simulated **35.2 MB**).")
    st.write("3. **Largest Saves:** Largest items (Simulated **182.1 MB**).")
    
    if st.button("Simulate Bulk Delete of Suggested Items", key="review_cleanup_btn", use_container_width=True, disabled=total_mb_from_saves < NEW_SAVE_COST_BASE_MB):
        if total_mb_from_saves > NEW_SAVE_COST_BASE_MB:
            mock_deleted_size = total_mb_from_saves * 0.25 # Delete 25% of current saved data
            
            # Reduce actual saved items (simplistic, just removes from end)
            num_to_delete_util = int(len(st.session_state.utility_db['saved_items']) * 0.25)
            st.session_state.utility_db['saved_items'] = st.session_state.utility_db['saved_items'][:-num_to_delete_util]
            
            # For teacher_db, delete from a random category for simulation
            if any(st.session_state.teacher_db.values()):
                random_category_key = np.random.choice(list(st.session_state.teacher_db.keys()))
                num_to_delete_teacher = int(len(st.session_state.teacher_db[random_category_key]) * 0.25)
                st.session_state.teacher_db[random_category_key] = st.session_state.teacher_db[random_category_key][:-num_to_delete_teacher]

            # Recalculate usage after deletion
            st.session_state.storage['utility_used_mb'] = sum(item['size_mb'] for item in st.session_state.utility_db['saved_items'])
            st.session_state.storage['teacher_used_mb'] = sum(item['size_mb'] for db_key in st.session_state.teacher_db.keys() for item in st.session_state.teacher_db[db_key])
            st.session_state.storage['total_used_mb'] = st.session_state.storage['utility_used_mb'] + st.session_state.storage['teacher_used_mb'] + st.session_state.storage['general_used_mb']
            
            save_db_file(st.session_state.utility_db, UTILITY_DATA_FILE)
            save_db_file(st.session_state.teacher_db, TEACHER_DATA_FILE)
            save_storage_tracker(st.session_state.storage)
            st.toast(f"🧹 Successfully cleaned up {mock_deleted_size:.1f}MB of data (Simulated)!")
            st.rerun()
        else:
            st.info("Not enough data saved to perform a significant cleanup.")


# --- MAIN APP LOGIC AND NAVIGATION CONTROL ---

# --- SIDEBAR NAVIGATION (Main Menu) ---
with st.sidebar:
    col_logo, col_title = st.columns([0.25, 0.75])
    with col_logo:
        st.image(ICON_SETTING, width=40)
    with col_title:
        st.markdown(f"## {WEBSITE_TITLE}")
    
    st.markdown("---")
    st.markdown(f"Current Plan: **{st.session_state.storage['tier']}**")
    st.markdown("---")

    menu_options = ["Usage Dashboard", "Dashboard", "Plan Manager", "Data Clean Up"]
    
    try:
        current_index = menu_options.index(st.session_state.get('app_mode', 'Usage Dashboard'))
    except ValueError:
        current_index = 0

    mode_selection = st.radio(
        "Application Menu:",
        options=menu_options,
        index=current_index,
        key="main_mode_select"
    )
    
    if mode_selection != st.session_state.get('app_mode', 'Usage Dashboard'):
        st.session_state['app_mode'] = mode_selection
        # Reset internal views when switching main app mode
        st.session_state.pop('utility_view', None)
        st.session_state.pop('utility_active_category', None)
        st.rerun()


# --- GLOBAL TIER RESTRICTION CHECK (Runs on every page load) ---
universal_limit_reached, universal_error_msg, _ = check_storage_limit('universal')
can_interact_universally = not universal_limit_reached

# Render the tier label at the top of the main content area
st.markdown(f'<p class="tier-label">Current Plan: {st.session_state.storage["tier"]}</p>', unsafe_allow_html=True)


# --- RENDERER DISPATCHER ---
if st.session_state['app_mode'] == "Usage Dashboard":
    render_usage_dashboard()
    
elif st.session_state['app_mode'] == "Dashboard":
    render_main_dashboard()

elif st.session_state['app_mode'] == "Plan Manager":
    render_plan_manager()
    
elif st.session_state['app_mode'] == "Data Clean Up":
    render_data_cleanup()
    
elif st.session_state['app_mode'] == "28/1 Utilities":
    # If universal limit is reached, access is blocked immediately for all interaction
    if not can_interact_universally:
        st.title("💡 28/1 Utilities")
        st.error(f"🛑 **ACCESS BLOCKED:** {universal_error_msg}. Cannot interact with the application while over your universal limit.")
        if st.button("← Back to Dashboard", key="utility_back_btn_blocked"):
            st.session_state['app_mode'] = "Dashboard"
            st.rerun()
    else:
        render_utility_hub_navigated(can_interact_universally, universal_error_msg)
    
elif st.session_state['app_mode'] == "Teacher Aid":
    # If universal limit is reached, access is blocked immediately for all interaction
    if not can_interact_universally:
        st.title("🎓 Teacher Aid")
        st.error(f"🛑 **ACCESS BLOCKED:** {universal_error_msg}. Cannot interact with the application while over your universal limit.")
        if st.button("← Back to Dashboard", key="teacher_back_btn_blocked"):
            st.session_state['app_mode'] = "Dashboard"
            st.rerun()
    else:
        render_teacher_aid_navigated(can_interact_universally, universal_error_msg)
