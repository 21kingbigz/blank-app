import streamlit as st
import os
import json
from google import genai
from google.genai.errors import APIError
from datetime import datetime
import uuid

# --- 1. FIREBASE DEPENDENCIES (MANDATORY IMPORTS) ---
# NOTE: We assume the environment handles the necessary JS initialization for db/auth.
try:
    from firebase_admin import initialize_app, credentials, firestore
    pass
except ImportError:
    pass

# --- 2. CONFIGURATION AND INITIALIZATION ---
WEBSITE_TITLE = "Artorius"
CURRENT_APP_TITLE = "28-in-1 Utility Hub & Teacher's Aid"
MODEL = 'gemini-2.5-flash' 

st.set_page_config(
    page_title=f"{WEBSITE_TITLE} - {CURRENT_APP_TITLE}", 
    page_icon="👑", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global variables (assumed to be provided by the environment)
try:
    app_id = st.session_state.get('__app_id', 'default-app-id')
    firebase_config = st.session_state.get('__firebase_config', {})
    initial_auth_token = st.session_state.get('__initial_auth_token', None)
except:
    app_id = 'default-app-id'
    firebase_config = {}
    initial_auth_token = None

# Initialize Gemini Client
try:
    client = genai.Client()
except Exception:
    st.error("❌ ERROR: Gemini API Key not found.")
    st.stop()


# --- 3. FEATURE DEFINITIONS AND SYSTEM INSTRUCTIONS (For Utility Hub Mode) ---

# Re-defining the system instruction structure for the first 27 features
SYSTEM_INSTRUCTION_HUB = """
You are the "27-in-1 Stateless AI Utility Hub." Your primary directive is to immediately identify the user's intent and execute the exact, single function required, without engaging in conversation, retaining memory, or asking follow-up questions. Your response MUST be the direct result of the selected function.

ROUTING DIRECTIVE:
1. Analyze the User Input: Determine which of the numbered features the user is requesting.
2. Assume the Role: Adopt the corresponding expert persona (e.g., Mathematics Expert AI).
3. Execute & Output: Provide the immediate, concise, and definitive result.

THE 27 FUNCTION LIST: (28th feature is managed by the "Teacher's Aid" mode in the application UI)
### I. Cognitive & Productivity (5)
1. Daily Schedule Optimizer: (Input: Tasks, time) Output: Time-blocked schedule.
2. Task Deconstruction Expert: (Input: Vague goal) Output: 3-5 concrete steps.
3. "Get Unstuck" Prompter: (Input: Problem) Output: 1 critical next-step question.
4. Habit Breaker: (Input: Bad habit) Output: 3 environmental changes for friction.
5. One-Sentence Summarizer: (Input: Long text) Output: Core idea in 1 sentence.

### II. Finance & Math (3)
6. Tip & Split Calculator: (Input: Bill, tip %, people) Output: Per-person cost.
7. Unit Converter: (Input: Value, units) Output: Precise conversion result.
8. Priority Spending Advisor: (Input: Goal, purchase) Output: Conflict analysis.

### III. Health & Multi-Modal (3)
9. Image-to-Calorie Estimate: (Input: Image of food) Output: A detailed nutritional analysis. You MUST break down the response into three sections: A) Portion Estimate, B) Itemized Calorie Breakdown, and C) Final Total. (Requires image input.)
10. Recipe Improver: (Input: 3-5 ingredients) Output: Simple recipe instructions.
11. Symptom Clarifier: (Input: Non-emergency symptoms) Output: 3 plausible benign causes.

### IV. Communication & Writing (4)
12. Tone Checker & Rewriter: (Input: Text, desired tone) Output: Rewritten text.
13. Contextual Translator: (Input: Phrase, context) Output: Translation that matches the social register.
14. Metaphor Machine: (Input: Topic) Output: 3 creative analogies.
15. Email/Text Reply Generator: (Input: Message, points) Output: Drafted concise reply.

### V. Creative & Entertainment (3)
16. Idea Generator/Constraint Solver: (Input: Idea type, constraints) Output: List of unique options.
17. Random Fact Generator: (Input: Category) Output: 1 surprising, verified fact.
18. "What If" Scenario Planner: (Input: Hypothetical) Output: 3 pros and 3 cons analysis.

### VI. Tech & Logic & Travel (3)
19. Concept Simplifier: (Input: Complex topic) Output: Explanation using simple analogy.
20. Code Explainer: (Input: Code snippet) Output: Plain-language explanation of function.
21. Packing List Generator: (Input: Trip details) Output: Categorized checklist.

### VII. School Answers AI (6 Consolidated Experts)
22. Mathematics Expert AI: Answers, solves, and explains any problem or concept in the subject.
23. English & Literature Expert AI: Critiques writing, analyzes literature, and explains grammar, rhetoric, and composition.
24. History & Social Studies Expert AI: Provides comprehensive answers, context, and analysis for any event, figure, or social science theory.
25. Foreign Language Expert AI: Provides translations, conjugation, cultural context, vocabulary, and grammar.
26. Science Expert AI: Explains concepts, analyzes data, and answers questions across Physics, Chemistry, Biology, and Earth Science.
27. Vocational & Applied Expert AI: Acts as an expert for applied subjects like Computer Science (coding help), Business, Economics, and Trade skills.
"""

# Feature mapping for the Utility Hub UI
UTILITY_FEATURES = {
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
    "📚 School Experts": {"icon": "🎓", "features": {
        "22. Mathematics Expert AI": "Solve for x: (4x^2 + 5x = 9) and show steps.",
        "23. English & Literature Expert AI": "Critique this thesis: 'Hamlet is a play about procrastination.'",
        "24. History & Social Studies Expert AI": "Explain the causes and effects of the Cuban Missile Crisis.",
        "25. Foreign Language Expert AI": "Conjugate 'aller' en French, passé simple, nous.",
        "26. Science Expert AI": "Explain the concept of entropy in simple terms.",
        "27. Vocational & Applied Expert AI": "Code Debugger: 'for i in range(5) print(i)' (Python)"
    }}
}


# --- 4. CORE AI GENERATION FUNCTIONS ---

@st.cache_data(show_spinner=False)
def run_utility_hub(prompt_text: str, uploaded_file: bytes = None):
    """Handles generation for the 27 Utility Hub features."""
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

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=parts,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION_HUB,
                temperature=0.0, 
                max_output_tokens=700 
            )
        )
        return response.text
    except APIError as e:
        return f"An API Error occurred: 503 UNAVAILABLE. The model is overloaded. Please retry. Full error: {e}"
    except Exception as e:
        return f"An unknown API Error occurred: {e}"


