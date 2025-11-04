import streamlit as st
import os
from google import genai
from PIL import Image
from io import BytesIO
from google.genai.errors import APIError

# --- CONFIGURATION AND PERSISTENCE ---
WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash' 
# Key for session state persistence
SCHEDULE_KEY = "last_schedule_data" 
# Mock Database structure for Teacher's Aid resources
TEACHER_DB = {"units": [], "lessons": [], "vocab": [], "worksheets": [], "quizzes": [], "tests": []}

# Set browser tab title, favicon, and layout. 
st.set_page_config(
    page_title=f"{WEBSITE_TITLE} - Dual Mode", 
    page_icon="👑", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CACHED MOCK PERSISTENCE FUNCTIONS ---
@st.cache_data
def load_last_schedule():
    """Loads the last schedule from session state."""
    return st.session_state.get(SCHEDULE_KEY, None) 

def save_last_schedule(schedule_text: str):
    """Saves the latest schedule to session state."""
    st.session_state[SCHEDULE_KEY] = schedule_text

# Load instruction and initialize client
try:
    # NOTE: You must ensure your environment has the GEMINI_API_KEY environment variable set for this to work.
    client = genai.Client()
except Exception:
    st.error("❌ ERROR: Gemini Client initialization failed. Please ensure the API Key is correctly configured.")
    st.stop()
    
# --- CRITICAL: LOAD SYSTEM INSTRUCTION FROM SEPARATE FILE ---
try:
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    st.error("❌ ERROR: 'system_instruction.txt' not found. Please ensure the file is in the same directory.")
    st.stop()
# --- END SYSTEM INSTRUCTION LOAD ---


# --- CRITICAL CSS FIX FOR DROPDOWN AND THEME ---
st.markdown(
    """
    <style>
    /* 1. Base App Background and General Text */
    .stApp {
        background-color: #0A0A0A; /* Deep Black */
        color: #FFFFFF; 
    }
    
    /* 2. Secondary Background (Sidebar, Input Widgets) */
    .css-1d391kg, .css-1dp5fjs, section[data-testid='stSidebar'] {
        background-color: #121212; 
        border-right: 1px solid #333333;
    }

    /* **SIDEBAR TEXT (Full White Enforcement)** */
    section[data-testid='stSidebar'] * { 
        color: #FFFFFF !important; 
    }
    
    /* 3. Button/Accent Color & Smoothness */
    .stButton>button {
        color: #FFFFFF;
        background-color: #333333; 
        border-radius: 8px; 
        padding: 10px 20px;
        font-weight: bold;
        border: 1px solid #555555;
        transition: all 0.2s ease-in-out; 
    }
    
    .stButton>button:hover {
        background-color: #555555; 
        border-color: #777777;
    }

    /* 4. INPUT FIELD STYLING (Main box) */
    .stTextInput>div>div>input, .stTextArea>div>div, .stSelectbox>div>div {
        background-color: #212121; 
        color: #FFFFFF !important; 
        border: 1px solid #444444;
        border-radius: 6px; 
    }
    
    /* --- CRITICAL DROPDOWN FIXES --- */
    
    /* Target the floating menu container (the box around all options) */
    div[data-baseweb="menu"] {
        background-color: #1A1A1A !important; 
        border: 1px solid #FFFFFF !important; /* WHITE OUTLINE for the whole menu */
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5); 
    }
    
    /* 🔥 FORCING DARK BACKGROUND (Level 1: Menu Items/Options) */
    [data-baseweb="menu-item"],
    div[role="option"] { 
        background-color: #212121 !important; /* Force Dark Grey */
        color: #FFFFFF !important;
        border-color: #212121 !important; 
    }
    
    /* 🔥 FORCING DARK BACKGROUND (Level 2: Nested elements inside options) */
    [data-baseweb="menu-item"] *,
    div[role="option"] * {
        background-color: #212121 !important; /* Force Dark Grey on all children */
        color: #FFFFFF !important;
    }
    
    /* HOVER/FOCUS STATE FIX: Solid dark grey on hover (maintains contrast) */
    [data-baseweb="menu-item"]:focus, 
    [data-baseweb="menu-item"]:active,
    [data-baseweb="menu-item"]:hover {
        background-color: #333333 !important; /* Slightly darker grey on hover */
        color: #FFFFFF !important;
    }

    /* Additional targets to cover all base layers */
    .st-bw-list-box, 
    div[role="listbox"],
    ul[role="menu"] { 
        background-color: #1A1A1A !important; 
    }
    
    /* --- END CRITICAL DROPDOWN FIXES --- */

    /* 7. AI RESPONSE BOX STYLING */
    div.stCode {
        background-color: #1A1A1A !important; 
        border-radius: 12px; 
        padding: 15px; 
    }
    div.stCode pre {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
    }

    /* 9. General text and label text */
    p, li, a, span, .stApp label { 
        color: #FFFFFF !important; 
    }
    
    /* 10. MANUAL ACCENT COLOR CHANGE (Blue links) */
    a {
        color: #00BFFF !important; 
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 1. CORE AI FUNCTION (Handles both modes) ---

def run_ai_generation(prompt_text: str, uploaded_file: BytesIO = None, max_tokens=700, temp=0.0):
    """Handles generation for both the Hub and Teacher's Aid."""
    parts = []
    
    if uploaded_file is not None:
        try:
            uploaded_file.seek(0) 
            image = Image.open(uploaded_file)
            parts.append(image)
        except Exception as e:
            return f"ERROR loading image: {e}"

    parts.append(prompt_text)

    # API Call with System Instruction loaded from file
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=parts,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION, 
                temperature=temp, 
                max_output_tokens=max_tokens
            )
        )
        return response.text
    except APIError as e:
        return f"An API Error occurred: 503 UNAVAILABLE. The model is overloaded. Please retry. Full error: {e}"
    except Exception as e:
        return f"An unknown API Error occurred: {e}"


