import streamlit as st
import os
import pandas as pd
from PIL import Image
from io import BytesIO
import json
import re
import random

# --- Ensure you have google-genai installed and configured if you want real AI calls ---
from google import genai
from google.genai.errors import APIError

# Import custom modules (Assuming these files exist and are correct)
from auth import render_login_page, logout, load_users, load_plan_overrides
from storage_logic import (
    load_storage_tracker, save_storage_tracker, check_storage_limit,
    calculate_mock_save_size, get_file_path, save_db_file, load_db_file,
    UTILITY_DB_INITIAL, TEACHER_DB_INITIAL, TIER_LIMITS
)

# --- 0. CONFIGURATION AND CONSTANTS ---
WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash'
LOGO_FILENAME = "image_ffd419.png" # Assuming this is the correct logo file name
ICON_SETTING = "💡"

st.set_page_config(
    page_title=WEBSITE_TITLE,
    page_icon=ICON_SETTING,
    layout="wide",
    initial_sidebar_state="auto"
)

# --- INITIALIZE GEMINI CLIENT ---
client = None # Default to None

try:
    # 1. Safely retrieve the API key first
    api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

    if api_key:
        # 2. Only proceed to configure and initialize if the key is found
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel(MODEL)
        # st.success("Gemini Client successfully initialized!") # Optional feedback for debugging
    else:
        # Key not found, client remains None. The warning will be shown in run_ai_generation.
        pass

except Exception as e:
    client = None
    # st.error(f"Gemini API Setup Error: {e}") # Optional detailed error for debugging

# --- END INITIALIZE GEMINI CLIENT ---


# --- SYSTEM INSTRUCTION LOADING (RAW CONTENT) ---
SYSTEM_INSTRUCTION_FALLBACK = """
<div><br class="Apple-interchange-newline">You are the "28-in-1 Stateless AI Utility Hub," a multi-modal tool built to handle 28 distinct tasks. Your primary directive is to immediately identify the user's intent and execute the exact, single function required, without engaging in conversation, retaining memory, or asking follow-up questions. Your response MUST be the direct result of the selected function.<br><br>**ROUTING DIRECTIVE:**<br>1. Analyze the User Input: Determine which of the 28 numbered features the user is requesting.<br>2. Assume the Role: Adopt the corresponding expert persona (e.g., Mathematics Expert AI) for features 22-28.<br>3. Execute & Output: Provide the immediate, concise, and definitive result. If the request is ambiguous, default to Feature #15 (Email/Text Reply Generator).<br><br>**THE 28 FUNCTION LIST:**<br>### I. Cognitive & Productivity (5)<br>1. Daily Schedule Optimizer: (Input: Tasks, time) Output: Time-blocked schedule.<br>2. Task Deconstruction Expert: (Input: Vague goal) Output: 3-5 concrete steps.<br>3. "Get Unstuck" Prompter: (Input: Problem) Output: 1 critical next-step question.<br>4. Habit Breaker: (Input: Bad habit) Output: 3 environmental changes for friction.<br>5. One-Sentence Summarizer: (Input: Long text) Output: Core idea in 1 sentence.<br><br>### II. Finance & Math (3)<br>6. Tip & Split Calculator: (Input: Bill, tip %, people) Output: Per-person cost.<br>7. Unit Converter: (Input: Value, units) Output: Precise conversion result.<br>8. Priority Spending Advisor: (Input: Goal, purchase) Output: Conflict analysis.<br><br>### III. Health & Multi-Modal (3)<br>9. Image-to-Calorie Estimate: (Input: Image of food) Output: A detailed nutritional analysis. You MUST break down the response into three sections: **A) Portion Estimate**, **B) Itemized Calorie Breakdown** (e.g., 4 oz chicken, 1 cup rice), and **C) Final Total**. Justify your portion sizes based on the visual data. **(Requires image input.)**<br>10. Recipe Improver: (Input: 3-5 ingredients) Output: Simple recipe instructions.<br>11. Symptom Clarifier: (Input: Non-emergency symptoms) Output: 3 plausible benign causes.<br><br>### IV. Communication & Writing (4)<br>12. Tone Checker & Rewriter: (Input: Text, desired tone) Output: Rewritten text.<br>13. Contextual Translator: (Input: Phrase, context) Output: Translation that matches the social register.<br>14. Metaphor Machine: (Input: Topic) Output: 3 creative analogies.<br>15. Email/Text Reply Generator: (Input: Message, points) Output: Drafted concise reply.<br><br>### V. Creative & Entertainment (3)<br>16. Idea Generator/Constraint Solver: (Input: Idea type, constraints) Output: List of unique options.<br>17. Random Fact Generator: (Input: Category) Output: 1 surprising, verified fact.<br>18. "What If" Scenario Planner": (Input: Hypothetical) Output: 3 pros and 3 cons analysis.<br><br>### VI. Tech & Logic (2)<br>19. Concept Simplifier: (Input: Complex topic) Output: Explanation using simple analogy.<br>20. Code Explainer: (Input: Code snippet) Output: Plain-language explanation of function.<br><br>### VII. Travel & Utility (1)<br>21. Packing List Generator: (Input: Trip details) Output: Categorized checklist.<br><br>### VIII. School Answers AI (8 Consolidated Experts)<br>22. Mathematics Expert AI: Answers, solves, and explains any problem or concept in the subject.<br>23. English & Literature Expert AI: Critiques writing, analyzes literature, and explains grammar, rhetoric, and composition.<br>24. History & Social Studies Expert AI: Provides comprehensive answers, context, and analysis for any event, figure, or social science theory.<br>25. Foreign Language Expert AI: Provides translations, conjugation, cultural context, vocabulary, and grammar.<br>26. Science Expert AI: Explains concepts, analyzes data, and answers questions across Physics, Chemistry, Biology, and Earth Science.<br>27. Vocational & Applied Expert AI: Acts as an expert for applied subjects like Computer Science (coding help), Business, Economics, and Trade skills.<br>28. Grade Calculator: (Input: Scores, weights) Output: Calculated final grade.<br><br>**--- Teacher Resource Tags (Separate Application Mode Directives) ---**<br>The following terms trigger specific, detailed output formats when requested from the separate Teacher's Aid mode:<br><br>* **Unit Overview:** Output must include four sections: **A) Unit Objectives**, **B) Key Topics/Subtopics**, **C) Suggested Activities (3-5)**, and **D) Assessment Overview**.<br>* **Lesson Plan:** Output must follow a structured plan: **A) Objective**, **B) Materials**, **C) Procedure (Warm-up, Main Activity, Wrap-up)**, and **D) Assessment Strategy**.<br>* **Vocabulary List:** Output must be a list of terms, each entry containing: **A) Term**, **B) Concise Definition**, and **C) Example Sentence** relevant to the topic.<br>* **Worksheet:** Output must be a numbered list of **10 varied questions** (e.g., matching, short answer, fill-in-the-blank) followed by a separate **Answer Key**.<br>* **Quiz:** Output must be a **5-question Multiple Choice Quiz** with four options for each question, followed by a separate **Answer Key**.<br>* **Test:** Output must be organized into two main sections: **A) Multiple Choice (15 Questions)** and **B) Short/Long Answer (4 Questions)**, followed by a detailed **Answer Key/Rubric**.<br></div>
"""

