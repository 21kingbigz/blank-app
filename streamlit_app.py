import streamlit as st
import os
import sys
from google import genai
from PIL import Image
from io import BytesIO
from google.genai.errors import APIError

# --- WEBSITE BRANDING & CONFIGURATION ---
WEBSITE_TITLE = "Artorius"
CURRENT_APP_TITLE = "27-in-1 Smart Utility Hub"

# Set browser tab title, favicon, and layout. 
st.set_page_config(
    page_title=f"{WEBSITE_TITLE} - {CURRENT_APP_TITLE}", 
    page_icon="👑", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for the precise dark theme specifications
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

    /* CRITICAL FIX: Sidebar text color */
    section[data-testid='stSidebar'] .css-pk0abn, 
    section[data-testid='stSidebar'] .css-1dp5fjs {
        color: #FFFFFF !important; /* Forces sidebar text (like "Artorius", "Categories") to white */
    }
    
    /* CRITICAL FIX: Sidebar separator line color */
    section[data-testid='stSidebar'] .st-emotion-cache-1q1n0ol { /* This targets the divider line */
        border-bottom-color: #FFFFFF !important; /* Makes the line white */
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

    /* 4. TEXT INPUT FIELDS (What the user types) */
    .stTextInput>div>div>input, .stTextArea>div>div, .stSelectbox>div>div {
        background-color: #212121; 
        color: #FFFFFF !important; /* Ensures text user types is pure white */
        border: 1px solid #444444;
        border-radius: 6px; 
    }
    .stTextArea textarea { /* For multiline text area */
        color: #FFFFFF !important;
    }

    /* 5. HEADING COLORS (Big Words: H1, H2, H3, H4, etc.) */
    h1, h2, h3, h4, h5, h6 {
        color: #AFAFAF; /* Light medium grey for blending */
        font-weight: 500;
    }

    /* 6. ***CRITICAL FIX: AI RESPONSE BOX BACKGROUND & TEXT (Image 1)*** */
    /* This targets the 'pre' element which is usually the innermost container of text in st.code */
    div.stCode pre {
        background-color: #1A1A1A !important; /* Solid Dark Grey Background */
        color: #FFFFFF !important; /* Ensure text inside is white */
        border: none !important; /* Remove borders */
        padding: 0; /* Remove internal padding to let the outer div control it */
    }

    /* 7. AI RESPONSE BOX OUTER CONTAINER STYLING */
    /* This sets the background for the entire box wrapper around the text */
    div.stCode {
        background-color: #1A1A1A !important; /* Ensure the outer container is also dark grey */
        border: none !important; 
        border-radius: 12px; 
        padding: 15px; /* Apply padding here for the entire box */
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3); 
        overflow-x: auto;
    }
    
    /* 8. General paragraph/label text */
    p, label, li, a, span { /* Added span to target more general text */
        color: #FFFFFF !important; /* Ensure general body text is white */
    }
    
    /* 9. Info/Warning Boxes - clean look */
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

# 1. API Key and Client Initialization
try:
    client = genai.Client()
except Exception:
    st.error("❌ ERROR: Gemini API Key not found. Please set your 'GEMINI_API_KEY' in Streamlit Secrets.")
    st.stop()

# 2. Load the System Instruction (Existing Logic)
try:
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    st.error("❌ ERROR: system_instruction.txt not found. Please ensure it exists in your repository.")
    st.stop()

# 3. Model Configuration (Existing Logic)
MODEL = 'gemini-2.5-flash' 

# --- 1. CORE AI FUNCTION (Existing Logic) ---

@st.cache_data(show_spinner=False)
def run_utility_hub(prompt_text: str, uploaded_file: BytesIO = None):
    # Function body remains the same
    parts = []
    
    if uploaded_file is not None:
        try:
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

# --- 2. FEATURE LIST AND EXAMPLES (Existing Logic) ---

CATEGORIES_FEATURES = {
    "🧠 Productivity/Cognitive": {"icon": "💡", "features": {
        "1. Daily Schedule Optimizer": "tasks: write report, call client. Time: 9am-12pm.",
        "2. Task Deconstruction Expert": "Vague goal: Start an online business.",
        "3. Get Unstuck Prompter": "Problem: I keep procrastinating on my final essay.",
        "4. Habit Breaker": "Bad habit: Checking my phone right when I wake up.",
        "5. One-Sentence Summarizer": "Text: The sun is a star at the center of the Solar System. It is a nearly perfect ball of hot plasma..."
    }},
    "💰 Finance/Math": {"icon": "🧮", "features": {
        "6. Tip & Split Calculator": "bill $85.50, 15% tip, 2 people.",
        "7. Unit Converter": "Convert 500 milliliters to pints.",
        "8. Priority Spending Advisor": "Goal: Save $10k. Planned purchase: $800 new gaming PC."
    }},
    "📸 Health/Multi-Modal": {"icon": "🥗", "features": {
        "9. Image-to-Calorie Estimate": "Estimate the calories and macros for this meal.",
        "10. Recipe Improver": "Ingredients: Chicken breast, rice, soy sauce, broccoli.",
        "11. Symptom Clarifier": "Non-emergency symptoms: Headache and minor fatigue in the afternoon."
    }},
    "🗣️ Communication/Writing": {"icon": "✍️", "features": {
        "12. Tone Checker & Rewriter": "Draft: I need the report soon. Desired tone: Professional.",
        "13. Contextual Translator": "Translate: 'It was lit.' Context: Talking about a good concert.",
        "14. Metaphor Machine": "Topic: Artificial Intelligence.",
        "15. Email/Text Reply Generator": "Received: 'Meeting canceled at 3pm.' Response points: Acknowledge, ask to reschedule for tomorrow."
    }},
    "💡 Creative/Fun": {"icon": "🎭", "features": {
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
        "27. Vocational & Applied Expert AI": "Code Debugger: 'for i in range(5) print(i)' (Python)"
    }}
}

# --- 3. STREAMLIT UI AND SIDEBAR NAVIGATION (Updated Title) ---

# Display the website name in the top left corner (using the sidebar)
st.sidebar.title(WEBSITE_TITLE) 
st.sidebar.markdown("---") # Visual separator

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

# --- INPUT AREA (Existing Logic) ---

user_input = ""
uploaded_file = None
image_needed = (selected_feature == "9. Image-to-Calorie Estimate")

# 1. SHOW EXAMPLE AND HINT
if selected_feature != "Select a Feature to Use":
    feature_code = selected_feature.split(".")[0]
    st.markdown(f"##### Step 1: Provide Input Data for Feature #{feature_code}")
    
    if image_needed:
        st.warning("⚠️ **Image Required!** Please upload your meal photo below.")
    
    example_prompt = category_data["features"][selected_feature]
    st.info(f"💡 **Example Input Format:** `{example_prompt}`")

    # 2. FILE UPLOADER (ONLY FOR CALORIE)
    if image_needed:
        uploaded_file = st.file_uploader(
            "Upload Meal Photo (Feature 9 Only)", 
            type=["jpg", "jpeg", "png"],
            key="calorie_image_upload_area"
        )
        if uploaded_file:
            st.image(uploaded_file, caption="Meal to Analyze", width=250)
            
    # 3. TEXT AREA INPUT
    user_input = st.text_area(
        "Enter your required data (e.g., your tasks, your math problem, your ingredients):",
        value="" if not image_needed else "Estimate the calories and macros for this meal.",
        placeholder=example_prompt,
        key="text_input"
    )

    # 4. EXECUTION BUTTON
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
                
                # Store and display the result
                st.session_state['result'] = result
                st.session_state['last_feature_used'] = selected_feature


# --- 4. GLOBAL OUTPUT DISPLAY (Existing Logic) ---

st.markdown("---")
st.header("Hub Output")

if 'result' in st.session_state:
    st.markdown(f"##### Result for: **{st.session_state.last_feature_used}**")
    st.code(st.session_state['result'], language='markdown')