# --- 2. FEATURE LIST FOR UTILITY HUB (28 Features) ---
CATEGORIES_FEATURES = {
    "🧠 Productivity": {"icon": "💡", "features": { 
        "1. Daily Schedule Optimizer": "tasks: write report, call client. Time: 9am-12pm.",
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

# --- 3. UTILITY HUB MODE FUNCTION ---
def render_utility_hub():
    """Renders the single-page 28-in-1 application."""
    st.title(f"👑 {WEBSITE_TITLE}: 28-in-1 Smart Utility Hub")
    st.caption("Select a category from the sidebar to begin using a stateless utility.")

    # Sidebar for category selection
    st.sidebar.header("Hub Categories")
    category_titles = list(CATEGORIES_FEATURES.keys())
    selected_category = st.sidebar.radio("Choose a Domain:", category_titles, index=0, key="hub_category_radio")

    # Get features for the selected category
    category_data = CATEGORIES_FEATURES[selected_category]
    features = list(category_data["features"].keys())

    st.header(f"{category_data['icon']} {selected_category}")

    # Feature Dropdown (Select Box)
    selected_feature = st.selectbox(
        "Choose a specific feature:",
        options=["Select a Feature to Use"] + features,
        key="hub_feature_select"
    )

    # --- INPUT AREA ---
    user_input = ""
    uploaded_file = None
    image_needed = (selected_feature == "9. Image-to-Calorie Estimate")
    is_schedule_optimizer = (selected_feature == "1. Daily Schedule Optimizer")

    if selected_feature != "Select a Feature to Use":
        feature_code = selected_feature.split(".")[0]
        col1, col2 = st.columns([0.7, 0.3])
        
        with col1:
            st.markdown(f"##### Step 1: Provide Input Data for Feature #{feature_code}")
        
        # POP-UP LOGIC: ONLY FOR DAILY SCHEDULE OPTIMIZER
        last_schedule = load_last_schedule()
        if is_schedule_optimizer and last_schedule:
            with col2:
                with st.popover("📅 View Last Schedule"):
                    st.markdown("### Saved Schedule")
                    st.caption("This is your last saved schedule.")
                    st.code(last_schedule, language='markdown')


        if image_needed:
            st.warning("⚠️ **Image Required!** Please upload your meal photo below.")
        
        example_prompt = category_data["features"][selected_feature]
        st.info(f"💡 **Example Input Format:** `{example_prompt}`")

        # FILE UPLOADER (ONLY FOR CALORIE)
        if image_needed:
            uploaded_file = st.file_uploader(
                "Upload Meal Photo (Feature 9 Only)", 
                type=["jpg", "jpeg", "png"],
                key="calorie_image_upload_area"
            )
            if uploaded_file:
                st.image(Image.open(uploaded_file), caption="Meal to Analyze", width=250)
                
        # TEXT AREA INPUT
        user_input = st.text_area(
            "Enter your required data:",
            value="" if not image_needed else "Estimate the calories and macros for this meal.",
            placeholder=example_prompt,
            key="hub_text_input"
        )

        # EXECUTION BUTTON
        if st.button(f"EXECUTE: {selected_feature}", key="hub_execute_btn"):
            
            if image_needed and uploaded_file is None:
                st.error("Please upload an image to run the Image-to-Calorie Estimate.")
            else:
                final_prompt = f"UTILITY HUB: {selected_feature}: {user_input}"
                
                with st.spinner(f'🎯 Routing request to **{selected_feature}**...'):
                    # Increased max_tokens for specific features
                    max_tokens_val = 700
                    if selected_feature in ["28. Grade Calculator", "22. Mathematics Expert AI"]:
                        max_tokens_val = 1000
                    elif selected_feature in ["23. English & Literature Expert AI", "24. History & Social Studies Expert AI"]:
                        max_tokens_val = 1200
                        
                    result = run_ai_generation(final_prompt, uploaded_file, max_tokens=max_tokens_val)
                    
                    st.session_state['hub_result'] = result
                    st.session_state['hub_last_feature_used'] = selected_feature
                    
                    # SAVE LOGIC 
                    if is_schedule_optimizer:
                        save_last_schedule(result) 

    # --- GLOBAL OUTPUT DISPLAY ---
    st.markdown("---")
    st.header("Hub Output")

    if 'hub_result' in st.session_state:
        st.markdown(f"##### Result for: **{st.session_state.hub_last_feature_used}**")
        st.code(
            st.session_state['hub_result'], 
            language='markdown'
        )

# --- 4. TEACHER'S AID MODE FUNCTION (Complex, Multi-Tabbed Application) ---
def render_teacher_aid():
    """Renders the complex, multi-tabbed Teacher's Aid curriculum manager."""
    st.title(f"🎓 {WEBSITE_TITLE}: Teacher's Aid Curriculum Manager")
    st.caption("Use this mode to plan and manage entire units, lessons, and resources.")

    # Initialize state for persistence (Mock DB)
    if 'teacher_db' not in st.session_state:
        st.session_state['teacher_db'] = TEACHER_DB

    st.header("Unit Planning & Resource Generation")

    # Mapped resource names for display and the specific tag to send to the AI
    RESOURCE_MAP = {
        "Unit Overview": "Unit Overview",
        "Lesson Plan": "Lesson Plan",
        "Vocabulary List": "Vocabulary List",
        "Worksheet": "Worksheet",
        "Quiz": "Quiz",
        "Test": "Test"
    }

    tab_titles = list(RESOURCE_MAP.keys())
    tabs = st.tabs(tab_titles)

    # --- Tab Generation Helper Function (Handles the repetitive tab logic) ---
    def generate_and_save_resource(tab_name, tab_object, ai_tag, db_key, ai_instruction_placeholder):
        with tab_object:
            st.subheader(f"1. Generate {tab_name}")
            prompt = st.text_area(
                f"Enter details for the {tab_name.lower()}:",
                placeholder=f"E.g., '{ai_instruction_placeholder}'",
                key=f"{db_key}_prompt",
                height=250 
            )
            if st.button(f"Generate {tab_name}", key=f"generate_{db_key}_btn"):
                if prompt:
                    # CRITICAL: Send the explicit AI_TAG (e.g., "Unit Overview") 
                    final_prompt = f"TEACHER'S AID RESOURCE TAG: {ai_tag}: {prompt}"
                    
                    with st.spinner(f'Building {tab_name} using tag "{ai_tag}"...'):
                        # Specific max_tokens for complex resources
                        max_tokens_val = 1500 
                        result = run_ai_generation(final_prompt, max_tokens=max_tokens_val, temp=0.2)
                        
                        # Store in mock DB (key is derived from resource name)
                        st.session_state['teacher_db'][db_key].append(result)
                        st.success(f"{tab_name} Generated and Saved!")

            st.markdown("---")
            st.subheader(f"Saved {tab_name}")
            if st.session_state['teacher_db'][db_key]:
                for i, resource in enumerate(st.session_state['teacher_db'][db_key]):
                    with st.expander(f"{tab_name} {i+1}"):
                        st.code(resource, language='markdown')
            else:
                st.info(f"No {tab_name.lower()} saved yet.")

    # Apply the helper function to all tabs, ensuring the correct tag is passed
    generate_and_save_resource(
        "Unit Overview", tabs[0], RESOURCE_MAP["Unit Overview"], "units", 
        "Generate a detailed unit plan for a 10th-grade World History class on the Renaissance."
    )
    
    generate_and_save_resource(
        "Lesson Plan", tabs[1], RESOURCE_MAP["Lesson Plan"], "lessons", 
        "Create a 45-minute lesson plan on Newton's First Law of Motion for 9th-grade science."
    )
    
    generate_and_save_resource(
        "Vocabulary List", tabs[2], RESOURCE_MAP["Vocabulary List"], "vocab", 
        "Generate 10 vocabulary words for a 5th-grade math lesson on fractions."
    )
    
    generate_and_save_resource(
        "Worksheet", tabs[3], RESOURCE_MAP["Worksheet"], "worksheets", 
        "Create a 10-question worksheet on subject-verb agreement for 7th-grade English."
    )
    
    generate_and_save_resource(
        "Quiz", tabs[4], RESOURCE_MAP["Quiz"], "quizzes", 
        "Generate a 5-question multiple-choice quiz on the causes of the American Civil War."
    )
    
    generate_and_save_resource(
        "Test", tabs[5], RESOURCE_MAP["Test"], "tests", 
        "Design a comprehensive end-of-unit test for a high school economics class on supply and demand."
    )


# --- 5. MAIN MODE SELECTION ---

# Display the website name in the top left corner (using the sidebar)
st.sidebar.title(WEBSITE_TITLE) 
st.sidebar.markdown("---") 

# Mode Selector
mode = st.sidebar.radio(
    "Select Application Mode:",
    options=["1. Utility Hub (28-in-1)", "2. Teacher's Aid"],
    key="main_mode_select"
)

# Render the selected mode
if mode == "1. Utility Hub (28-in-1)":
    render_utility_hub()
elif mode == "2. Teacher's Aid":
    render_teacher_aid()
