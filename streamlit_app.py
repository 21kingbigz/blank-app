import streamlit as st
import os
import json
import math
import pandas as pd # Added for simple data tables/charts
import numpy as np # Added for mock data generation
from google import genai
from PIL import Image
from io import BytesIO
from google.generativeai.errors import APIError

# --- 0. CONFIGURATION AND PERSISTENCE FILE PATHS ---
WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash' # Or 'gemini-pro' for text-only, or 'gemini-1.5-flash'
# File names for permanent storage (Mocked for this script)
TEACHER_DATA_FILE = "teacher_data.json" # Stores generated teacher resources
UTILITY_DATA_FILE = "utility_data.json" # Stores saved 28/1 utility outputs
STORAGE_TRACKER_FILE = "storage_tracker.json" # Stores user tier and usage stats

# Tier Definitions and Storage Limits (in MB)
TIER_LIMITS = {
    "Free Tier": 500, # 500 MB total
    "28/1 Pro": 3000, # 3 GB dedicated for 28/1 utilities, general uses 500MB
    "Teacher Pro": 3000, # 3 GB dedicated for Teacher Aid, general uses 500MB
    "Universal Pro": 5000, # 5 GB total for everything combined
    "Unlimited": float('inf') # Infinite storage
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
NEW_SAVE_COST_MB = 10 # Data cost for a new permanent save (simulated: 10MB per save)
# In a real app, 'NEW_SAVE_COST_MB' would be dynamic based on AI output size.

# Initial structure for databases
TEACHER_DB_INITIAL = {"units": [], "lessons": [], "vocab": [], "worksheets": [], "quizzes": [], "tests": []}
UTILITY_DB_INITIAL = {"saved_items": []} # Format: [{"name": "item_name", "content": "ai_output", "size_mb": 10, "category": "Productivity"}]

# Initial storage state for a new user (or if storage_tracker.json is missing)
STORAGE_INITIAL = {
    "tier": "Free Tier",
    "total_used_mb": 40.0, # Start with some usage for demo
    "utility_used_mb": 15.0,
    "teacher_used_mb": 20.0,
    "general_used_mb": 5.0 # For data not categorized (e.g., chat history if implemented)
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
# This CSS attempts to match the visual style of the image you provided.
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
    .stSidebar .stRadio > label {{ /* For the main navigation radio buttons */
        font-size: 1.1em;
        font-weight: 500;
        color: #333333;
        margin-bottom: 8px; /* Space between items */
        padding: 5px 10px;
        border-radius: 8px;
    }}
    .stSidebar .stRadio > label:hover {{
        color: #2D6BBE; /* Darker blue on hover */
        background-color: #E0E4EB; /* Very light blue background on hover */
    }}
    /* Active sidebar item */
    .stSidebar .stRadio > label[data-baseweb="radio"] > div:first-child {{ /* This targets the radio button itself */
        background-color: #2D6BBE; /* Darker blue for active background */
        color: #FFFFFF !important; /* White text for active */
        border-radius: 8px;
        padding: 10px 15px; /* Adjust padding for visual appeal */
        margin: 5px 0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}
    /* Ensure text within the active radio button is white */
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
        margin-left: 10px; /* Align with other content */
    }}
    .stSidebar img {{ /* Adjust logo size */
        width: 40px;
        height: 40px;
        margin-right: 10px;
    }}

    /* Main Content Area Styling (cards, buttons, etc.) */
    
    /* Card-like containers (for graphs, lists, plan info) */
    .stContainer, [data-testid="stVerticalBlock"] > div > div:has([data-testid="stExpander"]) {{ /* Target expanders too */
        background-color: #FFFFFF; /* Cards should be white */
        border: 1px solid #E0E0E0; /* Light border */
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px; /* Space between cards */
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); /* Subtle shadow */
    }}
    
    /* Specific styling for the columns/blocks to look like distinct cards */
    div[data-testid="stColumn"] > div:nth-child(1),
    div[data-testid="stVerticalBlock"] > div:nth-child(1) > div:nth-child(n) > div:nth-child(1) > div:has([data-testid="stVerticalBlock"]) > div:has([data-testid="stMarkdownContainer"])
    {{
        background-color: #FFFFFF; /* Ensure nested blocks also have card background */
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px; /* Space between cards */
    }}


    /* Headings and Titles */
    h1, h2, h3, h4, h5, h6 {{
        color: #333333;
    }}
    p, li, span {{ /* General text color */
        color: #555555;
    }}

    /* Buttons (Primary/Darker Blue) */
    .stButton>button {{
        background-color: #2D6BBE; /* Darker blue */
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-weight: 600;
        transition: background-color 0.2s;
    }}
    .stButton>button:hover {{
        background-color: #255A9E; /* Even darker blue on hover */
        color: white;
    }}
    .stButton>button:disabled {{
        background-color: #A0A0A0; /* Gray for disabled buttons */
        cursor: not-allowed;
    }}

    /* Metrics (for storage display) */
    [data-testid="stMetric"] {{
        background-color: #F8F8F8; /* Light background for metrics */
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #EAEAEA;
    }}
    [data-testid="stMetricValue"] {{
        color: #2D6BBE; /* Darker blue for metric values */
    }}
    [data-testid="stMetricDelta"] {{
        color: #555555; /* Neutral for delta */
    }}

    /* Progress Bar (for storage) */
    .stProgress > div > div > div > div {{
        background-color: #2D6BBE; /* Darker blue for filled part */
    }}
    .stProgress > div > div > div {{
        background-color: #E0E0E0; /* Light gray for empty part */
        border-radius: 5px;
    }}

    /* Info/Warning/Error boxes */
    .stAlert {{
        border-radius: 8px;
        padding: 15px;
    }}
    .stAlert.stAlert_info {{
        background-color: #e0f2f7; /* Light blue info */
        color: #0d47a1;
        border-left: 5px solid #2196f3;
    }}
    .stAlert.stAlert_warning {{
        background-color: #fffde7; /* Light yellow warning */
        color: #f57f17;
        border-left: 5px solid #ffeb3b;
    }}
    .stAlert.stAlert_error {{
        background-color: #ffebee; /* Light red error */
        color: #c62828;
        border-left: 5px solid #ef5350;
    }}

    /* Custom tier label (top left of content area) */
    .tier-label {{
        color: #888888; /* Keep it subtle */
        background-color: transparent; /* No background */
        padding: 0;
        font-size: 0.9em;
        font-weight: 600;
        margin-bottom: 15px; /* Space from title */
        display: block; /* Ensure it takes its own line */
    }}
    /* Hide Streamlit footer and menu button */
    #MainMenu, footer {{visibility: hidden;}}

    /* Input Fields */
    .stTextInput>div>div>input, .stTextArea>div>div, .stSelectbox>div>div, .stTextInput>div, .stTextArea>div {{
        background-color: #F8F8F8; /* Light gray background for inputs */
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        color: #333333;
        padding: 8px 12px;
    }}
    .stTextInput>div>div>input:focus, .stTextArea>div>div:focus-within {{
        border-color: #2D6BBE; /* Highlight on focus */
        box-shadow: 0 0 0 1px #2D6BBE;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# --- PERSISTENCE & STORAGE FUNCTIONS (Simplified and Mocked for demo) ---
# --- IMPORTANT: In a real production app, these would interact with a secure database. ---

def load_db_mock(filename, initial_data):
    """Loads data from a JSON file (mock persistence)."""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, type(initial_data)) else initial_data
        except (json.JSONDecodeError, FileNotFoundError):
            st.warning(f"Error loading {filename}. Resetting to initial data.")
            return initial_data
    return initial_data

def save_db_mock(data, filename):
    """Saves data to a JSON file (mock persistence)."""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        st.toast(f"💾 Saved {filename.replace('_', ' ')} (Mocked)")
    except Exception as e:
        st.error(f"Error saving {filename}: {e}")

def load_storage_tracker():
    """Loads user tier and usage stats (MOCK)."""
    data = load_db_mock(STORAGE_TRACKER_FILE, STORAGE_INITIAL)

    # Simulate daily usage increase (ONLY for tiers that aren't unlimited)
    # This simulation is simplistic; in reality, you'd track last access date.
    if data['tier'] != 'Unlimited':
        data['total_used_mb'] += DAILY_SAVED_DATA_COST_MB * 0.1 # Small daily increase for demo
        data['utility_used_mb'] += DAILY_SAVED_DATA_COST_MB * 0.04
        data['teacher_used_mb'] += DAILY_SAVED_DATA_COST_MB * 0.04
        data['general_used_mb'] += DAILY_SAVED_DATA_COST_MB * 0.02
        data['total_used_mb'] = data['utility_used_mb'] + data['teacher_used_mb'] + data['general_used_mb']
        
        # Ensure total_used_mb doesn't exceed tier limit for "Free Tier" on load
        if data['tier'] == "Free Tier" and data['total_used_mb'] > TIER_LIMITS["Free Tier"]:
            data['total_used_mb'] = TIER_LIMITS["Free Tier"] # Cap it for free tier
            st.warning("Daily usage increment capped at Free Tier limit on load.")
        
    return data

def save_storage_tracker(data):
    """Saves user tier and usage stats (MOCK)."""
    save_db_mock(data, STORAGE_TRACKER_FILE)
    st.session_state['storage'] = data # Update session state immediately


def check_storage_limit(action_area: str):
    """Checks if the user can perform an action based on their tier and usage.
    Returns (can_proceed: bool, error_message: str, effective_limit_mb: float).
    """
    current_tier = st.session_state.storage['tier']
    limit_for_tier = TIER_LIMITS[current_tier]
    
    if current_tier == "Unlimited":
        return True, None, float('inf')
        
    effective_limit = limit_for_tier
    used_mb = 0.0

    if action_area == 'utility_save':
        used_mb = st.session_state.storage['utility_used_mb']
        if current_tier == '28/1 Pro':
            effective_limit = TIER_LIMITS['28/1 Pro']
        elif current_tier != 'Universal Pro': # Free or Teacher Pro using 28/1
            effective_limit = TIER_LIMITS['Free Tier'] # Falls back to Free Tier limit for this area
        
    elif action_area == 'teacher_save':
        used_mb = st.session_state.storage['teacher_used_mb']
        if current_tier == 'Teacher Pro':
            effective_limit = TIER_LIMITS['Teacher Pro']
        elif current_tier != 'Universal Pro': # Free or 28/1 Pro using Teacher Aid
            effective_limit = TIER_LIMITS['Free Tier'] # Falls back to Free Tier limit for this area

    elif action_area == 'general_save':
        used_mb = st.session_state.storage['general_used_mb']
        # General saves always use the overall tier limit (unless dedicated plan)
        if current_tier == '28/1 Pro' or current_tier == 'Teacher Pro':
             effective_limit = TIER_LIMITS['Free Tier'] # Dedicated plans only get free tier for general
        
    # For 'universal' checks (like typing, overall usage)
    elif action_area == 'universal':
        used_mb = st.session_state.storage['total_used_mb']
        # Effective limit is the tier's total limit
        
    if used_mb + NEW_SAVE_COST_MB > effective_limit:
        return False, f"Storage limit reached ({used_mb:.2f}MB / {effective_limit}MB).", effective_limit
    
    return True, None, effective_limit


# --- INITIALIZATION BLOCK ---

if 'storage' not in st.session_state:
    st.session_state['storage'] = load_storage_tracker()
    
if 'teacher_db' not in st.session_state:
    st.session_state['teacher_db'] = load_db_mock(TEACHER_DATA_FILE, TEACHER_DB_INITIAL)
    
if 'utility_db' not in st.session_state:
    st.session_state['utility_db'] = load_db_mock(UTILITY_DATA_FILE, UTILITY_DB_INITIAL)

# Use current mode to set the correct sidebar highlight
if 'app_mode' not in st.session_state:
    st.session_state['app_mode'] = "Usage Dashboard" # Default start page

# AI client and system instruction setup (as per your original code)
try:
    # NOTE: Ensure GEMINI_API_KEY environment variable is set
    client = genai.Client()
except Exception:
    st.error("❌ ERROR: Gemini Client initialization failed. Please ensure the API Key is correctly configured.")
    # st.stop() # Commented out for smoother demo if API key isn't set

try:
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    st.error("❌ ERROR: 'system_instruction.txt' not found. Please ensure the file is in the same directory.")
    # st.stop() # Commented out for smoother demo if file is missing

# --- CORE AI FUNCTION (Mocked for this file due to length/API key) ---
def run_ai_generation(prompt_text: str, uploaded_file: BytesIO = None, max_tokens=700, temp=0.0):
    """Mocks AI generation to return a placeholder result."""
    
    # In a real app, you'd use your actual genai.Client() call here
    # For demo purposes, we return a consistent mock response.
    mock_response = f"🌟 AI Generated Content for '{prompt_text[:50]}...' 🌟\n\nThis is a placeholder response for the AI model.\n\n"
    if "Calendar Creator" in prompt_text:
        mock_response += "📅 Your mock calendar:\n- 9am-10am: Mock Task 1\n- 10am-11am: Mock Task 2\n- 11am-12pm: Mock Task 3"
    elif "Image-to-Calorie Estimate" in prompt_text:
        mock_response += "🥗 Estimated calories: 450 kcal, Protein: 30g, Carbs: 40g, Fats: 20g (Mock)"
    elif "Unit Overview" in prompt_text:
        mock_response += "📚 Mock Unit Overview: Introduction to Renaissance Art. (Placeholder)"
    else:
        mock_response += "Further details would be provided here by the actual AI model."
        
    return mock_response

# --- CATEGORIES AND FEATURES (Unchanged from your original code) ---
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
    "📸 Health": {"icon": "🥗", "features": {
        "9. Image-to-Calorie Estimate": "Estimate the calories and macros for this meal.",
        "10. Recipe Improver": "Ingredients: Chicken breast, rice, soy sauce, broccoli.",
        "11. Symptom Clarifier": "Non-emergency symptoms: Headache and minor fatigue in the afternoon."
    }},
    "🗣️ Writing/Comm": {"icon": "✍️", "features": {
        "12. Tone Checker & Rewriter": "Draft: I need the report soon. Desired tone: Professional.",
        "13. Contextual Translator": "Translate: 'It was lit.' Context: Talking about a good concert.",
        "14. Metaphor Machine": "Topic: Artificial Intelligence.",
        "15. Email/Text Reply Generator": "Received: 'Meeting canceled at 3pm.' Response points: Acknowledge, ask to reschedule for tomorrow."
    }},
    "💡 Creative": {"icon": "🎭", "features": {
        "16. Idea Generator/Constraint Solver": "Idea type: App name. Constraint: Must contain 'Zen' and be for productivity.",
        "17. Random Fact Generator": "Category: Deep Sea Creatures.",
        "18. 'What If' Scenario Planner": "Hypothetical: Moving to a small town in Norway."
    }},
    "💻 Tech/Travel": {"icon": "✈️", "features": {
        "19. Concept Simplifier": "Complex topic: Quantum Entanglement. Analogy type: Food.",
        "20. Code Explainer": "Code snippet: 'def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)'",
        "21. Packing List Generator": "Trip: 5 days, cold city, business trip."
    }},
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

# Helper to calculate mock size for a save (can be improved)
def calculate_mock_save_size(content: str) -> float:
    return max(NEW_SAVE_COST_MB, len(content) / 1000) # Min 10MB or 1KB per char

# --- APPLICATION PAGE RENDERERS ---

def render_usage_dashboard():
    """Renders the main landing page with storage visualization and plan information."""
    
    current_tier = st.session_state.storage['tier']
    total_used = st.session_state.storage['total_used_mb']
    utility_used = st.session_state.storage['utility_used_mb']
    teacher_used = st.session_state.storage['teacher_used_mb']
    general_used = st.session_state.storage['general_used_mb']
    
    limit = TIER_LIMITS[current_tier]
    
    st.title("📊 Usage Dashboard")
    st.caption(f"Your current plan: **{current_tier}**")
    st.markdown("---")
    
    # --- TOP ROW: Storage Visuals ---
    col_pie, col_bar = st.columns(2)
    
    with col_pie:
        # Pie Chart: Storage Left vs. Used
        st.subheader("Storage Utilization")
        if current_tier != 'Unlimited':
            used_percent = min(100, (total_used / limit) * 100) if limit > 0 else 0
            
            st.metric(label="Total Storage Used", value=f"{total_used:.2f} MB", delta=f"{limit - total_used:.2f} MB Remaining")
            st.progress(used_percent / 100)
            st.markdown(f"**Limit:** {limit} MB")
        else:
            st.info("Storage is **Unlimited** for your current plan.")

    with col_bar:
        # Bar Chart: Where Storage is Used Most
        st.subheader("Usage Breakdown")
        breakdown_data = pd.DataFrame({
            "Category": ["28/1 Utilities", "Teacher Aid", "General Data"],
            "Usage (MB)": [utility_used, teacher_used, general_used]
        })
        st.bar_chart(breakdown_data.set_index("Category"))

    st.markdown("---")
    
    # --- BOTTOM ROW: Storage Cleanup & Plan Info ---
    col_list, col_plans = st.columns(2)
    
    with col_list:
        # List: Specific Items Taking Most Storage
        st.subheader("🗑️ Data Cleanup (Top Usage)")
        all_saved_items = st.session_state.utility_db['saved_items'] + [
            {"name": f"Teacher Resource #{i+1}", "size_mb": NEW_SAVE_COST_MB, "category": "Teacher Aid", "db_key": "units"} 
            for i in range(len(st.session_state.teacher_db["units"]))
        ] # Mock teacher items
        
        # Sort by size (descending)
        all_saved_items_sorted = sorted(all_saved_items, key=lambda x: x.get('size_mb', 0), reverse=True)
        
        if all_saved_items_sorted:
            for item in all_saved_items_sorted[:5]: # Show top 5
                col_item, col_size, col_delete = st.columns([0.6, 0.2, 0.2])
                col_item.write(f"*{item['category']}:* {item['name']}")
                col_size.write(f"{item['size_mb']:.1f} MB")
                
                # Mock delete functionality
                if col_delete.button("Delete", key=f"delete_{item['name']}_{np.random.rand()}"):
                    st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - item['size_mb'])
                    if item['category'] == "28/1 Utility":
                        st.session_state.utility_db['saved_items'] = [i for i in st.session_state.utility_db['saved_items'] if i['name'] != item['name']]
                        st.session_state.storage['utility_used_mb'] = max(0, st.session_state.storage['utility_used_mb'] - item['size_mb'])
                    elif item['category'] == "Teacher Aid":
                        # In a real app, you'd specifically find and remove this item from teacher_db
                        st.session_state.storage['teacher_used_mb'] = max(0, st.session_state.storage['teacher_used_mb'] - item['size_mb'])
                    
                    save_storage_tracker(st.session_state.storage)
                    st.toast(f"🗑️ Deleted {item['name']} (Simulated).")
                    st.rerun()
        else:
            st.info("No saved data found.")

    with col_plans:
        # Bubbles: Explain Each Plan
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