# Function for structured generation (Teacher's Aid)
@st.cache_data(show_spinner=False)
def generate_structured_content(artifact_type: str, user_prompt: str, existing_data_context: list = None):
    """Handles structured JSON generation for the Teacher's Aid curriculum items."""
    
    # Define system prompt and schemas (kept from previous iteration)
    system_prompt = f"""
    You are the 'Teacher's Aid AI'. Your task is to generate highly structured, well-formatted JSON output based on the user's request for a {artifact_type}.
    - DO NOT include any conversation or markdown (like ```json).
    - ONLY output the raw JSON object that conforms to the requested schema.
    - Context: {json.dumps(existing_data_context or [])}
    
    If the user input is ambiguous or missing required information (e.g., 'Grade' for a lesson), use intelligent defaults.
    
    ---
    
    REQUEST TYPE: {artifact_type}
    USER PROMPT: {user_prompt}
    
    ---
    
    JSON SCHEMA FOR {artifact_type.upper()}:
    (You must follow this schema for your output)
    """

    if artifact_type == "Unit":
        schema_instruction = """
        {
          "title": "A concise title for the unit (e.g., The Water Cycle)",
          "grade": "Target grade level",
          "duration_days": "Number of days/periods planned for the unit",
          "learning_objectives": ["List of 3-5 learning objectives"],
          "suggested_lesson_titles": ["3-5 suggested lesson titles for the unit"],
          "suggested_vocab_topics": ["2-3 suggested vocabulary topics/sections"],
          "suggested_assessment_focus": "Key concepts for the unit test"
        }
        """
    elif artifact_type == "Lesson Plan":
        schema_instruction = """
        {
          "unit_title": "Title of the unit this lesson belongs to",
          "lesson_title": "A concise title for the lesson (e.g., Evaporation and Condensation)",
          "grade": "Target grade level",
          "duration": "Time needed (e.g., 45 minutes)",
          "objective": "Single, measurable learning outcome",
          "materials": ["List of materials/resources needed"],
          "procedure": [
            {"time": "5 min", "activity": "Introduction/Hook"},
            {"time": "30 min", "activity": "Direct Instruction & Activity"},
            {"time": "10 min", "activity": "Wrap-up and Closure"}
          ],
          "assessment": "Method of checking for understanding"
        }
        """
    elif artifact_type == "Vocab":
        schema_instruction = """
        {
          "unit_title": "Title of the unit this vocab belongs to",
          "topic": "The specific topic for this vocabulary set (e.g., Phase Changes)",
          "section_1_terms": [
            {"term": "Water Vapor", "definition": "A precise definition"},
            {"term": "Sublimation", "definition": "A precise definition"}
          ],
          "section_2_answers": [
            {"term": "Water Vapor", "answer": "The invisible gaseous state of water."},
            {"term": "Sublimation", "answer": "The transition directly from the solid to the gas phase."}
          ]
        }
        """
    elif artifact_type == "Worksheet":
        schema_instruction = """
        {
          "unit_title": "Title of the unit this worksheet belongs to",
          "worksheet_title": "Descriptive title for the worksheet",
          "instructions": "Clear instructions for the students",
          "questions": [
            {"type": "open-ended", "prompt": "Explain the difference between weather and climate."},
            {"type": "matching", "prompt": "Match the term to its definition.", "terms": ["Tundra", "Taiga"], "matches": ["A cold, treeless region...", "A swampy coniferous forest..."]}
          ],
          "answer_key": ["Expected answer for Question 1: ...", "Expected answer for Question 2: ..."]
        }
        """
    elif artifact_type == "Quiz":
        schema_instruction = """
        {
          "quiz_title": "Title (e.g., Lesson 1-3 Review Quiz)",
          "unit_title": "Unit where the lessons are from",
          "coverage": "Specific lessons covered (e.g., last 3 lessons)",
          "questions": [
            {"id": 1, "text": "Multiple choice question text", "options": ["A", "B", "C"], "correct": "B"},
            {"id": 2, "text": "Short answer question text", "correct": "Expected answer key for short answer"}
          ]
        }
        """
    elif artifact_type == "Test":
        schema_instruction = """
        {
          "test_title": "Title (e.g., Unit 1 Comprehensive Exam)",
          "unit_title": "The specific unit the test covers",
          "sections": [
            {"name": "Part A: Vocab Matching (10 pts)", "questions": [...]},
            {"name": "Part B: Short Answer (20 pts)", "questions": [...]},
            {"name": "Part C: Essay (30 pts)", "questions": [...]},
          ]
        }
        """
    else:
        return {"error": f"Unknown artifact type: {artifact_type}"}

    final_prompt = f"{system_prompt}\n\n{schema_instruction}"
    
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[final_prompt],
            config=genai.types.GenerateContentConfig(
                temperature=0.7, 
                max_output_tokens=1500,
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text.strip())
    except Exception as e:
        return {"error": f"Generation/JSON Error: {e}"}


