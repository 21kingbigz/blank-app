import streamlit as st
import os
import json
import math
import pandas as pd
import numpy as np
from google import genai
from PIL import Image
from io import BytesIO
from google.genai.errors import APIError # Correct Import
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
    "Productivity": {
        "icon": "📝",
        "features": {
            "1. Smart Email Drafts": "Draft an email to a client regarding the Q3 budget review.",
            "2. Meeting Summarizer": "Summarize notes from a 30-minute standup meeting.",
            "3. Project Planner": "Create a 5-step plan for launching a new website."
        }
    },
    "Finance": {
        "icon": "💰",
        "features": {
            "4. Budget Tracker": "Analyze spending habits for the last month based on these transactions.",
            "5. Investment Idea Generator": "Suggest three low-risk investment ideas for a 30-year-old.",
            "6. Tax Explanation": "Explain the capital gains tax implications of selling stocks held for two years."
        }
    },
    "Health & Fitness": {
        "icon": "🏋️",
        "features": {
            "7. Workout Generator": "Generate a 45-minute full-body workout using only dumbbells.",
            "8. Meal Plan Creator": "Create a 7-day high-protein, low-carb meal plan.",
            "9. Image-to-Calorie Estimate": "Estimate calories and macros for the uploaded meal image."
        }
    }
}


# Tier Definitions and Storage Limits (in MB)
TIER_LIMITS = {
    "Free Tier": 500,
    "28/1 Pro": 3000,
    "Teacher Pro": 3000,
    "Universal Pro": 5000,
    "Unlimited": float('inf')
}
TIER_PRICES = {
    "Free Tier": "Free", "28/1 Pro": "$7/month", "Teacher Pro": "$7/month",
    "Universal Pro": "$12/month", "Unlimited": "$18/month"
}

# Data consumption (simulated)
DAILY_SAVED_DATA_COST_MB = 0.5 # Small reduction for a longer demo
NEW_SAVE_COST_BASE_MB = 10.0 # Base cost for a new permanent save (10MB)