def render_utility_hub_navigated():
    """Renders the utility hub with back button and internal navigation."""
    
    can_save, error_message, effective_limit = check_storage_limit('utility_save')

    col_back, col_title, col_save_data_btn_container = st.columns([0.15, 0.55, 0.3])
    
    if col_back.button("← Back", key="utility_back_btn"):
        st.session_state['app_mode'] = "Dashboard"
        st.session_state['utility_view'] = 'main' # Reset internal view
        st.session_state.pop('utility_active_category', None)
        st.rerun()

    col_title.title("💡 28/1 Utilities")

    with col_save_data_btn_container:
        if st.button("💾 Saved Data", key="utility_saved_data_btn", use_container_width=True, disabled= not can_save):
            st.session_state['utility_view'] = 'saved'
        elif 'utility_view' not in st.session_state:
             st.session_state['utility_view'] = 'main'

    st.markdown("---")

    if st.session_state.get('utility_view') == 'saved':
        st.header("💾 Saved 28/1 Utility Items")
        st.info("Here you can see, edit, and delete all your permanent 28/1 utility saves.")
        
        if not can_save:
            st.error(f"🛑 {error_message} Cannot access saved items while over limit. Clean up data or upgrade plan.")
        elif not st.session_state.utility_db['saved_items']:
            st.info("No 28/1 utility items saved yet.")
        else:
            for i, item in enumerate(st.session_state.utility_db['saved_items']):
                with st.expander(f"**{item.get('name', f'Saved Item #{i+1}')}** ({item.get('category', 'N/A')}) - {item.get('size_mb', 0):.1f}MB"):
                    st.code(item['content'], language='markdown')
                    new_name = st.text_input("Edit Save Name:", value=item.get('name', ''), key=f"edit_util_name_{i}")
                    if new_name != item.get('name', ''):
                        st.session_state.utility_db['saved_items'][i]['name'] = new_name
                        save_db_mock(st.session_state.utility_db, UTILITY_DATA_FILE)
                        st.toast("Name updated!")
                    
                    if st.button("🗑️ Delete This Save", key=f"delete_util_item_{i}"):
                        st.session_state.storage['utility_used_mb'] = max(0, st.session_state.storage['utility_used_mb'] - item['size_mb'])
                        st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - item['size_mb'])
                        st.session_state.utility_db['saved_items'].pop(i)
                        save_db_mock(st.session_state.utility_db, UTILITY_DATA_FILE)
                        save_storage_tracker(st.session_state.storage)
                        st.toast("Item deleted!")
                        st.rerun()
        
    elif st.session_state.get('utility_view') == 'main':
        st.header("Select a Utility Category")
        
        # Display the explanation box
        with st.container(border=True):
            st.subheader("📚 Explanation & Guide")
            st.markdown("Each category contains specialized AI tools. Select a category to proceed to the features within it.")
            
        # The 7 Category boxes (Grid format)
        categories = list(CATEGORIES_FEATURES.keys())
        cols = st.columns(3) # 3 columns for 7 categories, will wrap
        
        for i, category in enumerate(categories):
            with cols[i % 3]:
                if st.button(f"{CATEGORIES_FEATURES[category]['icon']} {category}", key=f"cat_btn_{i}", use_container_width=True):
                    st.session_state['utility_active_category'] = category
                    st.session_state['utility_view'] = 'category' # Switch to feature list view
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
        
        # --- INPUT AREA (Re-integrated from original 28/1 Hub logic) ---
        user_input = ""
        uploaded_file = None
        image_needed = (selected_feature == "9. Image-to-Calorie Estimate")
        
        if selected_feature != "Select a Feature to Use":
            feature_code = selected_feature.split(".")[0]
            
            if image_needed:
                st.warning("⚠️ **Image Required!** Please upload your meal photo below.")
                
            example_prompt = category_data["features"][selected_feature]
            st.info(f"💡 **Example Input Format:** `{example_prompt}`")

            if image_needed:
                uploaded_file = st.file_uploader(
                    "Upload Meal Photo (Feature 9 Only)",
                    type=["jpg", "jpeg", "png"],
                    key="calorie_image_upload_area"
                )
                if uploaded_file:
                    st.image(Image.open(uploaded_file), caption="Meal to Analyze", width=250)
                    
            user_input = st.text_area(
                "Enter your required data:",
                value="" if not image_needed else "Estimate the calories and macros for this meal.",
                placeholder=example_prompt,
                key="hub_text_input",
                disabled=not can_save # Disable typing if over limit
            )

            if st.button(f"EXECUTE: {selected_feature}", key="hub_execute_btn", disabled=not can_save):
                if image_needed and uploaded_file is None:
                    st.error("Please upload an image to run the Image-to-Calorie Estimate.")
                else:
                    final_prompt = f"UTILITY HUB: {selected_feature}: {user_input}"
                    with st.spinner(f'🎯 Routing request to **{selected_feature}**...'):
                        result = run_ai_generation(final_prompt, uploaded_file) # Using mock AI
                        st.session_state['hub_result'] = result
                        st.session_state['hub_last_feature_used'] = selected_feature
            
            st.markdown("---")
            st.subheader("Hub Output")

            if 'hub_result' in st.session_state:
                st.markdown(f"##### Result for: **{st.session_state.hub_last_feature_used}**")
                output_content = st.session_state['hub_result']
                st.code(output_content, language='markdown')

                if st.button("💾 Save Output", key="save_hub_output_btn", disabled=not can_save):
                    save_size = calculate_mock_save_size(output_content)
                    if can_save: # Re-check before saving
                        st.session_state.utility_db['saved_items'].append({
                            "name": f"{st.session_state.hub_last_feature_used} ({active_category})",
                            "content": output_content,
                            "size_mb": save_size,
                            "category": "28/1 Utility"
                        })
                        st.session_state.storage['utility_used_mb'] += save_size
                        st.session_state.storage['total_used_mb'] += save_size
                        save_db_mock(st.session_state.utility_db, UTILITY_DATA_FILE)
                        save_storage_tracker(st.session_state.storage)
                        st.toast(f"Saved {st.session_state.hub_last_feature_used} ({save_size:.1f}MB)!")
                    else:
                        st.error(f"🛑 Cannot save: {error_message}")


