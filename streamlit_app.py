import streamlit as st
import os
import sys
from google import genai
from PIL import Image
from io import BytesIO
from google.genai.errors import APIError

# --- CONFIGURATION AND PERSISTENCE ---
WEBSITE_TITLE = "Artorius"
CURRENT_APP_TITLE = "28-in-1 Smart Utility Hub" # Correct 28-feature title
# Define a persistent storage file for the last schedule
SCHEDULE_FILE = "last_schedule.txt" 
MODEL = 'gemini-2.5-flash' 

# Set browser tab title, favicon, and layout. 
st.set_page_config(
    page_title=f"{WEBSITE_TITLE} - {CURRENT_APP_TITLE}", 
    page_icon="👑", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CACHED FUNCTIONS FOR PERSISTENCE ---

@st.cache_data
def load_last_schedule():
    """Loads the last saved schedule from the persistent file."""
    try:
        # Check if the file exists before attempting to read
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, "r") as f:
                return f.read()
        return None
    except Exception:
        return None

def save_last_schedule(schedule_text: str):
    """Saves the schedule to the persistent file and clears the cache."""
    try:
        with open(SCHEDULE_FILE, "w") as f:
            f.write(schedule_text)
        # Clear the cache so the app reloads the new content next time
        load_last_schedule.clear()
    except Exception as e:
        st.error(f"Error saving schedule: {e}")

# Load instruction and initialize client (Existing Logic)
try:
    client = genai.Client()
except Exception:
    st.error("❌ ERROR: Gemini API Key not found. Please set your 'GEMINI_API_KEY' in Streamlit Secrets.")
    st.stop()
try:
    # We assume the user has updated their system_instruction.txt to the 28-feature version.
    # The app will function regardless, as the prompt is built from the selected feature.
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    st.error("❌ ERROR: system_instruction.txt not found. Please ensure it exists in your repository.")
    st.stop()