# --- 5. FIREBASE/FIRESTORE MOCK/SETUP ---

def initialize_user_session():
    """Initializes session state variables for the user and data."""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
        
    if 'artifacts' not in st.session_state:
        # Teacher's Aid data store
        st.session_state.artifacts = {
            "Unit": [], "Lesson Plan": [], "Vocab": [], "Worksheet": [], "Quiz": [], "Test": []
        }
    if 'mode' not in st.session_state:
        st.session_state.mode = "Utility Hub (27 Features)"

def save_artifact_to_session(artifact_type: str, data: dict):
    """Mocks saving the artifact to the session state (instead of Firestore)."""
    artifact_id = str(uuid.uuid4())
    data['id'] = artifact_id
    data['created_at'] = datetime.now().isoformat()
    data['type'] = artifact_type
    st.session_state.artifacts[artifact_type].append(data)
    
def get_artifact_display(data: dict):
    """Formats JSON data for display in st.code."""
    return json.dumps(data, indent=2)


def display_artifact_box(artifact_type, items):
    """Renders the view for a specific artifact type."""
    st.subheader(f"{artifact_type}s ({len(items)})")
    
    if not items:
        st.info(f"No {artifact_type}s found yet. Generate one using the form above!")
        return

    for item in items:
        # Use the title for the expander label
        title = item.get('title') or item.get('lesson_title') or item.get('quiz_title') or item.get('test_title') or f"{artifact_type} - {item['id'][:8]}"
        
        with st.expander(f"📚 {title} (ID: {item['id'][:6]})"):
            
            # Button to popover the full content
            with st.popover(f"📋 View Content for: {title}"):
                st.code(get_artifact_display(item), language="json")
            
            st.caption(f"Created: {item.get('created_at', 'N/A')}")