def render_teacher_aid_navigated():
    """Renders the teacher aid app with internal navigation sidebar."""
    
    can_save, error_message, effective_limit = check_storage_limit('teacher_save')

    st.title("🎓 Teacher Aid")
    st.caption("Curriculum manager and resource generator.")
    
    # Internal Sidebar Navigation
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎓 Teacher Aid Menu")
    
    teacher_mode = st.sidebar.radio(
        "Navigation:",
        options=["Resource Dashboard", "Saved Data", "Data Management"],
        key="teacher_nav_radio"
    )
    st.sidebar.markdown("---")

    # Back button to the main dashboard
    if st.button("← Back to Main Dashboard", key="teacher_back_main_btn"):
        st.session_state['app_mode'] = "Dashboard"
        st.rerun()
        
    st.markdown("---")

    if teacher_mode == "Resource Dashboard":
        st.header("Resource Generation Dashboard")
        st.info("Generate new units, lessons, quizzes, and more. All resources are saved permanently.")
        
        RESOURCE_MAP = {
            "Unit Overview": "Unit Overview", "Lesson Plan": "Lesson Plan",
            "Vocabulary List": "Vocabulary List", "Worksheet": "Worksheet",
            "Quiz": "Quiz", "Test": "Test"
        }
        
        tab_titles = list(RESOURCE_MAP.keys())
        tabs = st.tabs(tab_titles)

        # Helper Function for generating and saving resources (adapted from your original code)
        def generate_and_save_resource(tab_object, tab_name, ai_tag, db_key, ai_instruction_placeholder, can_save_flag, error_msg_flag):
            with tab_object:
                st.subheader(f"1. Generate {tab_name}")
                prompt = st.text_area(
                    f"Enter details for the {tab_name.lower()}:",
                    placeholder=f"E.g., '{ai_instruction_placeholder}'",
                    key=f"{db_key}_prompt",
                    height=150,
                    disabled=not can_save_flag # Disable typing if over limit
                )
                if st.button(f"Generate {tab_name}", key=f"generate_{db_key}_btn", disabled=not can_save_flag):
                    if prompt:
                        final_prompt = f"TEACHER'S AID RESOURCE TAG: {ai_tag}: {prompt}"
                        with st.spinner(f'Building {tab_name} using tag "{ai_tag}"...'):
                            result = run_ai_generation(final_prompt) # Using mock AI
                            save_size = calculate_mock_save_size(result)

                            if can_save_flag:
                                st.session_state['teacher_db'][db_key].append({
                                    "name": f"{tab_name} generated from '{prompt[:30]}...'",
                                    "content": result,
                                    "size_mb": save_size
                                })
                                st.session_state.storage['teacher_used_mb'] += save_size
                                st.session_state.storage['total_used_mb'] += save_size
                                save_db_mock(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                                save_storage_tracker(st.session_state.storage)
                                st.success(f"{tab_name} Generated and Saved Permanently! ({save_size:.1f}MB)")
                                st.rerun() # Rerun to update saved list
                            else:
                                st.error(f"🛑 Cannot save {tab_name}: {error_msg_flag}")
                    else:
                        st.warning("Please provide a prompt to generate.")

                st.markdown("---")
                st.subheader(f"Saved {tab_name}")
                
                if not can_save_flag:
                    st.error(f"🛑 {error_msg_flag} Cannot access saved items while over limit. Clean up data or upgrade plan.")
                elif st.session_state['teacher_db'][db_key]:
                    for i, resource_item in enumerate(reversed(st.session_state['teacher_db'][db_key])): # Show most recent first
                        display_idx = len(st.session_state['teacher_db'][db_key]) - 1 - i
                        expander_label = f"**{resource_item.get('name', f'{tab_name} #{display_idx+1}')}** - {resource_item.get('size_mb', 0):.1f}MB"
                        with st.expander(expander_label):
                            st.code(resource_item['content'], language='markdown')
                            new_name = st.text_input("Edit Save Name:", value=resource_item.get('name', ''), key=f"edit_teacher_name_{db_key}_{display_idx}")
                            if new_name != resource_item.get('name', ''):
                                st.session_state['teacher_db'][db_key][display_idx]['name'] = new_name
                                save_db_mock(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                                st.toast("Name updated!")

                            if st.button("🗑️ Delete This Save", key=f"delete_{db_key}_{display_idx}"):
                                st.session_state.storage['teacher_used_mb'] = max(0, st.session_state.storage['teacher_used_mb'] - resource_item['size_mb'])
                                st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - resource_item['size_mb'])
                                st.session_state['teacher_db'][db_key].pop(display_idx)
                                save_db_mock(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                                save_storage_tracker(st.session_state.storage)
                                st.toast(f"🗑️ {tab_name} deleted.")
                                st.rerun()
                else:
                    st.info(f"No {tab_name.lower()} saved yet.")

        # Apply the helper function to all tabs
        generate_and_save_resource(tabs[0], "Unit Overview", RESOURCE_MAP["Unit Overview"], "units", "Generate a detailed unit plan for a 10th-grade World History class on the Renaissance.", can_save, error_message)
        generate_and_save_resource(tabs[1], "Lesson Plan", RESOURCE_MAP["Lesson Plan"], "lessons", "Create a 45-minute lesson plan on Newton's First Law of Motion for 9th-grade science.", can_save, error_message)
        generate_and_save_resource(tabs[2], "Vocabulary List", RESOURCE_MAP["Vocabulary List"], "vocab", "Generate 10 vocabulary words for a 5th-grade math lesson on fractions.", can_save, error_message)
        generate_and_save_resource(tabs[3], "Worksheet", RESOURCE_MAP["Worksheet"], "worksheets", "Create a 10-question worksheet on subject-verb agreement for 7th-grade English.", can_save, error_message)
        generate_and_save_resource(tabs[4], "Quiz", RESOURCE_MAP["Quiz"], "quizzes", "Generate a 5-question multiple-choice quiz on the causes of the American Civil War.", can_save, error_message)
        generate_and_save_resource(tabs[5], "Test", RESOURCE_MAP["Test"], "tests", "Design a comprehensive end-of-unit test for a high school economics class on supply and demand.", can_save, error_message)

    elif teacher_mode == "Saved Data":
        st.header("Saved Resources Manager")
        st.info("View, edit, or delete all your generated Teacher Aid resources.")
        if not can_save:
            st.error(f"🛑 {error_message} Cannot access saved items while over limit. Clean up data or upgrade plan.")
        else:
            # Display all teacher resources in a categorized way, similar to the tab display but without generation forms
            for db_key, resources in st.session_state['teacher_db'].items():
                if resources:
                    st.subheader(f"📖 {db_key.replace('_', ' ').title()}")
                    for i, resource_item in enumerate(resources):
                        expander_label = f"**{resource_item.get('name', f'{db_key.title()} #{i+1}')}** - {resource_item.get('size_mb', 0):.1f}MB"
                        with st.expander(expander_label):
                            st.code(resource_item['content'], language='markdown')
                            new_name = st.text_input("Edit Save Name:", value=resource_item.get('name', ''), key=f"edit_saved_teacher_name_{db_key}_{i}")
                            if new_name != resource_item.get('name', ''):
                                st.session_state['teacher_db'][db_key][i]['name'] = new_name
                                save_db_mock(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                                st.toast("Name updated!")
                            if st.button("🗑️ Delete This Save", key=f"delete_saved_teacher_{db_key}_{i}"):
                                st.session_state.storage['teacher_used_mb'] = max(0, st.session_state.storage['teacher_used_mb'] - resource_item['size_mb'])
                                st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - resource_item['size_mb'])
                                st.session_state['teacher_db'][db_key].pop(i)
                                save_db_mock(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                                save_storage_tracker(st.session_state.storage)
                                st.toast("Resource deleted!")
                                st.rerun()
                
    elif teacher_mode == "Data Management":
        st.header("Data Management & Cleanup")
        st.info("This screen helps you manage what is taking up the most data within your Teacher Aid section.")
        if not can_save:
            st.error(f"🛑 {error_message} Cannot access data management while over limit. Clean up data or upgrade plan.")
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

            if teacher_data_list_sorted:
                st.subheader("Top Teacher Aid Data Consumers")
                for item in teacher_data_list_sorted[:10]: # Show top 10
                    col_item, col_size, col_delete = st.columns([0.6, 0.2, 0.2])
                    col_item.write(f"*{item['category'].title()}:* {item['name']}")
                    col_size.write(f"{item['size_mb']:.1f} MB")
                    if col_delete.button("Delete", key=f"clean_teacher_{item['category']}_{item['index']}_{np.random.rand()}"):
                        st.session_state.storage['teacher_used_mb'] = max(0, st.session_state.storage['teacher_used_mb'] - item['size_mb'])
                        st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - item['size_mb'])
                        st.session_state['teacher_db'][item['category']].pop(item['index']) # Remove from specific list
                        save_db_mock(st.session_state['teacher_db'], TEACHER_DATA_FILE)
                        save_storage_tracker(st.session_state.storage)
                        st.toast(f"🗑️ Deleted {item['name']}!")
                        st.rerun()
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
            with st.container(border=True): # Wrap each plan in a container for card-like appearance
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

                # Action button
                if tier == st.session_state.storage['tier']:
                    st.button("Current Plan", disabled=True, key=f"plan_current_{i}", use_container_width=True)
                    if tier != "Free Tier" and st.button("Cancel Plan", key=f"plan_cancel_{i}", use_container_width=True):
                        # MOCK: In a real app, this would involve API calls to your payment provider to cancel recurring payments
                        st.session_state.storage['tier'] = "Free Tier"
                        save_storage_tracker(st.session_state.storage)
                        st.toast("🚫 Plan cancelled. Downgraded to Free Tier.")
                        st.rerun()
                else:
                    if st.button(f"Upgrade to {tier}", key=f"plan_upgrade_{i}", use_container_width=True):
                        # --- MOCK PAYMENT INITIATION ---
                        st.info(f"Initiating upgrade to {tier}... (In a real app, this redirects to a secure payment page)")
                        
                        # In a real application, you would:
                        # 1. Call your secure backend server.
                        # 2. Your backend server would interact with Stripe/PayPal to create a checkout session.
                        # 3. The backend returns a redirect URL (e.g., Stripe Checkout URL).
                        # 4. Streamlit opens that URL in a new tab.
                        
                        # Example: Redirect to a mock payment page or an external service endpoint
                        mock_payment_url = f"https://mock-payment-gateway.com/checkout?plan={tier.replace(' ', '-')}&price={TIER_PRICES[tier]}"
                        
                        # This line attempts to open a new tab. Streamlit blocks pop-ups,
                        # so users might need to explicitly allow them or copy the link.
                        st.markdown(f'<script>window.open("{mock_payment_url}", "_blank");</script>', unsafe_allow_html=True)
                        
                        st.warning(f"Please complete the payment for **{tier}** in the new browser tab that just opened.")
                        st.info("After successful payment, your tier will be automatically updated on your next visit or refresh.")
                        
                        # For DEMO ONLY: Simulate immediate upgrade after "payment initiation"
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
    if not can_proceed:
        st.error(f"🛑 {error_msg} Cannot access detailed cleanup options while over limit. Consider quick deletes from Usage Dashboard or upgrading.")
        return # Stop rendering further if over limit

    st.subheader("Automated Suggestions")
    
    # Mock suggestions (in a real app, these would be dynamic)
    suggestions = [
        {"desc": "5 items saved over 6 months ago (35.2 MB)", "items": []}, # Populate with actual items for action
        {"desc": "3 largest items (182.1 MB)", "items": []},
        {"desc": "12 items not accessed in the last 90 days (50.5 MB)", "items": []}
    ]

    for i, suggestion in enumerate(suggestions):
        st.write(f"{i+1}. {suggestion['desc']}")
        if st.button(f"Review and Delete Suggested Items ({i+1})", key=f"review_cleanup_btn_{i}", use_container_width=True):
            st.info(f"Redirecting to detailed review for: {suggestion['desc']} (Mocked).")
            # In a real app, this would show a list of actual items to delete.
            # For demo, we'll just simulate a deletion
            mock_deleted_size = np.random.uniform(5, 50) # Simulate deleting some data
            st.session_state.storage['total_used_mb'] = max(0, st.session_state.storage['total_used_mb'] - mock_deleted_size)
            save_storage_tracker(st.session_state.storage)
            st.toast(f"🧹 Successfully cleaned up {mock_deleted_size:.1f}MB of data (Simulated)!")
            st.rerun()

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
    
    # Set the index for the radio button to ensure the correct item is highlighted
    try:
        current_index = menu_options.index(st.session_state.get('app_mode', 'Usage Dashboard'))
    except ValueError:
        current_index = 0 # Default to Usage Dashboard if app_mode is unknown/nested

    mode_selection = st.radio(
        "Application Menu:",
        options=menu_options,
        index=current_index,
        key="main_mode_select"
    )
    
    # Update app_mode in session state if user clicks a new item in the sidebar
    if mode_selection != st.session_state.get('app_mode', 'Usage Dashboard'):
        st.session_state['app_mode'] = mode_selection
        st.session_state.pop('utility_view', None) # Reset nested views on main navigation change
        st.session_state.pop('utility_active_category', None)
        st.rerun() # Rerun to properly switch view


# --- GLOBAL TIER RESTRICTION CHECK (Runs on every page load) ---
universal_limit_reached, universal_error_msg, _ = check_storage_limit('universal')

# If universal limit is reached, disable typing/saving/copying functionality
# This flag will be passed to input fields and buttons.
can_interact = not universal_limit_reached

if not can_interact:
    st.error(f"🛑 **STORAGE LIMIT REACHED:** {universal_error_msg}. You cannot generate new data, save, type, or copy any existing data until you upgrade your plan or clean up storage.")
    
    # Redirect users to a management page if they're stuck in a content generation page
    if st.session_state['app_mode'] not in ["Usage Dashboard", "Plan Manager", "Data Clean Up"]:
        st.session_state['app_mode'] = "Usage Dashboard"
        st.rerun() # Force a re-render to the management page


# --- RENDERER DISPATCHER ---
# The tier label is rendered by the CSS, but its content depends on session state
# Each rendering function is responsible for displaying the main content for its page.

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