# --- CUSTOM CSS FOR DARK THEME (All Fixes Included) ---
st.markdown(
    """
    <style>
    /* 1. Base App Background and General Text */
    .stApp {
        background-color: #0A0A0A; /* Deep Black */
        color: #FFFFFF; /* Makes all general body text white by default */
    }
    
    /* 2. Secondary Background (Sidebar, Input Widgets) */
    .css-1d391kg, .css-1dp5fjs, section[data-testid='stSidebar'] {
        background-color: #121212; /* Slightly Lighter Black Sidebar */
        border-right: 1px solid #333333;
    }

    /* **SIDEBAR TEXT AND LINE (White)** */
    section[data-testid='stSidebar'] h1, 
    section[data-testid='stSidebar'] h2 {
        color: #FFFFFF !important; /* Forces "Artorius" and "Categories" to white */
    }
    section[data-testid='stSidebar'] .st-emotion-cache-1q1n0ol {
        border-bottom-color: #FFFFFF !important; /* Makes the line white */
    }
    
    /* CRITICAL FIX 1: Sidebar Radio Button Highlight ELIMINATED */
    /* Target the container div and apply a transition and background fix */
    div[data-testid="stSidebar"] div.stRadio > label {
        transition: none !important; /* Stop the default highlight animation */
        background-color: transparent !important; /* Base must be transparent */
        border-color: transparent !important;
    }
    /* Target the specific element that receives the hover/focus highlight */
    div[data-testid="stSidebar"] div.stRadio > label:hover,
    div[data-testid="stSidebar"] div.stRadio > label:focus {
        background-color: #121212 !important; /* Force to sidebar background */
        border-color: #121212 !important;
    }
    /* Ensure the selected item also uses the dark sidebar background */
    div[data-testid="stSidebar"] div.stRadio > label:has(input:checked) {
        background-color: #121212 !important;
    }
    /* Shrink font size slightly to help text fit on one line */
    div[data-testid="stSidebar"] div.stRadio > label {
        font-size: 15px !important; 
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

    /* CRITICAL FIX 2: Popover Button and Content (Schedule Pop-up) */
    /* Target the Popover Button (st.popover) */
    div[data-testid="stPopover"] button {
        color: #FFFFFF !important;
        background-color: #333333 !important; /* Dark background like other buttons */
        border: 1px solid #555555 !important;
    }
    /* Target the Popover Content Box (the modal itself) */
    div[data-baseweb="popover"] div.st-ck, div[data-baseweb="popover"] {
        background-color: #1A1A1A !important; /* Inner dark gray for contrast */
        border: 1px solid #444444 !important;
        color: #FFFFFF !important;
    }
    /* Ensure text inside the popover is white */
    div[data-baseweb="popover"] p, div[data-baseweb="popover"] h3 {
        color: #FFFFFF !important;
    }
    /* Ensure code block inside popover is styled correctly */
    div[data-baseweb="popover"] div.stCode {
        background-color: #212121 !important; /* Slightly lighter inner box */
        border: 1px solid #444444 !important;
    }


    /* 4. INPUT FIELD STYLING (The Box where you type/select) */
    .stTextInput>div>div>input, .stTextArea>div>div, .stSelectbox>div>div {
        background-color: #212121; 
        color: #FFFFFF !important; /* Ensures selected text is white */
        border: 1px solid #444444;
        border-radius: 6px; 
    }
    .stTextArea textarea { /* For multiline text area */
        color: #FFFFFF !important;
    }

    /* 5. Dropdown Menu (Selectbox) Styling */
    .stSelectbox div[data-testid="stTextInput"] div input {
        color: #FFFFFF !important;
    }
    .st-bo, .st-bp, .st-bq, .st-br, .st-bs { 
        background-color: #212121 !important;
        border-color: #444444 !important;
    }
    .st-bo > div > div {
        color: #FFFFFF !important; /* Ensures all text in the list is white */
    }


    /* 6. HEADING COLORS (Big Words: H1, H2, H3, H4) */
    h1, h2, h3, h4, h5, h6 {
        color: #AFAFAF; /* Light medium grey for blending */
        font-weight: 500;
    }

    /* 7. AI RESPONSE BOX BACKGROUND & TEXT (Dark Grey) */
    div.stCode pre {
        background-color: #1A1A1A !important; /* Solid Dark Grey Background */
        color: #FFFFFF !important; /* Ensure output text is white */
        border: none !important; 
        padding: 0; 
    }
    div.stCode pre code {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
    }

    /* 8. AI RESPONSE BOX OUTER CONTAINER STYLING */
    div.stCode {
        background-color: #1A1A1A !important; /* Outer box background */
        border: none !important; 
        border-radius: 12px; 
        padding: 15px; 
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3); 
        overflow-x: auto;
    }
    
    /* 9. General paragraph/label text (White) */
    p, label, li, a, span { 
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


# --- 1. CORE AI FUNCTION (Existing Logic) ---

@st.cache_data(show_spinner=False)
def run_utility_hub(prompt_text: str, uploaded_file: BytesIO = None):
    # Function body remains the same
    parts = []
    
    if uploaded_file is not None:
        try:
            # Need to re-import these here as BytesIO/Image are not global in this scope
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
                system_instruction=SYSTEM_INSTRUCTION, # Using the main 28-feature instruction
                temperature=0.0, 
                max_output_tokens=700 
            )
        )
        return response.text
    except APIError as e:
        # Handle the 503 overload error gracefully
        return f"An API Error occurred: 503 UNAVAILABLE. The model is overloaded. Please retry. Full error: {e}"
    except Exception as e:
        return f"An unknown API Error occurred: {e}"

# --- 2. FEATURE LIST AND EXAMPLES (28 Features) ---

CATEGORIES_FEATURES = {
    # Shortened: Productivity/Cognitive -> Productivity
    "🧠 Productivity": {"icon": "💡", "features": { 
        "1. Daily Schedule Optimizer": "tasks: write report, call client. Time: 9am-12pm.",
        "2. Task Deconstruction Expert": "Vague goal: Start an online business.",
        "3. Get Unstuck Prompter": "Problem: I keep procrastinating on my final essay.",
        "4. Habit Breaker": "Bad habit: Checking my phone right when I wake up.",
        "5. One-Sentence Summarizer": "Text: The sun is a star at the center of the Solar System. It is a nearly perfect ball of hot plasma..."
    }},
    # Shortened: Finance/Math -> Finance
    "💰 Finance": {"icon": "🧮", "features": { 
        "6. Tip & Split Calculator": "bill $85.50, 15% tip, 2 people.",
        "7. Unit Converter": "Convert 500 milliliters to pints.",
        "8. Priority Spending Advisor": "Goal: Save $10k. Planned purchase: $800 new gaming PC."
    }},
    # Shortened: Health/Multi-Modal -> Health
    "📸 Health": {"icon": "🥗", "features": {
        "9. Image-to-Calorie Estimate": "Estimate the calories and macros for this meal.",
        "10. Recipe Improver": "Ingredients: Chicken breast, rice, soy sauce, broccoli.",
        "11. Symptom Clarifier": "Non-emergency symptoms: Headache and minor fatigue in the afternoon."
    }},
    # Shortened: Communication/Writing -> Writing/Comm
    "🗣️ Writing/Comm": {"icon": "✍️", "features": {
        "12. Tone Checker & Rewriter": "Draft: I need the report soon. Desired tone: Professional.",
        "13. Contextual Translator": "Translate: 'It was lit.' Context: Talking about a good concert.",
        "14. Metaphor Machine": "Topic: Artificial Intelligence.",
        "15. Email/Text Reply Generator": "Received: 'Meeting canceled at 3pm.' Response points: Acknowledge, ask to reschedule for tomorrow."
    }},
    # Shortened: Creative/Fun -> Creative
    "💡 Creative": {"icon": "🎭", "features": {
        "16. Idea Generator/Constraint Solver": "Idea type: App name. Constraint: Must contain 'Zen' and be for productivity.",
        "17. Random Fact Generator": "Category: Deep Sea Creatures.",
        "18. 'What If' Scenario Planner": "Hypothetical: Moving to a small town in Norway."
    }},
    # Shortened: Tech/Travel -> Tech
    "💻 Tech": {"icon": "✈️", "features": {
        "19. Concept Simplifier": "Complex topic: Quantum Entanglement. Analogy type: Food.",
        "20. Code Explainer": "Code snippet: 'def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)'",
        "21. Packing List Generator": "Trip: 5 days, cold city, business trip."
    }},
    # School Expert AI
    "📚 School Expert AI": {"icon": "🎓", "features": {
        "22. Mathematics Expert AI": "Solve for x: (4x^2 + 5x = 9) and show steps.",
        "23. English & Literature Expert AI": "Critique this thesis: 'Hamlet is a play about procrastination.'",
        "24. History & Social Studies Expert AI": "Explain the causes and effects of the Cuban Missile Crisis.",
        "25. Foreign Language Expert AI": "Conjugate 'aller' en French, passé simple, nous.",
        "26. Science Expert AI": "Explain the concept of entropy in simple terms.",
        "27. Vocational & Applied Expert AI": "Code Debugger: 'for i in range(5) print(i)' (Python)",
        "28. Teacher's Lesson Planner": "Topic: Photosynthesis. Grade: 7th. Duration: 45 minutes." # ADDED FEATURE 28
    }}
}

# --- 3. STREAMLIT UI AND SIDEBAR NAVIGATION (Existing Logic) ---

# Display the website name in the top left corner (using the sidebar)
st.sidebar.title(WEBSITE_TITLE) 
st.sidebar.markdown("---") 

# Display the main application title with new format
st.title(f"👑 {WEBSITE_TITLE}: {CURRENT_APP_TITLE}")
st.caption("Select a category from the sidebar to begin.")

# Sidebar for category selection
st.sidebar.header("Categories")
category_titles = list(CATEGORIES_FEATURES.keys())
selected_category = st.sidebar.radio("Choose a Domain:", category_titles, index=0, key="category_radio")

# Get features for the selected category
category_data = CATEGORIES_FEATURES[selected_category]
features = list(category_data["features"].keys())

st.header(f"{category_data['icon']} {selected_category}")

# Feature Dropdown (Select Box)
selected_feature = st.selectbox(
    "Choose a specific feature:",
    options=["Select a Feature to Use"] + features,
    key="feature_select"
)

# --- INPUT AREA ---

user_input = ""
uploaded_file = None
image_needed = (selected_feature == "9. Image-to-Calorie Estimate")
is_schedule_optimizer = (selected_feature == "1. Daily Schedule Optimizer")

# 1. SHOW EXAMPLE AND HINT
if selected_feature != "Select a Feature to Use":
    feature_code = selected_feature.split(".")[0]
    col1, col2 = st.columns([0.7, 0.3])
    
    with col1:
        st.markdown(f"##### Step 1: Provide Input Data for Feature #{feature_code}")
    
    # 2. POP-UP LOGIC: ONLY FOR DAILY SCHEDULE OPTIMIZER
    last_schedule = load_last_schedule()
    if is_schedule_optimizer and last_schedule:
        with col2:
            with st.popover("📅 View Last Schedule"):
                st.markdown("### Saved Schedule")
                st.caption("This schedule was saved from your previous session.")
                st.code(last_schedule, language='markdown')


    if image_needed:
        st.warning("⚠️ **Image Required!** Please upload your meal photo below.")
    
    example_prompt = category_data["features"][selected_feature]
    st.info(f"💡 **Example Input Format:** `{example_prompt}`")

    # 3. FILE UPLOADER (ONLY FOR CALORIE)
    if image_needed:
        uploaded_file = st.file_uploader(
            "Upload Meal Photo (Feature 9 Only)", 
            type=["jpg", "jpeg", "png"],
            key="calorie_image_upload_area"
        )
        if uploaded_file:
            st.image(uploaded_file, caption="Meal to Analyze", width=250)
            
    # 4. TEXT AREA INPUT
    user_input = st.text_area(
        "Enter your required data (e.g., your tasks, your math problem, your ingredients):",
        value="" if not image_needed else "Estimate the calories and macros for this meal.",
        placeholder=example_prompt,
        key="text_input"
    )

    # 5. EXECUTION BUTTON
    if st.button(f"EXECUTE: {selected_feature}", key="execute_btn"):
        
        # Validation for Calorie Feature
        if image_needed and uploaded_file is None:
            st.error("Please upload an image to run the Image-to-Calorie Estimate.")
        else:
            # Combine feature name and user input for the AI routing
            final_prompt = f"{selected_feature}: {user_input}"
            
            with st.spinner(f'🎯 Routing request to **{selected_feature}**...'):
                # Send the request to the core function
                result = run_utility_hub(final_prompt, uploaded_file)
                
                # Update Session State
                st.session_state['result'] = result
                st.session_state['last_feature_used'] = selected_feature
                
                # *** PERSISTENT SAVE LOGIC ***
                if is_schedule_optimizer:
                    save_last_schedule(result)
                # *****************************


# --- 4. GLOBAL OUTPUT DISPLAY (Existing Logic) ---

st.markdown("---")
st.header("Hub Output")

if 'result' in st.session_state:
    st.markdown(f"##### Result for: **{st.session_state.last_feature_used}**")
    st.code(
        st.session_state['result'], 
        language='markdown'
    )