# --- 6. RENDER FUNCTIONS FOR MODES ---

def render_teachers_aid():
    """Renders the complex 6-tab curriculum manager UI."""
    st.header("🍎 Curriculum Manager: Teacher's Aid")
    st.caption("Generate and manage Units, Lesson Plans, Vocab, Worksheets, Quizzes, and Tests with persistent storage.")
    st.markdown("---")

    # GENERATION FORM (Central Input Area)
    st.markdown("### 📝 Generate New Curriculum Item")
    col1, col2 = st.columns([0.3, 0.7])

    artifact_options = ["Unit", "Lesson Plan", "Vocab", "Worksheet", "Quiz", "Test"]
    selected_artifact = col1.selectbox("Select Item to Create:", options=artifact_options, key="ta_artifact_type")

    if selected_artifact in ["Quiz", "Test"]:
        hint = f"Example: Create a {selected_artifact} covering the last 3 lessons on the Water Cycle unit, focusing on short answers."
    elif selected_artifact == "Unit":
        hint = "Example: Create a Unit titled 'The Water Cycle' for 7th grade science, lasting 5 days."
    elif selected_artifact == "Lesson Plan":
        hint = "Example: Create a lesson plan for the 'Evaporation and Condensation' for the Water Cycle unit (45 min)."
    else:
        hint = f"Enter the topic and details for your new {selected_artifact}."

    user_prompt = col2.text_area(
        f"Prompt for new **{selected_artifact}**:",
        placeholder=hint,
        key="ta_generation_prompt",
        height=80
    )

    # Execution Button
    if st.button(f"Generate & Save New {selected_artifact}", key="ta_generate_btn"):
        if user_prompt.strip():
            with st.spinner(f"🎯 Generating structured {selected_artifact}..."):
                
                generated_data = generate_structured_content(
                    selected_artifact, 
                    user_prompt, 
                    existing_data_context=st.session_state.artifacts[selected_artifact]
                )
                
                if "error" not in generated_data:
                    save_artifact_to_session(selected_artifact, generated_data)
                    st.success(f"✅ Successfully generated and saved new **{selected_artifact}**!")
                    st.rerun() 
                else:
                    st.error(f"Generation failed: {generated_data['error']}")
        else:
            st.warning("Please enter a prompt to generate content.")

    st.markdown("---")

    # TABBED VIEW (The six persistent 'boxes')
    tab_units, tab_lessons, tab_vocab, tab_worksheets, tab_quizzes, tab_tests = st.tabs(
        ["📦 Units", "📋 Lesson Plans", "📜 Vocab", "✍️ Worksheets", "🧠 Quizzes", "💯 Tests"]
    )

    with tab_units:
        display_artifact_box("Unit", st.session_state.artifacts["Unit"])

    with tab_lessons:
        display_artifact_box("Lesson Plan", st.session_state.artifacts["Lesson Plan"])

    with tab_vocab:
        display_artifact_box("Vocab", st.session_state.artifacts["Vocab"])

    with tab_worksheets:
        display_artifact_box("Worksheet", st.session_state.artifacts["Worksheet"])

    with tab_quizzes:
        display_artifact_box("Quiz", st.session_state.artifacts["Quiz"])

    with tab_tests:
        display_artifact_box("Test", st.session_state.artifacts["Test"])