# Initial structure for databases
TEACHER_DB_INITIAL = {"units": [], "lessons": [], "vocab": [], "worksheets": [], "quizzes": [], "tests": []}
UTILITY_DB_INITIAL = {"saved_items": []} # Format: [{"name": "item_name", "content": "ai_output", "size_mb": 10, "category": "Productivity"}]
STORAGE_INITIAL = {
    "tier": "Free Tier", 
    "total_used_mb": 40.0,
    "utility_used_mb": 15.0, 
    "teacher_used_mb": 20.0,
    "general_used_mb": 5.0
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
    .stSidebar .stRadio > label {{
        font-size: 1.1em;
        font-weight: 500;
        color: #333333;
        margin-bottom: 8px;
        padding: 5px 10px;
        border-radius: 8px;
    }}
    .stSidebar .stRadio > label:hover {{
        color: #2D6BBE;
        background-color: #E0E4EB;
    }}
    /* Active sidebar item */
    .stSidebar .stRadio > label[data-baseweb="radio"] > div:first-child {{
        background-color: #2D6BBE;
        color: #FFFFFF !important;
        border-radius: 8px;
        padding: 10px 15px;
        margin: 5px 0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}
    .stSidebar .stRadio > label[data-baseweb="radio"] > div:first-child .stMarkdown p,
    .stSidebar .stRadio > label[data-baseweb="radio"] > div:first-child .stMarkdown h1,
    .stSidebar .stRadio > label[data-baseweb="radio"] > div:first-child .stMarkdown h2,
    .stSidebar .stRadio > label[data-baseweb="radio"] > div:first-child .stMarkdown h3,
    .stSidebar .stRadio > label[data-baseweb="radio"] > div:first-child .stMarkdown h4,
    .stSidebar .stRadio > label[data-baseweb="radio"] > div:first-child .stMarkdown h5,
    .stSidebar .stRadio > label[data-baseweb="radio"] > div:first-child .stMarkdown h6
    {{
         color: #FFFFFF !important;
    }}
    /* Sidebar header/title */
    .stSidebar h1 {{
        color: #333333;
        font-size: 1.8em;
        margin-left: 10px;
    }}
    .stSidebar img {{
        width: 40px;
        height: 40px;
        margin-right: 10px;
    }}

    /* Card-like containers (for the dashboard and general use) */
    .stContainer, [data-testid="stVerticalBlock"] > div > div:has([data-testid="stExpander"]), 
    div[data-testid="stColumn"] > div > div > [data-testid="stVerticalBlock"] > div > div:not([data-testid="stTextarea"]) 
    {{
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }}
    
    /* Specific styling for the columns/blocks to look like distinct cards */
    div[data-testid="stColumn"] > div:nth-child(1),
    div[data-testid="stVerticalBlock"] > div:nth-child(1) > div:nth-child(n) > div:nth-child(1) > div:has([data-testid="stVerticalBlock"]) > div:has([data-testid="stMarkdownContainer"])
    {{
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
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
    [data-testid="stMetricDelta"] {{
        color: #555555;
    }}

    /* Progress Bar (for storage) */
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

    /* Input Fields */
    .stTextInput>div>div>input, .stTextArea>div>div, .stSelectbox>div>div, .stTextInput>div, .stTextArea>div {{
        background-color: #F8F8F8;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        color: #333333;
        padding: 8px 12px;
    }}
    
    /* Specific styling for the custom dashboard navigation */
    .custom-nav-active {{
        background-color: #2D6BBE !important; 
        color: #FFFFFF !important; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.2) !important;
    }}
    .custom-nav-inactive {{
        background-color: transparent !important; 
        color: #333333 !important;
    }}
    .custom-nav-inactive:hover {{
        background-color: #F0F2F6 !important;
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
                # Simple type check to prevent data corruption
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

    if data['tier'] != 'Unlimited':
        # Apply small daily usage increase
        data['utility_used_mb'] += DAILY_SAVED_DATA_COST_MB * 0.4
        data['teacher_used_mb'] += DAILY_SAVED_DATA_COST_MB * 0.4
        data['general_used_mb'] += DAILY_SAVED_DATA_COST_MB * 0.2
        data['total_used_mb'] = data['utility_used_mb'] + data['teacher_used_mb'] + data['general_used_mb']
        
        # Ensure usage doesn't exceed the total universal limit on load
        current_limit = TIER_LIMITS[data['tier']]
        if data['tier'] in ["Free Tier", "Universal Pro"] and data['total_used_mb'] > current_limit:
            data['total_used_mb'] = current_limit
            # st.warning("Daily usage increment capped at tier limit.")
        
    return data

def save_storage_tracker(data):
    """Saves user tier and usage stats."""
    save_db_file(data, STORAGE_TRACKER_FILE)
    st.session_state['storage'] = data


def check_storage_limit(action_area: str):
    """Checks if the user can perform an action based on their tier and usage.
    Returns (can_proceed: bool, error_message: str, effective_limit_mb: float).
    """
    current_tier = st.session_state.storage['tier']
    
    if current_tier == "Unlimited":
        return True, None, float('inf')
        
    limit_for_tier = TIER_LIMITS[current_tier]
    effective_limit = limit_for_tier
    used_mb = 0.0

    if action_area == 'utility_save':
        used_mb = st.session_state.storage['utility_used_mb']
        if current_tier == '28/1 Pro': effective_limit = TIER_LIMITS['28/1 Pro']
        elif current_tier not in ['Universal Pro', '28/1 Pro']: effective_limit = TIER_LIMITS['Free Tier']
        
    elif action_area == 'teacher_save':
        used_mb = st.session_state.storage['teacher_used_mb']
        if current_tier == 'Teacher Pro': effective_limit = TIER_LIMITS['Teacher Pro']
        elif current_tier not in ['Universal Pro', 'Teacher Pro']: effective_limit = TIER_LIMITS['Free Tier']

    elif action_area == 'universal':
        used_mb = st.session_state.storage['total_used_mb']
        
    # Check if the next save would exceed the limit
    if used_mb + NEW_SAVE_COST_BASE_MB > effective_limit:
        return False, f"Storage limit reached ({used_mb:.2f}MB / {effective_limit}MB).", effective_limit
    
    return True, None, effective_limit


# --- INITIALIZATION BLOCK ---

if 'storage' not in st.session_state:
    st.session_state['storage'] = load_storage_tracker()
    
if 'teacher_db' not in st.session_state:
    st.session_state['teacher_db'] = load_db_file(TEACHER_DATA_FILE, TEACHER_DB_INITIAL)
    
if 'utility_db' not in st.session_state:
    st.session_state['utility_db'] = load_db_file(UTILITY_DATA_FILE, UTILITY_DB_INITIAL)

if 'app_mode' not in st.session_state:
    st.session_state['app_mode'] = "Usage Dashboard" 

# AI client and system instruction setup
try:
    client = genai.Client()
except Exception as e:
    st.error(f"❌ ERROR: Gemini Client initialization failed. Check API Key: {e}")

try:
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    # Use a basic default if the file is missing
    SYSTEM_INSTRUCTION = "You are a helpful and detailed assistant."


# --- CORE AI GENERATION FUNCTION (Live Integration) ---
def run_ai_generation(prompt_text: str, uploaded_file: BytesIO = None, max_tokens=1500, temp=0.5):
    """Runs the Gemini AI model with the provided prompt and optional image."""
    
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
    """Renders the main landing page, visually mimicking the provided image."""
    
    current_tier = st.session_state.storage['tier']
    total_used = st.session_state.storage['total_used_mb']
    limit = TIER_LIMITS[current_tier]
    
    # Hide the Streamlit main page title/header area for a cleaner look
    st.markdown("<h1 style='visibility: hidden; height: 0;'>Dashboard</h1>", unsafe_allow_html=True)

    # --- MAIN CONTENT AREA (Left side: Charts/Metrics) ---
    col_left, col_right = st.columns([0.75, 0.25])

    # --- LEFT COLUMN: FOUR CARDS (Visually Mapped to the Image) ---
    with col_left:
        # --- ROW 1: Monthly Metrics and Market Share ---
        row1_col1, row1_col2 = st.columns(2)
        
        with row1_col1:
            # Card 1: Monthly Performance Metrics (Line Chart Mock)
            with st.container(border=True):
                st.markdown("##### Monthly Performance Metrics")
                # Using an image or a styled div to mock the chart appearance
                st.markdown("""
                <div style="height: 150px; background-color: #FFFFFF; border-radius: 8px; 
                            display: flex; align-items: center; justify-content: center; 
                            color: #A0A0A0; font-size: 0.8em; border: 1px solid #F0F0F0; padding: 10px;">
                    
                </div>
                """, unsafe_allow_html=True)
        
        with row1_col2:
            # Card 2: Market Share (Doughnut Chart Mock)
            with st.container(border=True):
                st.markdown("##### Market Share")
                
                # --- CORRECTED DOUGHNUT CHART MOCK ---
                st.markdown(
                f"""
                <div style="display: flex; align-items: center; justify-content: space-around;">
                    <div style="font-size: 1.5em; font-weight: 600; color: #333333;">
                        81.8%<br><span style="font-size: 0.8em; color: #888888;">Expected Share</span>
                    </div>
                    
                    <div style="width: 100px; height: 100px; position: relative;">
                        <div style="width: 100%; height: 100%; border-radius: 50%; background: conic-gradient(
                            #2D6BBE 0% 87%, 
                            #E0E0E0 87% 100%
                        ); position: relative; display: flex; align-items: center; justify-content: center;">
                            <div style="width: 60%; height: 60%; border-radius: 50%; background: white; text-align: center; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #333;">
                                87%
                            </div>
                        </div>
                    </div>
                </div>
                """
                , unsafe_allow_html=True)
                # --- END OF CORRECTED DOUGHNUT CHART MOCK ---

        # --- ROW 2: Market Share Distribution and Uline SI Distribution ---
        row2_col1, row2_col2 = st.columns(2)
        
        with row2_col1:
            # Card 3: Market Share Distribution (Line Chart Mock)
            with st.container(border=True):
                st.markdown("##### Market Share Distribution")
                st.markdown("""
                <div style="height: 150px; background-color: #FFFFFF; border-radius: 8px; 
                            display: flex; align-items: center; justify-content: center; 
                            color: #A0A0A0; font-size: 0.8em; border: 1px solid #F0F0F0; padding: 10px;">
                    
                </div>
                """, unsafe_allow_html=True)
                
                # Nested row for Regional Sales (Mock Bar Chart)
                st.markdown("###### Regional Sales")
                st.markdown("""
                <div style="height: 50px; display: flex; align-items: flex-end; justify-content: space-around; padding: 0 10px;">
                    <div style="width: 10%; height: 60%; background-color: #2D6BBE; border-radius: 3px;"></div>
                    <div style="width: 10%; height: 30%; background-color: #2D6BBE; border-radius: 3px;"></div>
                    <div style="width: 10%; height: 80%; background-color: #2D6BBE; border-radius: 3px;"></div>
                    <div style="width: 10%; height: 20%; background-color: #2D6BBE; border-radius: 3px;"></div>
                    <div style="width: 10%; height: 90%; background-color: #2D6BBE; border-radius: 3px;"></div>
                    <div style="width: 10%; height: 45%; background-color: #2D6BBE; border-radius: 3px;"></div>
                </div>
                """, unsafe_allow_html=True)

        with row2_col2:
            # Card 4: Uline SI Distribution (Bar Chart Mock)
            with st.container(border=True):
                st.markdown("##### Uline SI Distribution")
                # Custom bar chart mock (simulating the blue color and structure)
                st.markdown("""
                <div style="height: 200px; display: flex; align-items: flex-end; justify-content: space-around; padding: 10px 0;">
                    <div style="width: 15%; height: 25%; background-color: #2D6BBE; border-radius: 3px;"></div>
                    <div style="width: 15%; height: 35%; background-color: #2D6BBE; border-radius: 3px;"></div>
                    <div style="width: 15%; height: 50%; background-color: #2D6BBE; border-radius: 3px;"></div>
                    <div style="width: 15%; height: 75%; background-color: #2D6BBE; border-radius: 3px;"></div>
                    <div style="width: 15%; height: 90%; background-color: #2D6BBE; border-radius: 3px;"></div>
                </div>
                """, unsafe_allow_html=True)


    # --- RIGHT COLUMN: NAVIGATION AND FILTERS (Visually Mapped to the Image) ---
    with col_right:
        # Card 5: Navigation (Dashboard)
        with st.container(border=True):
            st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 1.5em; color: #2D6BBE; margin-right: 10px; font-weight: 700;">A</span>
                    <span style="font-size: 1.2em; font-weight: 700; color: #333333;">ARTORIOUS</span>
                </div>
                <span style="font-size: 1.5em; color: #888888;">⋮</span>
            </div>
            """, unsafe_allow_html=True)
            
            # --- Custom Navigation Buttons ---
            def nav_button(label, icon, key):
                is_active = (label == 'Dashboard Overview')
                css_class = "custom-nav-active" if is_active else "custom-nav-inactive"
                
                st.markdown(f"""
                <div class="{css_class}" style="
                    padding: 10px 15px; 
                    margin: 5px 0; 
                    border-radius: 8px; 
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    font-weight: 500;
                    transition: all 0.2s;
                ">
                    <span style="margin-right: 15px; font-size: 1.1em;">{icon}</span>
                    {label}
                </div>
                """, unsafe_allow_html=True)

            # NOTE: These are visually styled mock buttons, not functional Streamlit buttons.
            nav_button("Dashboard Overview", "🏠", "nav_overview")
            nav_button("Dashboard", "🖥️", "nav_dash")
            nav_button("Data Input", "📝", "nav_input")
            nav_button("Historical Trends", "📈", "nav_trends")

        # Card 6: Filter Options
        with st.container(border=True):
            st.markdown("##### Filter Options")
            # Using st.toggle for the switch/toggle appearance
            st.toggle("Date Range", key="filter_date", value=True)
            st.toggle("Product Type", key="filter_product", value=False)
            st.toggle("Region", key="filter_region", value=True)
            st.toggle("Product Type", key="filter_product_2", value=False)
            st.toggle("Region", key="filter_region_2", value=False)
            
            # Simulated Slider
            st.slider("Region", 0, 100, 50, key="filter_slider")

def render_main_dashboard():
    """Renders the split-screen selection for Teacher Aid and 28/1 Utilities."""
    
    st.title("🖥️ Main Dashboard")
    st.caption("Access your two main application suites.")
    st.markdown("---")
    
    col_teacher, col_utility = st.columns(2)
    
    with col_teacher:
        st.header("🎓 Teacher Aid")
        st.markdown("Access curriculum planning tools, resource generation, and student management features.")
        if st.button("Launch Teacher Aid", key="launch_teacher_btn", use_container_width=True):
            st.session_state['app_mode'] = "Teacher Aid"
            st.rerun()

    with col_utility:
        st.header("💡 28/1 Utilities")
        st.markdown("Use 28 specialized AI tools for productivity, finance, health, and more.")
        if st.button("Launch 28/1 Utilities", key="launch_utility_btn", use_container_width=True):
            st.session_state['app_mode'] = "28/1 Utilities"
            st.rerun()

def render_utility_hub_navigated(can_interact):
    """Renders the utility hub with back button and internal navigation."""
    
    can_save, error_message, effective_limit = check_storage_limit('utility_save')

    col_back, col_title, col_save_data_btn_container = st.columns([0.15, 0.55, 0.3])
    
    if col_back.button("← Back", key="utility_back_btn"):
        st.session_state['app_mode'] = "Dashboard"
        st.session_state['utility_view'] = 'main'
        st.session_state.pop('utility_active_category', None)
        st.rerun()

    col_title.title("💡 28/1 Utilities")

    with col_save_data_btn_container:
        if st.button("💾 Saved Data", key="utility_saved_data_btn", use_container_width=True, disabled=not can_interact):
            st.session_state['utility_view'] = 'saved'
        elif 'utility_view' not in st.session_state:
             st.session_state['utility_view'] = 'main'

    st.markdown("---")

    if st.session_state.get('utility_view') == 'saved':
        st.header("💾 Saved 28/1 Utility Items")
        if not can_interact:
            st.error(f"🛑 {error_message} Cannot access saved items while over limit. Clean up data or upgrade plan.")
        elif not st.session_state.utility_db['saved_items']:
            st.info("No 28/1 utility items saved yet.")
        else:
            # Need to iterate over a copy or range to allow list modification (deletion)
            items_to_display = st.session_state.utility_db['saved_items']
            for i in range(len(items_to_display)):
                item = items_to_display[i]
                current_index = i 
                with st.expander(f"**{item.get('name', f'Saved Item #{i+1}')}** ({item.get('category', 'N/A')}) - {item.get('size_mb', 0):.1f}MB"):
                    st.code(item['content'], language='markdown')
                    
                    new_name = st.text_input("Edit Save Name:", value=item.get('name', ''), key=f"edit_util_name_{current_index}")
                    
                    if new_name != item.get('name', '') and st.button("Update Name", key=f"update_util_name_btn_{current_index}"):
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
        
    elif st.session_state.get('utility_view') == 'main':
        st.header("Select a Utility Category")
        
        with st.container(border=True):
            st.subheader("📚 Explanation & Guide")
            st.markdown("Each category contains specialized AI tools. Select a category to proceed to the features within it.")
            
        categories = list(CATEGORIES_FEATURES.keys())
        cols = st.columns(3)
        
        for i, category in enumerate(categories):
            with cols[i % 3]:
                if st.button(f"{CATEGORIES_FEATURES[category]['icon']} {category}", key=f"cat_btn_{i}", use_container_width=True):
                    st.session_state['utility_active_category'] = category
                    st.session_state['utility_view'] = 'category'
                    st.rerun()

    elif st.session_state.get('utility_view') == 'category' and 'utility_active_category' in st.session_state:
        st.markdown("---")
        active_category = st.session_state['utility_active_category']
        st.subheader(f"Features in: {active_category}")
        
        category_data = CATEGORIES_FEATURES[active_category]
        features = list(category_data["features"].keys())

        selected_feature = st.selectbox(
            "Choose a specific feature:",
            options=["Select a Feature to Use"] + features,
            key="hub_feature_select"
        )
        
        user_input = ""
        uploaded_file = None
        image_needed = (selected_feature == "9. Image-to-Calorie Estimate")
        
        if selected_feature != "Select a Feature to Use":
            
            if image_needed:
                st.warning("⚠️ **Image Required!** Please upload your meal photo below.")
                
            example_prompt = category_data["features"][selected_feature]
            st.info(f"💡 **Example Input Format:** `{example_prompt}`")

            if image_needed:
                uploaded_file = st.file_uploader(
                    "Upload Meal Photo (Feature 9 Only)",
                    type=["jpg", "jpeg", "png"],
                    key="calorie_image_upload_area",
                    disabled=not can_interact
                )
                if uploaded_file:
                    st.image(Image.open(uploaded_file), caption="Meal to Analyze", width=250)
                    
            user_input = st.text_area(
                "Enter your required data:",
                value="",
                placeholder=example_prompt,
                key="hub_text_input",
                disabled=not can_interact
            )

            if st.button(f"EXECUTE: {selected_feature}", key="hub_execute_btn", disabled=not can_interact):
                if image_needed and uploaded_file is None:
                    st.error("Please upload an image to run the Image-to-Calorie Estimate.")
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

                if st.button("💾 Save Output", key="save_hub_output_btn", disabled=not can_save):
                    save_size = calculate_mock_save_size(output_content)
                    
                    if can_save:
                        st.session_state.utility_db['saved_items'].append({
                            "name": f"{st.session_state.hub_last_feature_used}",
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
                        st.error(f"🛑 Cannot save: {error_message}")


def render_teacher_aid_navigated(can_interact):
    """Renders the teacher aid app with internal navigation sidebar."""
    
    can_save, error_message, effective_limit = check_storage_limit('teacher_save')

    st.title("🎓 Teacher Aid")
    st.caption("Curriculum manager and resource generator.")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎓 Teacher Aid Menu")
    
    teacher_mode = st.sidebar.radio(
        "Navigation:",
        options=["Resource Dashboard", "Saved Data", "Data Management"],
        key="teacher_nav_radio"
    )
    st.sidebar.markdown("---")

    if st.button("← Back to Main Dashboard", key="teacher_back_main_btn"):
        st.session_state['app_mode'] = "Dashboard"
        st.rerun()
        
    st.markdown("---")

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

        def generate_and_save_resource(tab_object, tab_name, ai_tag, db_key, ai_instruction_placeholder, can_save_flag, error_msg_flag, can_interact_flag):
            with tab_object:
                st.subheader(f"1. Generate {tab_name}")
                prompt = st.text_area(
                    f"Enter details for the {tab_name.lower()}:",
                    placeholder=ai_instruction_placeholder,
                    key=f"{db_key}_prompt",
                    height=150,
                    disabled=not can_interact_flag
                )
                if st.button(f"Generate {tab_name}", key=f"generate_{db_key}_btn", disabled=not can_interact_flag):
                    if prompt:
                        final_prompt = f"TEACHER'S AID RESOURCE TAG: {ai_tag}: {prompt}"
                        with st.spinner(f'Building {tab_name} using tag "{ai_tag}"...'):
                            result = run_ai_generation(final_prompt)
                            save_size = calculate_mock_save_size(result)

                            if can_save_flag:
                                st.session_state['teacher_db'][db_key].append({
                                    "name": f"{tab_name} from '{prompt[:20]}...'",
                                    "content": result,
                                    "size_mb": save_size
                                })
                                st.session_state.storage['teacher_used_mb'] += save_size
                                st.session_state.storage['total_used_mb'] += save_size
                                save_db_file(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                                save_storage_tracker(st.session_state.storage)
                                st.success(f"{tab_name} Generated and Saved Permanently! ({save_size:.1f}MB)")
                                st.rerun()
                            else:
                                st.error(f"🛑 Cannot save {tab_name}: {error_msg_flag}")
                    else:
                        st.warning("Please provide a prompt to generate.")

                st.markdown("---")
                st.subheader(f"Saved {tab_name}")
                
                if not can_interact_flag:
                    st.error(f"🛑 {error_msg_flag} Cannot access saved items while over limit.")
                elif st.session_state['teacher_db'][db_key]:
                    # Iterate over a list of indices to handle deletion
                    indices = list(range(len(st.session_state['teacher_db'][db_key])))
                    for i in reversed(indices):
                        resource_item = st.session_state['teacher_db'][db_key][i]
                        display_idx = i
                        expander_label = f"**{resource_item.get('name', f'{tab_name} #{display_idx+1}')}** - {resource_item.get('size_mb', 0):.1f}MB"
                        with st.expander(expander_label):
                            st.code(resource_item['content'], language='markdown')
                            
                            if st.button("🗑️ Delete This Save", key=f"delete_{db_key}_{display_idx}"):
                                deleted_size = st.session_state['teacher_db'][db_key][display_idx]['size_mb']
                                st.session_state.storage['teacher_used_mb'] = max(0, st.session_state.storage['teacher_used_mb'] - deleted_size)
                                st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - deleted_size)
                                st.session_state['teacher_db'][db_key].pop(display_idx)
                                save_db_file(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                                save_storage_tracker(st.session_state.storage)
                                st.toast(f"🗑️ {tab_name} deleted.")
                                st.rerun()
                else:
                    st.info(f"No {tab_name.lower()} saved yet.")

        for i, (name, data) in enumerate(RESOURCE_MAP.items()):
            generate_and_save_resource(tabs[i], name, data["tag"], data["key"], data["placeholder"], can_save, error_message, can_interact)

    elif teacher_mode == "Saved Data":
        st.header("Saved Resources Manager")
        st.info("View, edit, or delete all your generated Teacher Aid resources.")
        if not can_interact:
            st.error(f"🛑 {error_message} Cannot access saved items while over limit. Clean up data or upgrade plan.")
        else:
            for db_key, resources in st.session_state['teacher_db'].items():
                if resources:
                    st.subheader(f"📖 {db_key.replace('_', ' ').title()}")
                    # Iterate over a copy or range to allow list modification (deletion)
                    indices = list(range(len(resources)))
                    for i in indices:
                        resource_item = resources[i]
                        current_index = i
                        expander_label = f"**{resource_item.get('name', f'{db_key.title()} #{i+1}')}** - {resource_item.get('size_mb', 0):.1f}MB"
                        with st.expander(expander_label):
                            st.code(resource_item['content'], language='markdown')
                            
                            new_name = st.text_input("Edit Save Name:", value=resource_item.get('name', ''), key=f"edit_saved_teacher_name_{db_key}_{current_index}")
                            if new_name != resource_item.get('name', '') and st.button("Update Name", key=f"update_teacher_name_btn_{db_key}_{current_index}"):
                                st.session_state['teacher_db'][db_key][current_index]['name'] = new_name
                                save_db_file(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                                st.toast("Name updated!")
                                st.rerun()
                            
                            if st.button("🗑️ Delete This Save", key=f"delete_saved_teacher_{db_key}_{current_index}"):
                                deleted_size = st.session_state['teacher_db'][db_key][current_index]['size_mb']
                                st.session_state.storage['teacher_used_mb'] = max(0, st.session_state.storage['teacher_used_mb'] - deleted_size)
                                st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - deleted_size)
                                st.session_state['teacher_db'][db_key].pop(current_index)
                                save_db_file(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                                save_storage_tracker(st.session_state.storage)
                                st.toast("Resource deleted!")
                                st.rerun()
                
    elif teacher_mode == "Data Management":
        st.header("Data Management & Cleanup")
        
        if not can_interact:
            st.error(f"🛑 {error_message} Cannot access data management while over limit.")
        else:
            teacher_data_list = []
            for db_key, resources in st.session_state['teacher_db'].items():
                for i, resource in enumerate(resources):
                    teacher_data_list.append({
                        "name": resource.get('name', f"{db_key.title()} #{i+1}"),
                        "size_mb": resource.get('size_mb', 0),
                        "category": db_key,
                        "index": i
                    })
            
            teacher_data_list_sorted = sorted(teacher_data_list, key=lambda x: x['size_mb'], reverse=True)
            total_teacher_mb = sum(item['size_mb'] for item in teacher_data_list_sorted)

            st.metric("Total Teacher Aid Usage", f"{total_teacher_mb:.2f} MB")

            if teacher_data_list_sorted:
                st.subheader("All Teacher Aid Data Consumers")
                # Iterate over a copy to allow list modification (deletion)
                for i, item in enumerate(teacher_data_list_sorted):
                    col_item, col_size, col_delete = st.columns([0.6, 0.2, 0.2])
                    col_item.write(f"*{item['category'].title()}:* {item['name']}")
                    col_size.write(f"{item['size_mb']:.1f} MB")
                    # Use unique index for button and a random number to avoid key conflicts
                    if col_delete.button("Delete", key=f"clean_teacher_{item['category']}_{item['index']}_{i}"):
                        
                        # Find the true index in the original DB list before deletion
                        true_index = next((idx for idx, res in enumerate(st.session_state['teacher_db'][item['category']]) if res['name'] == item['name'] && res['size_mb'] == item['size_mb']), -1)
                        
                        if true_index != -1:
                            deleted_size = item['size_mb']
                            st.session_state.storage['teacher_used_mb'] = max(0, st.session_state.storage['teacher_used_mb'] - deleted_size)
                            st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - deleted_size)
                            st.session_state['teacher_db'][item['category']].pop(true_index)
                            save_db_file(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                            save_storage_tracker(st.session_state.storage)
                            st.toast(f"🗑️ Deleted {item['name']}!")
                            st.rerun()
                        else:
                            st.error("Error finding item for deletion.")
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
                
                benefits = []
                if tier == "Free Tier": benefits.append(f"**{TIER_LIMITS[tier]} MB** Universal Storage.")
                elif tier == "28/1 Pro": benefits.append(f"**3 GB** Dedicated 28/1 Storage (Free Tier elsewhere).")
                elif tier == "Teacher Pro": benefits.append(f"**3 GB** Dedicated Teacher Aid Storage (Free Tier elsewhere).")
                elif tier == "Universal Pro": benefits.append(f"**5 GB** Total for ALL tools combined.")
                elif tier == "Unlimited": benefits.append("Truly Unlimited Storage and Features!")
                
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
                        # --- MOCK PAYMENT INITIATION (Requires external service for LIVE payments) ---
                        st.warning(f"Initiating LIVE payment for {tier}... (Requires secure backend integration like Stripe)")
                        
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
    
    can_proceed, error_msg, _ = check_storage_limit('universal')
    
    st.subheader("Storage Utilization")
    total_used = st.session_state.storage['total_used_mb']
    limit = TIER_LIMITS[st.session