try:
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_FALLBACK
    st.warning("`system_instruction.txt` file not found. Using hardcoded fallback instructions.")


TIER_PRICES = {
    "Free Tier": "Free", "28/1 Pro": "$7/month", "Teacher Pro": "$7/month",
    "Universal Pro": "$12/month", "Unlimited": "$18/month"
}

# Apply custom CSS
st.markdown(
    """
    <style>
    .css-1d391kg {
        padding-top: 2rem;
    }
    .tier-label {
        font-size: 0.8em;
        color: #888;
        margin-top: -15px;
        margin-bottom: 20px;
    }
    .stRadio {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }
    .stRadio > label {
        padding-right: 0;
        margin-bottom: 5px;
    }
    .example-text {
        font-size: 0.8em;
        color: #555;
        margin-top: -5px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 1. THE 28 FUNCTION LIST (MOCK/EXAMPLE PLACEHOLDERS) ---
# NOTE: These mock functions are kept for the sake of code structure/data mapping, 
# but they are NOT used in run_ai_generation anymore.
def daily_schedule_optimizer(tasks_time: str) -> str:
    return f"**Feature 1: Daily Schedule Optimizer**\nTime-blocked schedule for: {tasks_time}"
def task_deconstruction_expert(vague_goal: str) -> str:
    return f"**Feature 2: Task Deconstruction Expert**\n3 Concrete Steps for '{vague_goal}':"
def get_unstuck_prompter(problem: str) -> str:
    return f"**Feature 3: 'Get Unstuck' Prompter**\nCritical Next-Step Question for '{problem}':"
def habit_breaker(bad_habit: str) -> str:
    return f"**Feature 4: Habit Breaker**\n3 Environmental Changes for friction against '{bad_habit}':"
def one_sentence_summarizer(long_text: str) -> str:
    return f"**Feature 5: One-Sentence Summarizer**\nCore Idea: {long_text}"
def tip_split_calculator(bill_tip_people: str) -> str:
    return f"**Feature 6: Tip & Split Calculator**\nCost per person calculated for: {bill_tip_people}"
def unit_converter(value_units: str) -> str:
    return f"**Feature 7: Unit Converter**\nPrecise conversion of '{value_units}':"
def priority_spending_advisor(goal_purchase: str) -> str:
    return f"**Feature 8: Priority Spending Advisor**\nConflict Analysis for '{goal_purchase}':"
def image_to_calorie_estimate(image: Image.Image, user_input: str) -> str:
    return f"**Feature 9: Image-to-Calorie Estimate**\nNutritional analysis for uploaded image and request: {user_input}"
def recipe_improver(ingredients: str) -> str:
    return f"**Feature 10: Recipe Improver**\nSimple recipe instructions for: {ingredients}"
def symptom_clarifier(symptoms: str) -> str:
    return f"**Feature 11: Symptom Clarifier**\n3 plausible benign causes for '{symptoms}':"
def tone_checker_rewriter(text_tone: str) -> str:
    return f"**Feature 12: Tone Checker & Rewriter**\nRewritten text (Desired tone): {text_tone}"
def contextual_translator(phrase_context: str) -> str:
    return f"**Feature 13: Contextual Translator**\nTranslation that matches social register for: {phrase_context}"
def metaphor_machine(topic: str) -> str:
    return f"**Feature 14: Metaphor Machine**\n3 Creative Analogies for '{topic}':"
def email_text_reply_generator(message_points: str) -> str:
    return f"**Feature 15: Email/Text Reply Generator**\nDrafted concise reply for: {message_points}"
def idea_generator_constraint_solver(idea_constraints: str) -> str:
    return f"**Feature 16: Idea Generator/Constraint Solver**\nUnique options for '{idea_constraints}':"
def random_fact_generator(category: str) -> str:
    return f"**Feature 17: Random Fact Generator**\nCategory: {category if category else 'General'}\nFact: A true random fact."
def what_if_scenario_planner(hypothetical: str) -> str:
    return f"**Feature 18: 'What If' Scenario Planner**\nAnalysis for: {hypothetical}"
def concept_simplifier(complex_topic: str) -> str:
    return f"**Feature 19: Concept Simplifier**\nExplanation of '{complex_topic}' using simple analogy."
def code_explainer(code_snippet: str) -> str:
    return f"**Feature 20: Code Explainer**\nPlain-language explanation of function for: {code_snippet}"
def packing_list_generator(trip_details: str) -> str:
    return f"**Feature 21: Packing List Generator**\nChecklist for: {trip_details}"
def mathematics_expert_ai(problem: str) -> str:
    return f"**Feature 22: Mathematics Expert AI**\nAnswer, Solve, and Explain: {problem}"
def english_literature_expert_ai(query: str) -> str:
    return f"**Feature 23: English & Literature Expert AI**\nCritique/Analysis for '{query}':"
def history_social_studies_expert_ai(query: str) -> str:
    return f"**Feature 24: History & Social Studies Expert AI**\nComprehensive Answer/Analysis for '{query}':"
def foreign_language_expert_ai(query: str) -> str:
    return f"**Feature 25: Foreign Language Expert AI**\nTranslation/Context for '{query}':"
def science_expert_ai(query: str) -> str:
    return f"**Feature 26: Science Expert AI**\nExplanation/Analysis for '{query}':"
def vocational_applied_expert_ai(query: str) -> str:
    return f"**Feature 27: Vocational & Applied Expert AI**\nExpert Answer for '{query}':"
def grade_calculator(scores_weights: str) -> str:
    return f"**Feature 28: Grade Calculator**\nCalculated final grade based on: {scores_weights}"


# --- CATEGORY AND FEATURE MAPPING ---
# Maps the UI selection to the function names (the AI uses the prompt content for routing)
UTILITY_CATEGORIES = {
    "Cognitive & Productivity": {
        "1. Daily Schedule Optimizer": daily_schedule_optimizer,
        "2. Task Deconstruction Expert": task_deconstruction_expert,
        "3. 'Get Unstuck' Prompter": get_unstuck_prompter,
        "4. Habit Breaker": habit_breaker,
        "5. One-Sentence Summarizer": one_sentence_summarizer,
    },
    "Finance & Math": {
        "6. Tip & Split Calculator": tip_split_calculator,
        "7. Unit Converter": unit_converter,
        "8. Priority Spending Advisor": priority_spending_advisor,
    },
    "Health & Multi-Modal": {
        "9. Image-to-Calorie Estimate": image_to_calorie_estimate,
        "10. Recipe Improver": recipe_improver,
        "11. Symptom Clarifier": symptom_clarifier,
    },
    "Communication & Writing": {
        "12. Tone Checker & Rewriter": tone_checker_rewriter,
        "13. Contextual Translator": contextual_translator,
        "14. Metaphor Machine": metaphor_machine,
        "15. Email/Text Reply Generator": email_text_reply_generator,
    },
    "Creative & Entertainment": {
        "16. Idea Generator/Constraint Solver": idea_generator_constraint_solver,
        "17. Random Fact Generator": random_fact_generator,
        '18. "What If" Scenario Planner': what_if_scenario_planner,
    },
    "Tech & Logic": {
        "19. Concept Simplifier": concept_simplifier,
        "20. Code Explainer": code_explainer,
    },
    "Travel & Utility": {
        "21. Packing List Generator": packing_list_generator,
    },
    "School Answers AI": {
        "22. Mathematics Expert AI": mathematics_expert_ai,
        "23. English & Literature Expert AI": english_literature_expert_ai,
        "24. History & Social Studies Expert AI": history_social_studies_expert_ai,
        "25. Foreign Language Expert AI": foreign_language_expert_ai,
        "26. Science Expert AI": science_expert_ai,
        "27. Vocational & Applied Expert AI": vocational_applied_expert_ai,
        "28. Grade Calculator": grade_calculator,
    }
}

# --- FEATURE EXAMPLE MAPPING ---
FEATURE_EXAMPLES = {
    "1. Daily Schedule Optimizer": "I have 4 hours for work, 1 hour for lunch, and need to read a report.",
    "2. Task Deconstruction Expert": "My goal is to 'start a small online business'.",
    "3. 'Get Unstuck' Prompter": "I can't figure out the opening paragraph for my essay.",
    "4. Habit Breaker": "I want to stop checking social media first thing in the morning.",
    "5. One-Sentence Summarizer": "The theory of relativity, developed by Albert Einstein, fundamentally changed physics...",
    "6. Tip & Split Calculator": "Bill: $75.50, Tip: 20%, People: 4",
    "7. Unit Converter": "Convert 55 miles per hour to kilometers per hour.",
    "8. Priority Spending Advisor": "Should I buy a new gaming console or save for a down payment on a car?",
    "9. Image-to-Calorie Estimate": "A bowl of chili with sour cream and a cornbread muffin.",
    "10. Recipe Improver": "Ingredients: Chicken breast, can of black beans, jar of salsa.",
    "11. Symptom Clarifier": "I have a headache behind my eyes and mild nausea.",
    "12. Tone Checker & Rewriter": "Original: 'I hate this process, it's so slow.' Target Tone: Formal.",
    "13. Contextual Translator": "Translate 'It's raining cats and dogs' into Spanish, focusing on the conversational tone.",
    "14. Metaphor Machine": "Create metaphors for the concept of 'remote work'.",
    "15. Email/Text Reply Generator": "Message: Meeting moved to 3 PM. Reply points: Confirm, apologize for absence at 1 PM.",
    "16. Idea Generator/Constraint Solver": "Generate 3 ideas for a mobile app using only the microphone and camera.",
    "17. Random Fact Generator": "Give me a random fact about the Roman Empire.",
    '18. "What If" Scenario Planner': "What if global internet access was free?",
    "19. Concept Simplifier": "Explain the basics of Blockchain technology to a 10-year-old.",
    "20. Code Explainer": "Explain this Python code: `def sum_list(x): return sum(x)`",
    "21. Packing List Generator": "I'm taking a 5-day business trip to Chicago in December.",
    "22. Mathematics Expert AI": "Solve for X: $3(x-4) = 9$. Show your steps.",
    "23. English & Literature Expert AI": "Analyze the theme of isolation in 'The Catcher in the Rye'.",
    "24. History & Social Studies Expert AI": "What were the primary economic effects of the Silk Road?",
    "25. Foreign Language Expert AI": "What is the polite way to ask for the bill in Japanese?",
    "26. Science Expert AI": "Describe the function of the Golgi apparatus in a cell.",
    "27. Vocational & Applied Expert AI": "Explain how to properly ground an electrical outlet.",
    "28. Grade Calculator": "Quiz 80 (20%), Midterm 75 (30%), Final 90 (50%)",
}

# --- AI GENERATION FUNCTION (MOCK LOGIC REMOVED) ---
def run_ai_generation(feature_function_key: str, prompt_text: str, uploaded_image: Image.Image = None) -> str:
    """
    Executes the selected feature function using the real Gemini API.
    All mock responses are removed, forcing an API call or an error.
    """

    # CRITICAL: If client is not initialized, return a clear error instead of a mock response.
    if client is None:
        return "🛑 **AI Client Error:** The Gemini API Key is not configured. Please set the **GEMINI_API_KEY** in your environment or Streamlit secrets to enable AI generation."

    try:
        contents = []
        if feature_function_key == "9. Image-to-Calorie Estimate" and uploaded_image:
            # Convert PIL Image to BytesIO for sending to Gemini
            img_byte_arr = BytesIO()
            uploaded_image.save(img_byte_arr, format=uploaded_image.format or 'PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # For the real API call, the image must be converted to a Part object
            contents.append(genai.types.Part.from_bytes(
                data=img_byte_arr,
                mime_type=uploaded_image.format.lower() if uploaded_image.format else "image/png"
            ))

        contents.append(prompt_text)

        # For GenerativeModel, system_instruction is part of generation_config
        generation_config = genai.types.GenerationConfig(
            system_instruction=SYSTEM_INSTRUCTION,
        )

        response = client.generate_content(
            contents=contents,
            generation_config=generation_config
        )
        return response.text

    except APIError as e:
        # Catch and display specific API errors
        return f"Gemini API Error: Could not complete request. Details: {e}"
    except Exception as e:
        # Catch any other unexpected errors
        return f"An unexpected error occurred during AI generation: {e}"


# --- INITIALIZATION BLOCK (CRITICAL FOR PERSISTENCE & ERROR FIXES) ---

# Check for 'logged_in' state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    user_email = st.session_state.current_user

    # --- Load Storage Tracker (Ensures Tier/User data is consistent) ---
    storage_data = load_storage_tracker(user_email)

    # Apply plan override if available
    plan_overrides = load_plan_overrides()
    if user_email in plan_overrides:
        storage_data['tier'] = plan_overrides[user_email]

    storage_data['user_email'] = user_email
    st.session_state['storage'] = storage_data
    save_storage_tracker(st.session_state.storage, user_email)


    # --- CRITICAL FIX: Load DBs and ensure structure on every run (Persistence) ---

    # 1. Utility DB
    db_file_path_utility = get_file_path("utility_data_", user_email)
    st.session_state['utility_db'] = load_db_file(db_file_path_utility, UTILITY_DB_INITIAL)

    if 'history' not in st.session_state['utility_db'] or not isinstance(st.session_state['utility_db']['history'], list):
         st.session_state['utility_db']['history'] = UTILITY_DB_INITIAL.get('history', [])

    # 2. Teacher DB
    db_file_path_teacher = get_file_path("teacher_data_", user_email)
    st.session_state['teacher_db'] = load_db_file(db_file_path_teacher, TEACHER_DB_INITIAL)

    if 'history' not in st.session_state['teacher_db'] or not isinstance(st.session_state['teacher_db']['history'], list):
         st.session_state['teacher_db']['history'] = TEACHER_DB_INITIAL.get('history', [])

    # --- Standard App State Initialization ---
    if 'app_mode' not in st.session_state:
        st.session_state['app_mode'] = "Dashboard"
    if '28_in_1_output' not in st.session_state:
        st.session_state['28_in_1_output'] = ""
    # Removed generic 'teacher_output' since outputs are now per tab
    if 'teacher_view' not in st.session_state: # Use this for teacher sub-view
        st.session_state['teacher_view'] = 'generation' 


    if 'selected_28_in_1_category' not in st.session_state:
        st.session_state['selected_28_in_1_category'] = list(UTILITY_CATEGORIES.keys())[0]
    if 'selected_28_in_1_feature' not in st.session_state:
        st.session_state['selected_28_in_1_feature'] = list(UTILITY_CATEGORIES[st.session_state['selected_28_in_1_category']].keys())[0]


# --- NAVIGATION RENDERER ---

def render_main_navigation_sidebar():
    """Renders the main navigation using Streamlit's sidebar for responsiveness."""
    with st.sidebar:
        # Logo and Title
        col_logo, col_title = st.columns([0.25, 0.75])
        image_to_use = LOGO_FILENAME
        with col_logo:
            if os.path.exists(image_to_use):
                st.image(image_to_use, width=30)
            else:
                st.markdown(f"**{ICON_SETTING}**")
        with col_title:
            st.markdown(f"**{WEBSITE_TITLE}**")

        st.markdown("---")
        st.markdown(f"**User:** *{st.session_state.current_user}*")
        st.markdown(f"**Plan:** *{st.session_state.storage['tier']}*")
        st.markdown("---")

        # CRITICAL FIX: Removed 28-in-1 and Teacher Aid from sidebar.
        menu_options = [
            {"label": "🖥️ Dashboard", "mode": "Dashboard"},
            {"label": "📊 Usage Dashboard", "mode": "Usage Dashboard"},
            {"label": "💳 Plan Manager", "mode": "Plan Manager"},
            {"label": "🧹 Data Clean Up", "mode": "Data Clean Up"},
            {"label": "🚪 Logout", "mode": "Logout"}
        ]

        for item in menu_options:
            mode = item["mode"]
            button_id = f"sidebar_nav_button_{mode.replace(' ', '_')}"

            if st.button(item["label"], key=button_id, use_container_width=True):
                if mode == "Logout":
                    logout()
                else:
                    st.session_state['app_mode'] = mode
                    st.rerun()


# --- APPLICATION PAGE RENDERERS ---

def render_main_dashboard():
    """Renders the split-screen selection for Teacher Aid and 28/1 Utilities."""
    st.title("🖥️ Main Dashboard")
    st.caption("Access your two main application suites: **Teacher Aid** or **28-in-1 Stateless Utility Hub**.")
    st.markdown("---")
    col_teacher, col_utility = st.columns(2)
    with col_teacher:
        with st.container(border=True):
            st.header("🎓 Teacher Aid")
            st.markdown("Access curriculum planning tools, resource generation, and saved resources.")
            if st.button("Launch Teacher Aid", key="launch_teacher_btn", use_container_width=True):
                st.session_state['app_mode'] = "Teacher Aid"
                st.session_state['teacher_view'] = 'generation' # Reset teacher view on launch
                st.rerun()

    with col_utility:
        with st.container(border=True):
            st.header("💡 28-in-1 Stateless Utility Hub")
            st.markdown("Use **28 specialized AI tools** via single input, identified by immediate intent routing.")
            if st.button("Launch 28-in-1 Hub", key="launch_utility_btn", use_container_width=True):
                st.session_state['app_mode'] = "28-in-1 Utilities"
                st.rerun()

def render_utility_hub_content(can_interact, universal_error_msg):
    """The 28-in-1 Stateless AI Utility Hub"""

    st.title("💡 28-in-1 Stateless AI Utility Hub")
    st.caption("Select a category, then choose a feature, and provide your input.")
    st.markdown("---")

    if not can_interact:
        display_msg = universal_error_msg if universal_error_msg else "Storage limit reached or plan data loading error."
        st.error(f"🛑 **ACCESS BLOCKED:** {display_msg}. Cannot interact with the application while over your universal limit.")
        return

    can_save_utility, utility_error_msg, utility_limit = check_storage_limit(st.session_state.storage, 'utility_save')

    col_left, col_right = st.columns([1, 2])

    # --- LEFT COLUMN: CATEGORY SELECTION ---
    with col_left:
        st.subheader("Select a Category:")
        category_options = list(UTILITY_CATEGORIES.keys())

        if st.session_state['selected_28_in_1_category'] not in category_options:
             st.session_state['selected_28_in_1_category'] = category_options[0]

        selected_category = st.radio(
            "Category",
            category_options,
            key="28_in_1_category_radio",
            index=category_options.index(st.session_state['selected_28_in_1_category']),
            label_visibility="collapsed"
        )
        st.session_state['selected_28_in_1_category'] = selected_category

    # --- RIGHT COLUMN: FEATURE SELECTION & INPUT ---
    with col_right:
        st.subheader("Select Feature & Input:")
        features_in_category = UTILITY_CATEGORIES[selected_category]

        if st.session_state['selected_28_in_1_feature'] not in features_in_category:
            st.session_state['selected_28_in_1_feature'] = list(features_in_category.keys())[0]

        selected_feature = st.selectbox(
            "Select a Feature/Module:",
            list(features_in_category.keys()),
            key="28_in_1_feature_selector",
            index=list(features_in_category.keys()).index(st.session_state['selected_28_in_1_feature'])
        )
        st.session_state['selected_28_in_1_feature'] = selected_feature

        example_input = FEATURE_EXAMPLES.get(selected_feature, "Enter your request here...")
        st.markdown(f'<p class="example-text">Example: <code>{example_input}</code></p>', unsafe_allow_html=True)


        user_input_placeholder = "Enter your request here..."
        if selected_feature == "9. Image-to-Calorie Estimate":
            user_input_placeholder = "Describe the food in the image and provide any specific details (e.g., '1 cup of rice with chicken')."

        needs_image = selected_feature == "9. Image-to-Calorie Estimate"

        uploaded_file = None
        uploaded_image = None
        if needs_image:
            uploaded_file = st.file_uploader(
                "Upload Image for Calorie Estimate (Feature 9 Only)",
                type=["png", "jpg", "jpeg"],
                key="28_in_1_image_uploader"
            )
            if uploaded_file:
                uploaded_image = Image.open(uploaded_file)
                st.image(uploaded_image, caption="Uploaded Image", use_column_width=False, width=150)


        prompt_input = st.text_area(
            "Your Request/Input:",
            placeholder=user_input_placeholder,
            height=150,
            key="28_in_1_prompt_input"
        )

        if st.button("Generate Result", key="28_in_1_generate_btn", use_container_width=True):
            if not prompt_input and not (needs_image and uploaded_image): # Ensure input or image for feature 9
                st.warning("Please enter a request or upload an image (for Feature 9).")
            else:
                with st.spinner(f"Running Feature: {selected_feature}..."):
                    
                    # CRITICAL: The prompt for the 28-in-1 hub includes the feature name 
                    # for the AI to correctly route the request based on the system instructions.
                    ai_prompt = f"Feature {selected_feature}: {prompt_input}"

                    generated_output = run_ai_generation(
                        feature_function_key=selected_feature,
                        prompt_text=ai_prompt,
                        uploaded_image=uploaded_image
                    )

                    st.session_state['28_in_1_output'] = generated_output

                    if can_save_utility:
                        data_to_save = {
                            "timestamp": pd.Timestamp.now().isoformat(),
                            "feature": selected_feature,
                            "input": prompt_input[:100] + "..." if len(prompt_input) > 100 else prompt_input,
                            "output_size_bytes": calculate_mock_save_size(generated_output),
                            "output_content": generated_output
                        }

                        st.session_state.utility_db['history'].append(data_to_save)
                        save_db_file(get_file_path("utility_data_", st.session_state.current_user), st.session_state.utility_db)

                        mock_size = data_to_save["output_size_bytes"]
                        st.session_state.storage['current_utility_storage'] += mock_size
                        st.session_state.storage['current_universal_storage'] += mock_size
                        save_storage_tracker(st.session_state.storage, st.session_state.current_user)

                        st.success(f"Result saved to Utility History (Mock Size: {mock_size} bytes).")
                    else:
                        st.error(f"⚠️ **Utility History Save Blocked:** {utility_error_msg}. Result is displayed below but not saved.")

        st.markdown("---")
        st.subheader("Output Result")
        st.markdown(st.session_state['28_in_1_output'])


# --- TEACHER AID RENDERERS (MODIFIED TO 6 TABS + HISTORY) ---
def render_teacher_aid_content(can_interact, universal_error_msg):
    st.title("🎓 Teacher Aid Hub")
    st.caption("Generate specialized educational resources using the six dedicated tabs below.")
    st.markdown("---")

    if not can_interact:
        st.error(f"🛑 **ACCESS BLOCKED:** {universal_error_msg}. Cannot interact.")
        return

    # Pass the save check results to the generation tab
    can_save_teacher, teacher_error_msg, teacher_limit = check_storage_limit(st.session_state.storage, 'teacher_save')

    # Use Streamlit Tabs for the requested layout (6 resource tabs + History)
    tab_unit, tab_lesson, tab_vocab, tab_worksheet, tab_quiz, tab_test, tab_history = st.tabs(
        ["Unit Overview", "Lesson Plan", "Vocabulary List", "Worksheet", "Quiz", "Test", "📚 Saved History"]
    )

    # Define a helper function to render each resource tab
    def render_resource_tab(tab_container, resource_type, example_prompt):
        with tab_container:
            st.subheader(f"Generate {resource_type}")
            st.markdown(f'<p class="example-text">Example: <code>{example_prompt}</code></p>', unsafe_allow_html=True)
            
            prompt_key = f"teacher_prompt_{resource_type.lower().replace(' ', '_')}"
            button_key = f"teacher_generate_btn_{resource_type.lower().replace(' ', '_')}"
            output_key = f"teacher_output_{resource_type.lower().replace(' ', '_')}"

            # Initialize output for persistence
            if output_key not in st.session_state:
                st.session_state[output_key] = f"Your generated {resource_type} will appear here."

            teacher_prompt = st.text_area(
                "Topic/Details:",
                placeholder=example_prompt,
                height=150,
                key=prompt_key
            )

            if st.button(f"Generate {resource_type}", key=button_key, use_container_width=True):
                if not teacher_prompt:
                    st.warning("Please enter a topic or details for the resource.")
                    return

                # CRITICAL: Prepend the Resource Tag to the prompt for AI routing
                # The resource tag is what the SYSTEM_INSTRUCTION.txt uses to format the output.
                full_ai_prompt = f"{resource_type}: {teacher_prompt}"
                feature_key_proxy = "Teacher_Aid_Routing" # Proxy key, the AI uses the full_ai_prompt

                with st.spinner(f"Generating specialized {resource_type}..."):
                    generated_output = run_ai_generation(
                        feature_function_key=feature_key_proxy,
                        prompt_text=full_ai_prompt,
                        uploaded_image=None
                    )
                    st.session_state[output_key] = generated_output
                    
                    if can_save_teacher:
                        data_to_save = {
                            "timestamp": pd.Timestamp.now().isoformat(),
                            "resource_type": resource_type,
                            "request": teacher_prompt[:100] + "..." if len(teacher_prompt) > 100 else teacher_prompt,
                            "output_size_bytes": calculate_mock_save_size(generated_output),
                            "output_content": generated_output
                        }

                        st.session_state.teacher_db['history'].append(data_to_save)
                        save_db_file(get_file_path("teacher_data_", st.session_state.current_user), st.session_state.teacher_db)

                        mock_size = data_to_save["output_size_bytes"]
                        st.session_state.storage['current_teacher_storage'] += mock_size
                        st.session_state.storage['current_universal_storage'] += mock_size
                        save_storage_tracker(st.session_state.storage, st.session_state.current_user)

                        st.success(f"Resource saved to History (Mock Size: {mock_size} bytes).")
                    else:
                        st.error(f"⚠️ **History Save Blocked:** {teacher_error_msg}. Result is displayed below but not saved.")

            st.markdown("---")
            st.subheader(f"Generated {resource_type} Output")
            st.markdown(st.session_state[output_key])


    # Render all 6 resource tabs
    render_resource_tab(tab_unit, "Unit Overview", "High school physics unit on Newton's Laws of Motion.")
    render_resource_tab(tab_lesson, "Lesson Plan", "A 50-minute lesson plan for middle school students learning about the water cycle.")
    render_resource_tab(tab_vocab, "Vocabulary List", "Generate 10 key terms for a 10th-grade class studying the novel '1984'.")
    render_resource_tab(tab_worksheet, "Worksheet", "A 10-question mixed-format worksheet on basic algebra: solving for x, and simple inequalities.")
    render_resource_tab(tab_quiz, "Quiz", "A 5-question multiple choice quiz for 5th graders on world geography, capitals and continents.")
    render_resource_tab(tab_test, "Test", "A comprehensive test for a college-level introduction to macroeconomics (supply/demand, GDP, inflation).")


    # Render the History Tab (identical to uploaded file's logic)
    with tab_history:
        st.subheader("Teacher Aid Saved History")
        teacher_df = pd.DataFrame(st.session_state.teacher_db['history'])
        if not teacher_df.empty:
            # Add 'resource_type' column if not present (only for old mock data compatibility)
            if 'resource_type' not in teacher_df.columns:
                teacher_df['resource_type'] = teacher_df['request'].apply(lambda x: x.split(':')[0].strip() if ':' in x else 'Generic')
            
            # Drop the 'output_content' column for the main table view to keep it clean
            display_df = teacher_df.drop(columns=['output_content'], errors='ignore')
            st.dataframe(display_df.sort_values(by='timestamp', ascending=False), use_container_width=True)
            
            # Display detailed view for selected item (optional, but good practice)
            selected_row_index = st.selectbox("Select History Item for Full Content View:", teacher_df.index, format_func=lambda i: f"[{i+1}] {teacher_df.loc[i, 'request']}", key="teacher_history_selector")
            
            if selected_row_index is not None and not teacher_df.empty:
                st.markdown("---")
                st.subheader("Full Resource Content")
                st.markdown(teacher_df.loc[selected_row_index, 'output_content'])
        else:
            st.info("No teacher resources have been saved yet.")


# --- USAGE DASHBOARD RENDERER (GRAPHS RESTORED) ---
def render_usage_dashboard():
    st.title("📊 Usage Dashboard")
    st.markdown("---")
    st.subheader(f"Current Plan: {st.session_state.storage['tier']} ({TIER_PRICES.get(st.session_state.storage['tier'], 'N/A')})")

    # --- RESTORED USAGE GRAPHS (Progress Bars) ---
    st.markdown("### Storage Usage")

    storage_data = st.session_state.storage
    tier = storage_data['tier']

    # 1. Universal Storage
    current_uni = storage_data.get('current_universal_storage', 0)
    limit_uni_raw = TIER_LIMITS.get(tier, {}).get('universal_storage_limit_bytes', 0)
    
    if limit_uni_raw == float('inf'):
        uni_percent = 0.0 # Display 0% progress for unlimited, but show usage
        uni_limit_display = "Unlimited"
    else:
        uni_limit_display = f"{int(limit_uni_raw):,}"
        uni_percent = min(1.0, current_uni / limit_uni_raw) if limit_uni_raw > 0 else 0.0

    st.progress(uni_percent, text=f"**Universal Storage:** {current_uni:,} / {uni_limit_display} Bytes")

    # 2. Utility Storage
    current_utility = storage_data.get('current_utility_storage', 0)
    limit_utility_raw = TIER_LIMITS.get(tier, {}).get('utility_save_limit_bytes', 0)
    
    if limit_utility_raw == float('inf'):
        utility_percent = 0.0
        utility_limit_display = "Unlimited"
    else:
        utility_limit_display = f"{int(limit_utility_raw):,}"
        utility_percent = min(1.0, current_utility / limit_utility_raw) if limit_utility_raw > 0 else 0.0

    st.progress(utility_percent, text=f"**28-in-1 Utility History:** {current_utility:,} / {utility_limit_display} Bytes")

    # 3. Teacher Storage
    current_teacher = storage_data.get('current_teacher_storage', 0)
    limit_teacher_raw = TIER_LIMITS.get(tier, {}).get('teacher_save_limit_bytes', 0)
    
    if limit_teacher_raw == float('inf'):
        teacher_percent = 0.0
        teacher_limit_display = "Unlimited"
    else:
        teacher_limit_display = f"{int(limit_teacher_raw):,}"
        teacher_percent = min(1.0, current_teacher / limit_teacher_raw) if limit_teacher_raw > 0 else 0.0

    st.progress(teacher_percent, text=f"**Teacher Aid History:** {current_teacher:,} / {teacher_limit_display} Bytes")
    
    # 4. File Storage (Placeholder/Mock - using Teacher limit for size tracking example)
    current_file = storage_data.get('current_file_storage', 0)
    limit_file_raw = TIER_LIMITS.get(tier, {}).get('file_upload_limit_bytes', 0)
    
    if limit_file_raw == float('inf'):
        file_percent = 0.0
        file_limit_display = "Unlimited"
    else:
        file_limit_display = f"{int(limit_file_raw):,}"
        file_percent = min(1.0, current_file / limit_file_raw) if limit_file_raw > 0 else 0.0

    st.progress(file_percent, text=f"**File Uploads/Images:** {current_file:,} / {file_limit_display} Bytes")
    
    st.markdown("---")
    
    # --- History Tables (The content that was NOT deleted) ---
    st.subheader("Utility History (Last 5 Saves)")
    utility_df = pd.DataFrame(st.session_state.utility_db['history'])
    if not utility_df.empty:
        st.dataframe(utility_df[['timestamp', 'feature', 'input', 'output_size_bytes']].tail(5).sort_values(by='timestamp', ascending=False), use_container_width=True)
    else:
        st.info("No utility history saved yet.")


# --- PLAN MANAGER RENDERER (CONTENT RESTORED) ---
def render_plan_manager():
    st.title("💳 Plan Manager")
    st.markdown("---")
    st.subheader(f"Your Current Plan: **{st.session_state.storage['tier']}**")
    st.markdown(f"Price: **{TIER_PRICES.get(st.session_state.storage['tier'], 'N/A')}**")

    st.markdown("### Choose a New Plan")

    col1, col2, col3, col4, col5 = st.columns(5)
    
    plans_list = ["Free Tier", "28/1 Pro", "Teacher Pro", "Universal Pro", "Unlimited"]
    cols = [col1, col2, col3, col4, col5]

    for i, plan in enumerate(plans_list):
        with cols[i]:
            with st.container(border=True):
                st.header(plan)
                price = TIER_PRICES[plan]
                st.markdown(f"**{price}**")
                
                # Dynamic feature descriptions (simplified)
                if "Pro" in plan:
                    st.markdown("✅ Enhanced Storage")
                    if "28/1" in plan:
                        st.markdown("✅ **28-in-1** Access")
                        st.markdown("❌ Teacher Aid")
                    elif "Teacher" in plan:
                        st.markdown("❌ 28-in-1 Access")
                        st.markdown("✅ **Teacher Aid**")
                    elif "Universal" in plan:
                        st.markdown("✅ Both Suites")
                        st.markdown("✅ Dedicated Support")
                elif plan == "Unlimited":
                    st.markdown("🌟 Everything")
                    st.markdown("🚀 Infinite Storage")
                else:
                    st.markdown("Basic Access")
                    st.markdown("Limited Storage")

                
                if plan == st.session_state.storage['tier']:
                    st.button("Current Plan", key=f"plan_current_{plan.replace(' ', '_')}", use_container_width=True, disabled=True)
                else:
                    # Restore the clickable interaction
                    if st.button(f"Select {plan}", key=f"plan_select_{plan.replace(' ', '_')}", use_container_width=True):
                        st.session_state.storage['tier'] = plan
                        # NOTE: In a real app, this would trigger a payment gateway.
                        st.success(f"Successfully selected the {plan}! (A full implementation would now process payment).")
                        save_storage_tracker(st.session_state.storage, st.session_state.current_user)
                        st.rerun()


# --- DATA CLEAN UP RENDERER ---
def render_data_clean_up():
    st.title("🧹 Data Clean Up")
    st.markdown("---")
    st.warning("Deleting data is permanent. Use with caution.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Wipe Utility History", key="wipe_utility_btn", use_container_width=True):
            st.session_state.utility_db['history'] = UTILITY_DB_INITIAL['history']
            save_db_file(get_file_path("utility_data_", st.session_state.current_user), st.session_state.utility_db)

            utility_size_cleared = st.session_state.storage.get('current_utility_storage', 0)
            st.session_state.storage['current_utility_storage'] = 0
            st.session_state.storage['current_universal_storage'] -= utility_size_cleared
            # Ensure universal storage doesn't go below zero
            if st.session_state.storage['current_universal_storage'] < 0:
                st.session_state.storage['current_universal_storage'] = 0
            save_storage_tracker(st.session_state.storage, st.session_state.current_user)

            st.success("Utility History has been reset and storage cleared.")
            st.rerun() # Rerun to update dashboard immediately

    with col2:
        if st.button("Wipe Teacher History", key="wipe_teacher_btn", use_container_width=True):
            st.session_state.teacher_db['history'] = TEACHER_DB_INITIAL['history']
            save_db_file(get_file_path("teacher_data_", st.session_state.current_user), st.session_state.teacher_db)

            teacher_size_cleared = st.session_state.storage.get('current_teacher_storage', 0)
            st.session_state.storage['current_teacher_storage'] = 0
            st.session_state.storage['current_universal_storage'] -= teacher_size_cleared
            # Ensure universal storage doesn't go below zero
            if st.session_state.storage['current_universal_storage'] < 0:
                st.session_state.storage['current_universal_storage'] = 0
            save_storage_tracker(st.session_state.storage, st.session_state.current_user)

            st.success("Teacher History has been reset and storage cleared.")
            st.rerun() # Rerun to update dashboard immediately


# --- MAIN APPLICATION LOGIC ---

if not st.session_state.logged_in:
    render_login_page()
else:
    # --- 1. Navigation ---
    render_main_navigation_sidebar()

    # Check universal access based on storage limits
    can_interact, universal_error_msg, _ = check_storage_limit(st.session_state.storage, 'universal_storage')

    # --- 2. Content Routing ---
    if st.session_state.app_mode == "Dashboard":
        render_main_dashboard()

    elif st.session_state.app_mode == "28-in-1 Utilities":
        render_utility_hub_content(can_interact, universal_error_msg)

    elif st.session_state.app_mode == "Teacher Aid":
        render_teacher_aid_content(can_interact, universal_error_msg)

    elif st.session_state.app_mode == "Usage Dashboard":
        render_usage_dashboard()

    elif st.session_state.app_mode == "Plan Manager":
        render_plan_manager()

    elif st.session_state.app_mode == "Data Clean Up":
        render_data_clean_up()