def render_utility_hub():
    """Renders the original 27 feature selection UI."""
    st.header("👑 Utility Hub (27 Features)")
    st.caption("Select a category and feature in the sidebar to run a quick, stateless AI tool.")
    st.markdown("---")

    # Sidebar for category selection
    st.sidebar.header("Feature Categories")
    category_titles = list(UTILITY_FEATURES.keys())
    selected_category = st.sidebar.radio("Choose a Domain:", category_titles, index=0, key="hub_category_radio")

    # Get features for the selected category
    category_data = UTILITY_FEATURES[selected_category]
    features = list(category_data["features"].keys())

    st.subheader(f"{category_data['icon']} {selected_category}")

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

    if selected_feature != "Select a Feature to Use":
        st.markdown(f"##### Step 1: Provide Input Data")
        
        if image_needed:
            st.warning("⚠️ **Image Required!** Please upload your meal photo below.")
        
        example_prompt = category_data["features"][selected_feature]
        st.info(f"💡 **Example Input Format:** `{example_prompt}`")

        # 3. FILE UPLOADER (ONLY FOR CALORIE)
        if image_needed:
            uploaded_file = st.file_uploader(
                "Upload Meal Photo (Feature 9 Only)", 
                type=["jpg", "jpeg", "png"],
                key="hub_calorie_image_upload_area"
            )
            if uploaded_file:
                from PIL import Image
                st.image(Image.open(uploaded_file), caption="Meal to Analyze", width=250)
                
        # 4. TEXT AREA INPUT
        user_input = st.text_area(
            "Enter your required data:",
            value="" if not image_needed else "Estimate the calories and macros for this meal.",
            placeholder=example_prompt,
            key="hub_text_input"
        )

        # 5. EXECUTION BUTTON
        if st.button(f"EXECUTE: {selected_feature}", key="hub_execute_btn"):
            
            if image_needed and uploaded_file is None:
                st.error("Please upload an image to run the Image-to-Calorie Estimate.")
            else:
                final_prompt = f"{selected_feature}: {user_input}"
                
                with st.spinner(f'🎯 Routing request to **{selected_feature}**...'):
                    result = run_utility_hub(final_prompt, uploaded_file)
                    
                    st.session_state['hub_result'] = result
                    st.session_state['hub_last_feature_used'] = selected_feature
                
    # --- GLOBAL OUTPUT DISPLAY ---
    st.markdown("---")
    st.subheader("Hub Output")

    if 'hub_result' in st.session_state:
        st.markdown(f"##### Result for: **{st.session_state.hub_last_feature_used}**")
        st.code(st.session_state['hub_result'], language='markdown')


# --- 7. MAIN APPLICATION LOGIC ---

# 1. Initialize session and user state
initialize_user_session()

# 2. UI HEADER
st.title(f"👑 {WEBSITE_TITLE}: {CURRENT_APP_TITLE}")

# 3. SIDEBAR MODE SELECTOR (The core change)
st.sidebar.title(WEBSITE_TITLE) 
st.sidebar.markdown("---") 

st.sidebar.header("Application Mode")
mode_selection = st.sidebar.radio(
    "Select Interface:",
    ["Utility Hub (27 Features)", "Teacher's Aid (Curriculum Manager)"],
    key="mode_radio"
)
st.session_state.mode = mode_selection # Update state

st.sidebar.markdown("---")


# 4. RENDER THE CORRECT MODE
if st.session_state.mode == "Teacher's Aid (Curriculum Manager)":
    render_teachers_aid()
else:
    # If the user switches back, clear the TA state so they start fresh next time
    st.session_state.artifacts = {
        "Unit": [], "Lesson Plan": [], "Vocab": [], "Worksheet": [], "Quiz": [], "Test": []
    } 
    render_utility_hub()

# --- 7. FOOTER/DEBUG (Optional but helpful) ---
st.sidebar.markdown("---")
st.sidebar.caption(f"App ID: {app_id}")
st.sidebar.caption(f"User ID: {st.session_state.user_id[:8]}...")
