import streamlit as st
import os
import sys
from google import genai
from PIL import Image
from io import BytesIO

# --- 0. INITIAL SETUP AND CONFIGURATION ---

# Custom CSS for a cleaner look
st.markdown(
    """
    <style>
    /* Main Streamlit container width */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 5%;
        padding-right: 5%;
    }
    /* Style for the execution button */
    .stButton>button {
        color: white;
        background-color: #4CAF50; /* Green */
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 1. API Key and Client Initialization
try:
    client = genai.Client()
except Exception:
    st.error("❌ ERROR: Gemini API Key not found. Please set your 'GEMINI_API_KEY' in Replit Secrets.")
    st.stop()

# 2. Load the System Instruction
try:
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    st.error("❌ ERROR: system_instruction.txt not found. Please create it.")
    st.stop()

# 3. Model Configuration
MODEL = 'gemini-2.5-flash' 

# --- 1. CORE AI FUNCTION ---

@st.cache_data(show_spinner=False)
def run_utility_hub(prompt_text: str, uploaded_file: BytesIO = None):
    """
    Sends the user's request (and optional image) to Gemini.
    """
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
    except Exception as e:
        return f"An API Error occurred: {e}"

# --- 2. FEATURE LIST AND EXAMPLES ---

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
        "25. Foreign Language Expert AI": "Conjugate 'aller' in French, passé simple, nous.",
        "26. Science Expert AI": "Explain the concept of entropy in simple terms.",
        "27. Vocational & Applied Expert AI": "Code Debugger: 'for i in range(5) print(i)' (Python)"
    }}
}

# --- 3. STREAMLIT UI AND SIDEBAR NAVIGATION ---

st.set_page_config(layout="wide")
st.title("🤖 27-in-1 Smart Utility Hub")
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


# --- 4. GLOBAL OUTPUT DISPLAY ---

st.markdown("---")
st.header("Hub Output")

if 'result' in st.session_state:
    st.markdown(f"##### Result for: **{st.session_state.last_feature_used}**")
    st.code(st.session_state['result'], language='markdown')
