import streamlit as st
import os
import sys
from google import genai
from PIL import Image
from io import BytesIO
from google.genai.errors import APIError

# --- CONFIGURATION AND PERSISTENCE ---
WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash' 
# Key for session state persistence
SCHEDULE_KEY = "last_schedule_data" 
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
    # This pattern safely gets data from st.session_state if it exists
    return st.session_state.get(SCHEDULE_KEY, None) 

def save_last_schedule(schedule_text: str):
    """Saves the latest schedule to session state."""
    st.session_state[SCHEDULE_KEY] = schedule_text

# Load instruction and initialize client
try:
    client = genai.Client()
except Exception:
    st.error("❌ ERROR: Gemini Client initialization failed. Please ensure the API Key is correctly configured.")
    st.stop()
try:
    # This instruction handles both the Utility Hub and the Teacher's Aid text generation
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    SYSTEM_INSTRUCTION = """
    You are the 'Artorius AI.' Depending on the user's selected mode, adopt one of two personas:
    1. Utility Hub: Act as a stateless, expert tool, providing direct, concise results formatted in markdown.
    2. Teacher's Aid: Act as a comprehensive curriculum management assistant, providing detailed, structured, and helpful content for K-12 educators.
    """


# --- CUSTOM CSS FOR DARK THEME (The fully corrected styling) ---
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

    /* **SIDEBAR TEXT AND LINE (White)** */
    section[data-testid='stSidebar'] h1, 
    section[data-testid='stSidebar'] h2 {
        color: #FFFFFF !important; 
    }
    section[data-testid='stSidebar'] .st-emotion-cache-1q1n0ol {
        border-bottom-color: #FFFFFF !important; 
    }
    
    /* Sidebar Radio Button Styling */
    div[data-testid="stSidebar"] div.stRadio > label {
        transition: none !important; 
        background-color: transparent !important;
        border-color: transparent !important;
    }
    div[data-testid="stSidebar"] div.stRadio > label {
        font-size: 15px !important; 
    }
    /* Make all sidebar radio button text white (especially the Mode Selector) */
    div[data-testid="stSidebar"] div.stRadio label {
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

    /* Popover Button and Content (Schedule Pop-up) */
    div[data-testid="stPopover"] button {
        color: #FFFFFF !important;
        background-color: #333333 !important; 
        border: 1px solid #555555 !important;
    }
    div[data-baseweb="popover"] div.st-ck, div[data-baseweb="popover"] {
        background-color: #1A1A1A !important; 
        border: 1px solid #444444 !important;
        color: #FFFFFF !important;
    }
    div[data-baseweb="popover"] p, div[data-baseweb="popover"] h3 {
        color: #FFFFFF !important;
    }
    div[data-baseweb="popover"] div.stCode {
        background-color: #212121 !important; 
        border: 1px solid #444444 !important;
    }
    
    /* Fix for tabs background */
    .stTabs [data-testid="stMarkdownContainer"] {
        background-color: #1A1A1A; /* Inner section background for Teacher's Aid */
        padding: 15px;
        border-radius: 8px;
    }


    /* 4. INPUT FIELD STYLING (Text color and background) */
    .stTextInput>div>div>input, .stTextArea>div>div, .stSelectbox>div>div {
        background-color: #212121; 
        color: #FFFFFF !important; 
        border: 1px solid #444444;
        border-radius: 6px; 
    }
    .stTextArea textarea { 
        color: #FFFFFF !important;
    }

    /* 5. Dropdown Menu (Selectbox) Styling */
    .stSelectbox div[data-testid="stTextInput"] div input {
        color: #FFFFFF !important;
    }
    div[data-baseweb="select"] ul {
        background-color: #212121 !important;
        border-color: #444444 !important;
    }
    div[data-baseweb="select"] ul li div {
        color: #FFFFFF !important; 
    }
    div[data-baseweb="select"] ul li:hover {
        background-color: #333333 !important; 
    }


    /* 6. HEADING COLORS (Big Words: H1, H2, H3, H4) */
    h1, h2, h3, h4, h5, h6 {
        color: #AFAFAF; 
        font-weight: 500;
    }

    /* 7. AI RESPONSE BOX BACKGROUND & TEXT */
    div.stCode pre {
        background-color: #1A1A1A !important; 
        color: #FFFFFF !important; 
        border: none !important; 
        padding: 0; 
    }
    div.stCode pre code {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
    }

    /* Force white text for all content inside the output box */
    div.stCode pre *, div.stCode pre p {
        color: #FFFFFF !important;
    }
    
    /* CRITICAL FIX 3: Selection Highlight Visibility */
    div.stCode ::selection {
        background-color: #004d99; /* Dark Blue highlight for selection */
        color: #FFFFFF !important; /* Keep selected text white */
    }


    /* 8. AI RESPONSE BOX OUTER CONTAINER STYLING */
    div.stCode {
        background-color: #1A1A1A !important; 
        border: none !important; 
        border-radius: 12px; 
        padding: 15px; 
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3); 
        overflow-x: auto;
    }
    
    /* 9. General paragraph, label, list, and link text (White) */
    p, li, a, span { 
        color: #FFFFFF !important; 
    }
    /* Explicitly targeting all labels for white text (Fix for the words not being white) */
    .stApp label {
        color: #FFFFFF !important;
    }
    
    /* 10. Info/Warning Boxes - clean look */
    .stAlert {
        border-left: 5px solid #666666;
        color: #DDDDDD;
        background-color: #1A1A1A;
        border-radius: 6px;
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
            from PIL import Image
            from io import BytesIO
            uploaded_file.seek(0) 
            image = Image.open(uploaded_file)
            parts.append(image)
        except Exception as e:
            return f"ERROR loading image: {e}"

    parts.append(prompt_text)

    # API Call with System Instruction
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
        # NEW FEATURE 28: Grade Calculator
        "28. Grade Calculator": "assignments: Quiz 80/100 (20%), Midterm 90/100 (30%), Final 75/100 (50%)." 
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
        
        # POP-UP LOGIC: ONLY FOR DAILY SCHEDULE OPTIMIZER (Now using session_state persistence)
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
                from PIL import Image
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
                    result = run_ai_generation(final_prompt, uploaded_file)
                    
                    st.session_state['hub_result'] = result
                    st.session_state['hub_last_feature_used'] = selected_feature
                    
                    # SAVE LOGIC RESTORED HERE
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

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Unit", "Lesson Plans", "Vocab", "Worksheets", "Quizzes", "Tests"]
    )

    # --- Unit Tab ---
    with tab1:
        st.subheader("1. Create New Unit")
        unit_prompt = st.text_area(
            "Unit Details (e.g., Topic, Grade, Duration):",
            placeholder="Create a Unit called 'The American Revolution' for 8th-grade history, lasting 10 days.",
            key="unit_prompt"
        )
        if st.button("Generate Unit Overview", key="generate_unit_btn"):
            if unit_prompt:
                final_prompt = f"TEACHER'S AID: Generate a detailed unit overview including objectives, key topics, and suggested assessments for the following: {unit_prompt}"
                with st.spinner('Building Unit...'):
                    result = run_ai_generation(final_prompt, max_tokens=1500, temp=0.2)
                    # Mock storage
                    st.session_state['teacher_db']['units'].append(result)
                    st.success("Unit Generated and Saved!")

        st.markdown("---")
        st.subheader("Saved Units")
        if st.session_state['teacher_db']['units']:
            for i, unit in enumerate(st.session_state['teacher_db']['units']):
                with st.expander(f"Unit {i+1}"):
                    st.code(unit, language='markdown')
        else:
            st.info("No units saved yet. Generate one above!")

    # --- Lesson Plans Tab ---
    with tab2:
        st.subheader("2. Generate Lesson Plan")
        lesson_prompt = st.text_area(
            "Lesson Details:",
            placeholder="Based on the American Revolution Unit, create a 45-minute lesson plan on 'Causes of the War' for 8th graders.",
            key="lesson_prompt"
        )
        if st.button("Generate Lesson Plan", key="generate_lesson_btn"):
            if lesson_prompt:
                final_prompt = f"TEACHER'S AID: Create a detailed, 45-minute lesson plan (including warm-up, main activity, materials, and wrap-up) for the topic: {lesson_prompt}"
                with st.spinner('Building Lesson Plan...'):
                    result = run_ai_generation(final_prompt, max_tokens=1500, temp=0.2)
                    st.session_state['teacher_db']['lessons'].append(result)
                    st.success("Lesson Plan Generated and Saved!")

        st.markdown("---")
        st.subheader("Saved Lesson Plans")
        if st.session_state['teacher_db']['lessons']:
            for i, lesson in enumerate(st.session_state['teacher_db']['lessons']):
                with st.expander(f"Lesson Plan {i+1}"):
                    st.code(lesson, language='markdown')
        else:
            st.info("No lesson plans saved yet.")

    # --- Other Tabs (Simplified Placeholder Logic) ---
    def generate_and_save_resource(tab_name, prompt_key, button_key, db_key, ai_instruction):
        st.subheader(f"3. Generate {tab_name}")
        prompt = st.text_area(
            f"Enter details for the {tab_name.lower()}:",
            placeholder=f"{ai_instruction} (e.g., '10 key terms for the American Revolution Unit')",
            key=prompt_key
        )
        if st.button(f"Generate {tab_name}", key=button_key):
            if prompt:
                final_prompt = f"TEACHER'S AID: {ai_instruction}: {prompt}"
                with st.spinner(f'Building {tab_name}...'):
                    result = run_ai_generation(final_prompt, max_tokens=1000, temp=0.3)
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

    with tab3:
        generate_and_save_resource("Vocabulary List", "vocab_prompt", "generate_vocab_btn", "vocab", 
                                   "Generate a vocabulary list with definitions and example sentences")
    with tab4:
        generate_and_save_resource("Worksheet", "worksheet_prompt", "generate_worksheet_btn", "worksheets", 
                                   "Create a 10-question worksheet with mixed question types (matching, short answer)")
    with tab5:
        generate_and_save_resource("Quiz", "quiz_prompt", "generate_quiz_btn", "quizzes", 
                                   "Generate a 5-question multiple choice quiz with answer key")
    with tab6:
        generate_and_save_resource("Test", "test_prompt", "generate_test_btn", "tests", 
                                   "Design a comprehensive end-of-unit test covering 4 essay questions and 15 multiple choice questions")


# --- 5. MAIN MODE SELECTION ---

# Display the website name in the top left corner (using the sidebar)
st.sidebar.title(WEBSITE_TITLE) 
st.sidebar.markdown("---") 

# Mode Selector
mode = st.sidebar.radio(
    "Select Application Mode:",
    options=["1. Utility Hub (28 Features)", "2. Teacher's Aid"],
    index=0,
    key="app_mode_radio"
)
st.sidebar.markdown("---") 


# Run the selected mode
if mode == "1. Utility Hub (28 Features)":
    render_utility_hub()
elif mode == "2. Teacher's Aid":
    render_teacher_aid()
