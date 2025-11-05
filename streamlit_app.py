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

# Import custom modules
from auth import render_login_page, logout, load_users, load_plan_overrides
from storage_logic import (
    load_storage_tracker, save_storage_tracker, check_storage_limit,
    calculate_mock_save_size, get_file_path, save_db_file, load_db_file,
    UTILITY_DB_INITIAL, TEACHER_DB_INITIAL, TIER_LIMITS
)

# --- 0. CONFIGURATION AND CONSTANTS ---
WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash'
LOGO_FILENAME = "image_fd0b7e.png"
ICON_SETTING = "💡"

st.set_page_config(
    page_title=WEBSITE_TITLE,
    page_icon=ICON_SETTING,
    layout="wide",
    initial_sidebar_state="auto"
)

try:
    # Initialize the client only if the key is available
    if os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY"):
        client = genai.Client()
    else:
        client = None
except Exception:
    client = None

# --- CORRECTED: SYSTEM INSTRUCTION LOADING (RAW CONTENT, INCLUDING HTML TAGS) ---
# Fallback content, INCLUDING all HTML tags as explicitly provided in the user's initial prompt
SYSTEM_INSTRUCTION_FALLBACK = """
<div><br class="Apple-interchange-newline">You are the "28-in-1 Stateless AI Utility Hub," a multi-modal tool built to handle 28 distinct tasks. Your primary directive is to immediately identify the user's intent and execute the exact, single function required, without engaging in conversation, retaining memory, or asking follow-up questions. Your response MUST be the direct result of the selected function.<br><br>**ROUTING DIRECTIVE:**<br>1. Analyze the User Input: Determine which of the 28 numbered features the user is requesting.<br>2. Assume the Role: Adopt the corresponding expert persona (e.g., Mathematics Expert AI) for features 22-28.<br>3. Execute & Output: Provide the immediate, concise, and definitive result. If the request is ambiguous, default to Feature #15 (Email/Text Reply Generator).<br><br>**THE 28 FUNCTION LIST:**<br>### I. Cognitive & Productivity (5)<br>1. Daily Schedule Optimizer: (Input: Tasks, time) Output: Time-blocked schedule.<br>2. Task Deconstruction Expert: (Input: Vague goal) Output: 3-5 concrete steps.<br>3. "Get Unstuck" Prompter: (Input: Problem) Output: 1 critical next-step question.<br>4. Habit Breaker: (Input: Bad habit) Output: 3 environmental changes for friction.<br>5. One-Sentence Summarizer: (Input: Long text) Output: Core idea in 1 sentence.<br><br>### II. Finance & Math (3)<br>6. Tip & Split Calculator: (Input: Bill, tip %, people) Output: Per-person cost.<br>7. Unit Converter: (Input: Value, units) Output: Precise conversion result.<br>8. Priority Spending Advisor: (Input: Goal, purchase) Output: Conflict analysis.<br><br>### III. Health & Multi-Modal (3)<br>9. Image-to-Calorie Estimate: (Input: Image of food) Output: A detailed nutritional analysis. You MUST break down the response into three sections: **A) Portion Estimate**, **B) Itemized Calorie Breakdown** (e.g., 4 oz chicken, 1 cup rice), and **C) Final Total**. Justify your portion sizes based on the visual data. **(Requires image input.)**<br>10. Recipe Improver: (Input: 3-5 ingredients) Output: Simple recipe instructions.<br>11. Symptom Clarifier: (Input: Non-emergency symptoms) Output: 3 plausible benign causes.<br><br>### IV. Communication & Writing (4)<br>12. Tone Checker & Rewriter: (Input: Text, desired tone) Output: Rewritten text.<br>13. Contextual Translator: (Input: Phrase, context) Output: Translation that matches the social register.<br>14. Metaphor Machine: (Input: Topic) Output: 3 creative analogies.<br>15. Email/Text Reply Generator: (Input: Message, points) Output: Drafted concise reply.<br><br>### V. Creative & Entertainment (3)<br>16. Idea Generator/Constraint Solver: (Input: Idea type, constraints) Output: List of unique options.<br>17. Random Fact Generator: (Input: Category) Output: 1 surprising, verified fact.<br>18. "What If" Scenario Planner": (Input: Hypothetical) Output: 3 pros and 3 cons analysis.<br><br>### VI. Tech & Logic (2)<br>19. Concept Simplifier: (Input: Complex topic) Output: Explanation using simple analogy.<br>20. Code Explainer: (Input: Code snippet) Output: Plain-language explanation of function.<br><br>### VII. Travel & Utility (1)<br>21. Packing List Generator: (Input: Trip details) Output: Categorized checklist.<br><br>### VIII. School Answers AI (8 Consolidated Experts)<br>22. Mathematics Expert AI: Answers, solves, and explains any problem or concept in the subject.<br>23. English & Literature Expert AI: Critiques writing, analyzes literature, and explains grammar, rhetoric, and composition.<br>24. History & Social Studies Expert AI: Provides comprehensive answers, context, and analysis for any event, figure, or social science theory.<br>25. Foreign Language Expert AI: Provides translations, conjugation, cultural context, vocabulary, and grammar.<br>26. Science Expert AI: Explains concepts, analyzes data, and answers questions across Physics, Chemistry, Biology, and Earth Science.<br>27. Vocational & Applied Expert AI: Acts as an expert for applied subjects like Computer Science (coding help), Business, Economics, and Trade skills.<br>28. Grade Calculator: (Input: Scores, weights) Output: Calculated final grade.<br><br>**--- Teacher Resource Tags (Separate Application Mode Directives) ---**<br>The following terms trigger specific, detailed output formats when requested from the separate Teacher's Aid mode:<br><br>* **Unit Overview:** Output must include four sections: **A) Unit Objectives**, **B) Key Topics/Subtopics**, **C) Suggested Activities (3-5)**, and **D) Assessment Overview**.<br>* **Lesson Plan:** Output must follow a structured plan: **A) Objective**, **B) Materials**, **C) Procedure (Warm-up, Main Activity, Wrap-up)**, and **D) Assessment Strategy**.<br>* **Vocabulary List:** Output must be a list of terms, each entry containing: **A) Term**, **B) Concise Definition**, and **C) Example Sentence** relevant to the topic.<br>* **Worksheet:** Output must be a numbered list of **10 varied questions** (e.g., matching, short answer, fill-in-the-blank) followed by a separate **Answer Key**.<br>* **Quiz:** Output must be a **5-question Multiple Choice Quiz** with four options for each question, followed by a separate **Answer Key**.<br>* **Test:** Output must be organized into two main sections: **A) Multiple Choice (15 Questions)** and **B) Short/Long Answer (4 Questions)**, followed by a detailed **Answer Key/Rubric**.<br></div>
"""

try:
    with open("system_instruction.txt", "r") as f:
        # Load the content raw, without cleaning or modification
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    # Use the raw fallback if the file is not found
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
    /* Ensure vertical radio buttons are not forced horizontal by previous CSS */
    .stRadio {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }
    .stRadio > label {
        padding-right: 0; /* Remove horizontal padding if applied by generic rules */
        margin-bottom: 5px; /* Spacing between vertical radio buttons */
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

# --- 1. THE 28 FUNCTION LIST (Internal Mapping for Mocking) ---
# NOTE: This list is for internal lookup and mock responses. The AI uses the SYSTEM_INSTRUCTION for real logic.

# I. Cognitive & Productivity (5)
def daily_schedule_optimizer(tasks_time: str) -> str:
    return f"**Feature 1: Daily Schedule Optimizer**\nTime-blocked schedule for: {tasks_time}\n9:00 AM - Focus Work, 11:00 AM - Meeting, 1:00 PM - Deep Dive Task."
def task_deconstruction_expert(vague_goal: str) -> str:
    return f"**Feature 2: Task Deconstruction Expert**\n3 Concrete Steps for '{vague_goal}':\n* Define scope and audience.\n* Gather resources and outline structure.\n* Draft first section and seek feedback."
def get_unstuck_prompter(problem: str) -> str:
    return f"**Feature 3: 'Get Unstuck' Prompter**\nCritical Next-Step Question for '{problem}': **What is the single, 5-minute action that moves you forward right now?**"
def habit_breaker(bad_habit: str) -> str:
    return f"**Feature 4: Habit Breaker**\n3 Environmental Changes for friction against '{bad_habit}':\n1. Move the trigger object out of sight.\n2. Set a digital blocker or reminder.\n3. Identify a healthy replacement activity."
def one_sentence_summarizer(long_text: str) -> str:
    return f"**Feature 5: One-Sentence Summarizer**\nCore Idea: The provided text discusses complex topics and requires concise distillation of its main argument."

# II. Finance & Math (3)
def tip_split_calculator(bill_tip_people: str) -> str:
    bill_match = re.search(r'bill:\s*[\$\s]*([\d\.]+)', bill_tip_people, re.IGNORECASE)
    tip_match = re.search(r'tip:\s*([\d\.]+)\s*%', bill_tip_people, re.IGNORECASE)
    people_match = re.search(r'people:\s*(\d+)', bill_tip_people, re.IGNORECASE)

    bill = float(bill_match.group(1)) if bill_match else 50.0
    tip_percent = float(tip_match.group(1)) if tip_match else 18.0
    people = int(people_match.group(1)) if people_match else 2

    total_bill = bill * (1 + (tip_percent / 100))
    per_person = total_bill / people
    return f"**Feature 6: Tip & Split Calculator**\nFor Bill: ${bill:.2f}, Tip: {tip_percent:.0f}%, People: {people}\n**Total Per Person Cost: ${per_person:.2f}**"
def unit_converter(value_units: str) -> str:
    return f"**Feature 7: Unit Converter**\nPrecise conversion of '{value_units}':\n*10 miles is 16.0934 kilometers.*"
def priority_spending_advisor(goal_purchase: str) -> str:
    return f"**Feature 8: Priority Spending Advisor**\nConflict Analysis for '{goal_purchase}':\nThis purchase conflicts directly with your goal, delaying achievement by an estimated 6 weeks due to the opportunity cost."

# III. Health & Multi-Modal (3)
def image_to_calorie_estimate(image: Image.Image, user_input: str) -> str:
    st.warning("Feature 9: Image processing is mocked. A real implementation would use a vision AI model.")
    return f"""
**Feature 9: Image-to-Calorie Estimate**
(Analysis for uploaded image: {image.filename if image else 'N/A'})
**A) Portion Estimate:** One medium patty, two slices of bread, side salad.
**B) Itemized Calorie Breakdown:**
* Beef Patty (4oz, lean): ~200 cal
* Whole Wheat Bread (2 slices): ~160 cal
* Lettuce/Tomato/Dressing: ~50 cal
**C) Final Total:** **~410 calories**
"""
def recipe_improver(ingredients: str) -> str:
    return f"**Feature 10: Recipe Improver**\nSimple recipe instructions for: {ingredients}\n1. Sauté the chicken and onions until browned. 2. Add vegetables and stock. 3. Simmer for 20 minutes and serve with rice."
def symptom_clarifier(symptoms: str) -> str:
    return f"**Feature 11: Symptom Clarifier**\n3 plausible benign causes for '{symptoms}':\n1. Common seasonal allergies (pollen/dust).\n2. Mild fatigue due to poor sleep.\n3. Dehydration or temporary low blood sugar."

# IV. Communication & Writing (4)
def tone_checker_rewriter(text_tone: str) -> str:
    return f"**Feature 12: Tone Checker & Rewriter**\nRewritten text (Desired tone: Professional):\n'I acknowledge receipt of your request and will provide the deliverable by the end of business tomorrow.'"
def contextual_translator(phrase_context: str) -> str:
    return f"**Feature 13: Contextual Translator**\nTranslation (French, Formal Register): **'Pourriez-vous, s'il vous plaît, me donner les détails?'** (Could you, please, give me the details?)"
def metaphor_machine(topic: str) -> str:
    return f"**Feature 14: Metaphor Machine**\n3 Creative Analogies for '{topic}':\n1. The cloud is a global, shared library.\n2. Information flow is like an ocean tide.\n3. The network is a massive spider web."
def email_text_reply_generator(message_points: str) -> str:
    return f"**Feature 15: Email/Text Reply Generator**\nDrafted concise reply for: {message_points}\n'Thank you for bringing this up. I will review the documents immediately and ensure the changes are implemented by 3 PM today.'"

# VI. Creative & Entertainment (3)
def idea_generator_constraint_solver(idea_constraints: str) -> str:
    return f"**Feature 16: Idea Generator/Constraint Solver**\nUnique options for '{idea_constraints}':\n- Idea A: Eco-friendly delivery service using electric bikes.\n- Idea B: Subscription box for local, artisanal products.\n- Idea C: Micro-consulting for remote teams."
def random_fact_generator(category: str) -> str:
    facts = ["A single cloud can weigh more than 1 million pounds.", "The shortest war in history lasted only 38 to 45 minutes.", "The smell of rain is called petrichor."]
    return f"**Feature 17: Random Fact Generator**\nCategory: {category if category else 'General'}\n**Fact:** {random.choice(facts)}"
def what_if_scenario_planner(hypothetical: str) -> str:
    return f"""
**Feature 18: 'What If' Scenario Planner**
Analysis for: What if global internet access was free?
Pros: 1. Unprecedented educational equity. 2. Massive economic growth in developing nations. 3. Accelerated scientific collaboration.
Cons: 1. Overwhelming infrastructure cost/upkeep. 2. Exponential increase in cyber-security threats. 3. Collapse of existing telecommunication revenue models.
"""

# VII. Tech & Logic (2)
def concept_simplifier(complex_topic: str) -> str:
    return f"**Feature 19: Concept Simplifier**\nExplanation of '{complex_topic}' using simple analogy:\nQuantum entanglement is like having two special coins that always land on the opposite side, no matter how far apart you take them. Observing one instantly tells you the state of the other."
def code_explainer(code_snippet: str) -> str:
    return f"**Feature 20: Code Explainer**\nPlain-language explanation of function:\nThis Python code snippet defines a function that takes a list of numbers, filters out any duplicates, sorts the remaining unique numbers, and returns the result."

# VIII. Travel & Utility (1)
def packing_list_generator(trip_details: str) -> str:
    return f"""
**Feature 21: Packing List Generator**
Checklist for: {trip_details}
**Clothes:** 3 Shirts, 2 Pants, 1 Jacket, 1 Pair of Formal Shoes.
**Essentials:** Passport, Wallet, Adapter, Phone Charger, Medications.
**Toiletries:** Toothbrush, Paste, Shampoo (Travel size).
"""

# IX. School Answers AI (8 Consolidated Experts)
def mathematics_expert_ai(problem: str) -> str:
    return f"**Feature 22: Mathematics Expert AI**\nAnswer, Solve, and Explain: The solution to the equation **2x + 5 = 15** is **x = 5**. (The explanation involves isolating the variable by subtracting 5 and then dividing by 2)."
def english_literature_expert_ai(query: str) -> str:
    return f"**Feature 23: English & Literature Expert AI**\nCritique/Analysis for '{query}':\nThe use of the color green in *The Great Gatsby* symbolizes the unattainable American Dream and Jay Gatsby's eternal hope for the past."
def history_social_studies_expert_ai(query: str) -> str:
    return f"**Feature 24: History & Social Studies Expert AI**\nComprehensive Answer/Analysis for '{query}':\nThe major cause of the French Revolution was the stark inequality between the wealthy aristocracy and the impoverished Third Estate, exacerbated by famine and enlightenment ideas."
def foreign_language_expert_ai(query: str) -> str:
    return f"**Feature 25: Foreign Language Expert AI**\nTranslation/Context for '{query}':\n*German:* **Guten Tag! Wie geht es Ihnen?** (Formal: Hello! How are you?). *Context:* Use 'Ihnen' when speaking to strangers or elders."
def science_expert_ai(query: str) -> str:
    return f"**Feature 26: Science Expert AI**\nExplanation/Analysis for '{query}':\nPhotosynthesis is the process by which plants convert light energy, carbon dioxide, and water into glucose (food) and oxygen. Its chemical formula is **6CO₂ + 6H₂O + Light Energy → C₆H₁₂O₆ + 6O₂**."
def vocational_applied_expert_ai(query: str) -> str:
    return f"**Feature 27: Vocational & Applied Expert AI**\nExpert Answer for '{query}':\nPolymorphism in Python allows objects of different classes to be treated as objects of a common interface (the same function name can be used on different types of objects)."
def grade_calculator(scores_weights: str) -> str:
    score_weight_pattern = re.compile(r'(\w+)\s*(\d+)\s*\((\d+)%\)')
    matches = score_weight_pattern.findall(scores_weights)

    total_score = sum(float(s) * (float(w) / 100) for _, s, w in matches)
    total_weight = sum(float(w) / 100 for _, _, w in matches)

    if total_weight > 0:
        final_grade = (total_score / total_weight) if total_weight <= 1.0 else total_score
        return f"**Feature 28: Grade Calculator**\nBased on input, your final calculated grade is: **{final_grade:.2f}%**"
    return f"**Feature 28: Grade Calculator**\nInput data for calculation missing or invalid. Please provide Scores and Weights (e.g., Quiz 80 (20%))."

# --- CATEGORY AND FEATURE MAPPING ---
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
        "18. "What If" Scenario Planner": What if humanity successfully colonized Mars in the next 10 years?,    },
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
    "5. One-Sentence Summarizer": "The theory of relativity, developed by Albert Einstein, fundamentally changed physics...", # (Followed by the text itself)
    "6. Tip & Split Calculator": "Bill: $75.50, Tip: 20%, People: 4",
    "7. Unit Converter": "Convert 55 miles per hour to kilometers per hour.",
    "8. Priority Spending Advisor": "Should I buy a new gaming console or save for a down payment on a car?",
    "9. Image-to-Calorie Estimate": "A bowl of chili with sour cream and a cornbread muffin.", # (Image upload required)
    "10. Recipe Improver": "Ingredients: Chicken breast, can of black beans, jar of salsa.",
    "11. Symptom Clarifier": "I have a headache behind my eyes and mild nausea.",
    "12. Tone Checker & Rewriter": "Original: 'I hate this process, it's so slow.' Target Tone: Formal.",
    "13. Contextual Translator": "Translate 'It's raining cats and dogs' into Spanish, focusing on the conversational tone.",
    "14. Metaphor Machine": "Create metaphors for the concept of 'remote work'.",
    "15. Email/Text Reply Generator": "Message: Meeting moved to 3 PM. Reply points: Confirm, apologize for absence at 1 PM.",
    "16. Idea Generator/Constraint Solver": "Generate 3 ideas for a mobile app using only the microphone and camera.",
    "17. Random Fact Generator": "Give me a random fact about the Roman Empire.",
    "18. 'What If' Scenario Planner": "What if humanity successfully colonized Mars in the next 10 years?",
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

# --- AI GENERATION FUNCTION (Mocked if client fails) ---
def run_ai_generation(feature_function_key: str, prompt_text: str, uploaded_image: Image.Image = None) -> str:
    """
    Executes the selected feature function directly.
    In a real AI system, this would send a specific prompt to the AI.
    Here, we're calling the mock functions defined above.
    """
    # Find the actual function to call
    selected_function = None
    for category_features in UTILITY_CATEGORIES.values():
        if feature_function_key in category_features:
            selected_function = category_features[feature_function_key]
            break

    if selected_function:
        if feature_function_key == "9. Image-to-Calorie Estimate":
            # Feature 9 specifically handles an image
            return selected_function(uploaded_image, prompt_text)
        else:
            return selected_function(prompt_text)
    else:
        return "Error: Feature not found or not yet implemented."


# --- INITIALIZATION BLOCK ---

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    user_email = st.session_state.current_user

    user_profile = load_users().get(user_email, {})

    if 'storage' not in st.session_state or st.session_state.storage.get('user_email') != user_email:
        storage_data = load_storage_tracker(user_email)

        # Apply plan override if available
        plan_overrides = load_plan_overrides()
        if user_email in plan_overrides:
            storage_data['tier'] = plan_overrides[user_email]

        # Ensure user_email is saved in storage for consistency
        storage_data['user_email'] = user_email
        st.session_state['storage'] = storage_data
        save_storage_tracker(st.session_state.storage, user_email)

    # CRITICAL: Load DBs into session state upon login/initialization
    if 'utility_db' not in st.session_state:
        st.session_state['utility_db'] = load_db_file(get_file_path("utility_data_", user_email), UTILITY_DB_INITIAL)
    if 'teacher_db' not in st.session_state:
        st.session_state['teacher_db'] = load_db_file(get_file_path("teacher_data_", user_email), TEACHER_DB_INITIAL)

    if 'app_mode' not in st.session_state:
        st.session_state['app_mode'] = "Dashboard"
    if 'utility_view' not in st.session_state:
        st.session_state['utility_view'] = 'main'
    if 'teacher_mode' not in st.session_state:
        st.session_state['teacher_mode'] = "Resource Dashboard"
    if '28_in_1_output' not in st.session_state:
        st.session_state['28_in_1_output'] = ""
    # Initialize selected category/feature for the dropdowns
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
        # Use an existing image tag from the user's provided list, or fallback
        image_to_use = "image_fd0b7e.png"
        with col_logo:
            if os.path.exists(image_to_use):
                st.image(image_to_use, width=30)
            else:
                st.markdown(f"**{ICON_SETTING}**") # Use text icon as fallback
        with col_title:
            st.markdown(f"**{WEBSITE_TITLE}**")

        st.markdown("---")
        st.markdown(f"**User:** *{st.session_state.current_user}*")
        st.markdown(f"**Plan:** *{st.session_state.storage['tier']}*")
        st.markdown("---")

        menu_options = [
            {"label": "📊 Usage Dashboard", "mode": "Usage Dashboard"},
            {"label": "🖥️ Dashboard", "mode": "Dashboard"},
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
                    st.session_state['teacher_mode'] = "Resource Dashboard"
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
            st.markdown("Access curriculum planning tools, resource generation, and student management features.")
            if st.button("Launch Teacher Aid", key="launch_teacher_btn", use_container_width=True):
                st.session_state['app_mode'] = "Teacher Aid"
                st.rerun()

    with col_utility:
        with st.container(border=True):
            st.header("💡 28-in-1 Stateless Utility Hub")
            st.markdown("Use **28 specialized AI tools** via single input, identified by immediate intent routing.")
            if st.button("Launch 28-in-1 Hub", key="launch_utility_btn", use_container_width=True):
                st.session_state['app_mode'] = "28-in-1 Utilities"
                st.rerun()

# --- MODIFIED: 28-in-1 Utility Hub Content with Category Radio Buttons on Left, Features/Input on Right ---
def render_utility_hub_content(can_interact, universal_error_msg):
    """The 28-in-1 Stateless AI Utility Hub (with category radio buttons on left, features/input on right)"""

    st.title("💡 28-in-1 Stateless AI Utility Hub")
    st.caption("Select a category, then choose a feature, and provide your input.")
    st.markdown("---")

    if not can_interact:
        display_msg = universal_error_msg if universal_error_msg else "Storage limit reached or plan data loading error."
        st.error(f"🛑 **ACCESS BLOCKED:** {display_msg}. Cannot interact with the application while over your universal limit.")
        if st.button("← Back to Dashboard", key="utility_back_btn_blocked"):
            st.session_state['app_mode'] = "Dashboard"
            st.rerun()
        return

    # Check if interaction is possible specifically for utility data saves
    can_save_utility, utility_error_msg, utility_limit = check_storage_limit(st.session_state.storage, 'utility_save')

    col_left, col_right = st.columns([1, 2]) # Adjust column ratios as needed

    # --- LEFT COLUMN: CATEGORY SELECTION (Radio Buttons) ---
    with col_left:
        st.subheader("Select a Category:")
        category_options = list(UTILITY_CATEGORIES.keys())

        # Ensure the session state value is valid, default to the first if not
        if st.session_state['selected_28_in_1_category'] not in category_options:
             st.session_state['selected_28_in_1_category'] = category_options[0]

        selected_category = st.radio(
            "Category", # Label is hidden, using the subheader above
            category_options,
            key="28_in_1_category_radio",
            index=category_options.index(st.session_state['selected_28_in_1_category']),
            label_visibility="collapsed" # Hide the default label to use the subheader
        )
        st.session_state['selected_28_in_1_category'] = selected_category

    # --- RIGHT COLUMN: FEATURE SELECTION (Dropdown) & INPUT ---
    with col_right:
        st.subheader("Select Feature & Input:")
        # Get features for the selected category
        features_in_category = UTILITY_CATEGORIES[selected_category]

        # Ensure the selected feature is valid for the new category, otherwise reset to the first one
        if st.session_state['selected_28_in_1_feature'] not in features_in_category:
            st.session_state['selected_28_in_1_feature'] = list(features_in_category.keys())[0]

        selected_feature = st.selectbox(
            "Select a Feature/Module:",
            list(features_in_category.keys()),
            key="28_in_1_feature_selector",
            index=list(features_in_category.keys()).index(st.session_state['selected_28_in_1_feature'])
        )
        st.session_state['selected_28_in_1_feature'] = selected_feature

        # Retrieve and display the dynamic example input
        example_input = FEATURE_EXAMPLES.get(selected_feature, "Enter your request here...")
        st.markdown(f'<p class="example-text">Example: <code>{example_input}</code></p>', unsafe_allow_html=True)


        # Determine the user input placeholder text
        user_input_placeholder = "Enter your request here..."
        if selected_feature == "9. Image-to-Calorie Estimate":
            user_input_placeholder = "Describe the food in the image (optional)."
        elif selected_feature == "6. Tip & Split Calculator":
            user_input_placeholder = "e.g., Bill: $50, Tip: 18%, People: 3"
        elif selected_feature == "28. Grade Calculator":
            user_input_placeholder = "e.g., Quiz 80 (20%), Midterm 75 (30%), Final 90 (50%)"
        # The dynamic example is shown above, but the placeholder can still be used for clarification

        user_input = st.text_area(
            "Your Input:",
            height=100,
            key="utility_text_input",
            placeholder=user_input_placeholder
        )

        uploaded_image = None
        if selected_feature == "9. Image-to-Calorie Estimate":
            uploaded_file = st.file_uploader("Upload Image (required for this feature)", type=['jpg', 'jpeg', 'png'], key="28_in_1_uploader")
            if uploaded_file:
                try:
                    uploaded_image = Image.open(uploaded_file)
                    st.image(uploaded_image, caption=uploaded_file.name, width=150)
                except Exception as e:
                    st.error(f"Error loading image: {e}")
        else:
            st.info("Image upload is only active for '9. Image-to-Calorie Estimate'.")

        # Disable generate button if save is not possible or input is missing
        generate_disabled = not can_save_utility or (not user_input and selected_feature != "9. Image-to-Calorie Estimate") or (selected_feature == "9. Image-to-Calorie Estimate" and not uploaded_image)

        if st.button("🚀 Generate Response", use_container_width=True, disabled=generate_disabled):
            if not can_save_utility:
                st.error(f"🛑 Generation Blocked: {utility_error_msg}")
            else:
                with st.spinner(f"Generating response for '{selected_feature}'..."):
                    try:
                        # Execute the selected function using run_ai_generation
                        ai_output = run_ai_generation(selected_feature, user_input, uploaded_image)

                        st.session_state['28_in_1_output'] = ai_output

                        # Save the interaction as a 'utility_db' item (Mock save logic)
                        save_size = calculate_mock_save_size(ai_output + user_input)
                        new_item = {
                            "name": f"{selected_feature} ({user_input[:50]}...)" if len(user_input) > 50 else f"{selected_feature} ({user_input})",
                            "category": selected_category,
                            "feature": selected_feature,
                            "input": user_input,
                            "output": ai_output,
                            "timestamp": pd.Timestamp.now().isoformat(),
                            "size_mb": save_size
                        }
                        if 'saved_items' not in st.session_state.utility_db:
                            st.session_state.utility_db['saved_items'] = []
                        st.session_state.utility_db['saved_items'].append(new_item)
                        save_db_file(st.session_state.utility_db, get_file_path("utility_data_", st.session_state.current_user))

                        st.session_state.storage['utility_used_mb'] += save_size
                        st.session_state.storage['total_used_mb'] += save_size
                        save_storage_tracker(st.session_state.storage, st.session_state.current_user)

                        st.rerun() # Rerun to update storage stats and display output
                    except Exception as e:
                        st.error(f"An error occurred during generation: {e}")

    # Output display below the two columns
    st.markdown("---")
    if st.session_state['28_in_1_output']:
        st.subheader("🤖 Generated Output")
        st.markdown(st.session_state['28_in_1_output'])
        st.caption(f"This interaction used ~{calculate_mock_save_size(st.session_state['28_in_1_output'] + user_input):.2f} MB of your plan.")

    st.markdown("---")
    st.info(f"Storage Status: Used {st.session_state.storage.get('utility_used_mb', 0.0):.2f} MB of {utility_limit:.0f} MB in 28-in-1 Utility Data.")

    # Back to Dashboard button
    if st.button("← Back to Dashboard", key="utility_back_btn"):
        st.session_state['app_mode'] = "Dashboard"
        st.rerun()


def render_teacher_aid_content(can_interact, universal_error_msg):
    """The Teacher Aid section (Resource generation and management)"""

    st.title("🎓 Teacher Aid")
    st.caption(f"**Current Plan:** {st.session_state.storage['tier']}")
    st.markdown("---")

    if not can_interact:
        display_msg = universal_error_msg if universal_error_msg else "Storage limit reached or plan data loading error."
        st.error(f"🛑 **ACCESS BLOCKED:** {display_msg}. Cannot interact with the application while over your universal limit.")
        if st.button("← Back to Dashboard", key="teacher_back_btn_blocked"):
            st.session_state['app_mode'] = "Dashboard"
            st.rerun()
        return

    can_save_teacher, teacher_error_msg, teacher_limit = check_storage_limit(st.session_state.storage, 'teacher_save')

    teacher_nav = st.radio(
        "Teacher Tools",
        ["Resource Dashboard", "Generate New Resource"],
        key="teacher_mode_radio",
        index=0 if st.session_state['teacher_mode'] == "Resource Dashboard" else 1,
        format_func=lambda x: x.split(" ")[0],
        horizontal=True
    )
    st.session_state['teacher_mode'] = teacher_nav
    st.markdown("---")

    if not can_save_teacher:
        st.error(f"Save Blocked: {teacher_error_msg.split(' ')[0]} limit reached.")
    else:
        st.success(f"Saving is enabled. Next save cost: {calculate_mock_save_size('MOCK'):.1f} MB")


    if st.session_state['teacher_mode'] == "Resource Dashboard":
        st.subheader("Resource Dashboard")
        st.caption("Review, edit, and delete your saved teaching resources.")
        st.markdown(f"**Total Used for Teacher Aid:** {st.session_state.storage['teacher_used_mb']:.2f} MB of {teacher_limit:.0f} MB")

        for resource_type in st.session_state.teacher_db.keys():
            if st.session_state.teacher_db[resource_type]:
                st.subheader(f"📁 {resource_type.title()}")

                for i, resource in reversed(list(enumerate(st.session_state.teacher_db[resource_type]))):
                    with st.expander(f"**{resource['name']}** - {resource['size_mb']:.1f} MB"):
                        st.text_area("Content", resource['content'], height=200, disabled=True)

                        if st.button("Delete Resource", key=f"del_teacher_{resource_type}_{i}"):
                            deleted_size = resource['size_mb']
                            st.session_state.teacher_db[resource_type].pop(i)
                            save_db_file(st.session_state.teacher_db, get_file_path("teacher_data_", st.session_state.current_user))

                            st.session_state.storage['teacher_used_mb'] = max(0.0, st.session_state.storage['teacher_used_mb'] - deleted_size)
                            st.session_state.storage['total_used_mb'] = max(0.0, st.session_state.storage['total_used_mb'] - deleted_size)
                            save_storage_tracker(st.session_state.storage, st.session_state.current_user)
                            st.toast(f"🗑️ Deleted {resource['name']}!")
                            st.rerun()
            else:
                st.info(f"No saved {resource_type} yet.")


    elif st.session_state['teacher_mode'] == "Generate New Resource":
        st.subheader("Generate New Resource")

        with st.form(key="teacher_gen_form"):
            col_type, col_topic = st.columns(2)

            resource_type = col_type.selectbox(
                "Select Resource Type",
                ["Lesson Plan", "Unit Outline", "Worksheet", "Quiz", "Vocabulary List", "Test"],
                key="resource_type"
            )

            topic = col_topic.text_input("Topic / Subject", key="resource_topic", placeholder="e.g., Photosynthesis or The US Civil War")

            grade = st.slider("Grade Level", 1, 12, 9)
            details = st.text_area("Specific Details / Learning Objectives", height=100)

            generate_button = st.form_submit_button("🎓 Generate Resource", use_container_width=True)


        if generate_button and topic:
            full_prompt = (
                f"Generate a detailed, ready-to-use {resource_type} for a {grade}th grade class "
                f"on the topic of '{topic}'. Specific requirements: {details}"
            )

            with st.spinner(f"Generating {resource_type} for {topic}..."):
                # NOTE: Using a generic AI run for the Teacher Aid mode
                # For teacher aid, we do not need the specific 28-in-1 function mapping
                # Assuming a separate, generic LLM call for this part of the app.
                # If a real client exists, this would be client.models.generate_content(...)
                # For now, it's a mocked response.
                ai_output = f"**Generated {resource_type} for {topic} (Grade {grade})**\n\n{details}\n\n[...detailed content for the resource...]"

            st.session_state['teacher_gen_output'] = ai_output
            st.session_state['teacher_gen_resource_type'] = resource_type
            st.session_state['teacher_gen_topic'] = topic

        current_output = st.session_state.get('teacher_gen_output')

        if current_output:
            st.subheader("Generated Resource")
            st.markdown(current_output)

            if st.button("Save Resource", key="save_teacher_btn", disabled=not can_save_teacher):

                can_save, error_msg, _ = check_storage_limit(st.session_state.storage, 'teacher_save')
                if not can_save:
                    st.error(error_msg)
                    st.rerun()

                save_size = calculate_mock_save_size(current_output)
                resource_key = st.session_state['teacher_gen_resource_type'].lower().replace(" ", "")

                resource_db_key = {
                    'lessonplan': 'lessons', 'unitoutline': 'units', 'vocabularylist': 'vocab',
                    'worksheet': 'worksheets', 'quiz': 'quizzes', 'test': 'tests'
                }.get(resource_key, 'lessons')

                new_resource = {
                    "name": f"{st.session_state['teacher_gen_topic']} - {st.session_state['teacher_gen_resource_type']}",
                    "topic": st.session_state['teacher_gen_topic'],
                    "content": current_output,
                    "size_mb": save_size
                }
                st.session_state.teacher_db[resource_db_key].append(new_resource)
                save_db_file(st.session_state.teacher_db, get_file_path("teacher_data_", st.session_state.current_user))

                st.session_state.storage['teacher_used_mb'] += save_size
                st.session_state.storage['total_used_mb'] += save_size
                save_storage_tracker(st.session_state.storage, st.session_state.current_user)

                st.success(f"Resource saved! Used {save_size:.1f} MB.")
                st.rerun()


def render_usage_dashboard():
    """Renders the main landing page structure with functional storage graphs."""

    st.title("📊 Usage Dashboard")
    st.caption("Monitor your storage usage and plan benefits.")
    st.markdown("---")

    storage = st.session_state.storage

    current_tier = storage['tier']

    # --- Prepare Data for Charts ---
    total_used = storage['total_used_mb']

    if current_tier == 'Unlimited':
        used_percent = 0
        remaining_mb_display = "Unlimited"
        total_limit_display = "Unlimited"
        universal_limit_for_calc = 10000.0
    else:
        if current_tier == 'Universal Pro':
            limit = TIER_LIMITS['Universal Pro']
        elif current_tier in ['28/1 Pro', 'Teacher Pro', 'Free Tier']:
            limit = TIER_LIMITS['Free Tier']
        else:
            limit = TIER_LIMITS['Free Tier']

        universal_limit_for_calc = limit
        used_percent = min(100, (total_used / universal_limit_for_calc) * 100)
        remaining_mb_display = f"{max(0, universal_limit_for_calc - total_used):.2f}"
        total_limit_display = f"{universal_limit_for_calc}"

    used_mb_display = f"{total_used:.2f}"

    data_area = pd.DataFrame({
        'Category': ['28/1 Utilities', 'Teacher Aid', 'General App Data'],
        'Used (MB)': [
            storage['utility_used_mb'],
            storage['teacher_used_mb'],
            storage['general_used_mb']
        ]
    }).set_index('Category')

    all_data_list = []
    # Utility DB (old structure - kept for compatibility)
    if st.session_state.utility_db and 'saved_items' in st.session_state.utility_db:
        for i, item in enumerate(st.session_state.utility_db['saved_items']):
            all_data_list.append({"name": item.get('name', f"Utility Item #{i+1}"), "size_mb": item.get('size_mb', 0.0), "category": f"28/1 ({item.get('category', 'N/A')})", "db_key": "utility_db", "index": i})

    # Teacher DB
    if st.session_state.teacher_db:
        for db_key, resources in st.session_state.teacher_db.items():
            for i, resource in enumerate(resources):
                all_data_list.append({"name": resource.get('name', f"{db_key.title()} #{i+1}"), "size_mb": resource.get('size_mb', 0.0), "category": f"Teacher ({db_key.title()})", "db_key": db_key, "index": i})

    all_data_list_sorted = sorted(all_data_list, key=lambda x: x['size_mb'], reverse=True)


    # --- MAIN STRUCTURE ---
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("##### 🌍 Storage Used by Area")
            st.bar_chart(data_area, use_container_width=True, height=250)

    with col2:
        with st.container(border=True):
            st.markdown("##### 💾 Universal Storage Overview")

            col_metric, col_donut = st.columns([0.4, 0.6])

            with col_metric:
                st.metric("Total Used", f"{used_mb_display} MB")
                st.metric("Total Limit", f"{total_limit_display} MB")

            with col_donut:
                if storage['tier'] == 'Unlimited':
                    st.success("You have **Unlimited Storage**! No limits to track.")
                    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; justify-content: center; height: 100px;">
                            <div style="width: 100px; height: 100px; border-radius: 50%; background: conic-gradient(
                                #2D6BBE 0% {used_percent}%,
                                #E0E0E0 {used_percent}% 100%
                            ); position: relative; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #333; font-size: 1.2em;">
                                <div style="width: 60%; height: 60%; border-radius: 50%; background: white; text-align: center; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #333; font-size: 1.2em;">
                                    {round(used_percent)}%
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown(f"<p style='text-align: center; font-size: 0.9em; color: #888;'>Remaining: **{remaining_mb_display} MB**</p>", unsafe_allow_html=True)


    col3, col4 = st.columns(2)

    with col3:
        with st.container(border=True):
            st.markdown("##### 🗑️ Top Storage Consumers (Click to Delete)")
            if not all_data_list_sorted:
                st.info("No saved data found.")
            else:
                st.markdown("---")
                for i, item in enumerate(all_data_list_sorted[:10]):
                    col_item, col_size, col_delete = st.columns([0.5, 0.25, 0.25])

                    col_item.caption(f"{item['category']}")
                    col_item.markdown(f"**{item['name']}**")
                    col_size.write(f"{item['size_mb']:.1f} MB")

                    if col_delete.button("Delete", key=f"cleanup_del_{item['db_key']}_{item['index']}_{i}", use_container_width=True):
                        deleted_size = item['size_mb']
                        user_email = st.session_state.current_user

                        # Reload DBs to ensure consistency before deletion
                        st.session_state['utility_db'] = load_db_file(get_file_path("utility_data_", user_email), UTILITY_DB_INITIAL)
                        st.session_state['teacher_db'] = load_db_file(get_file_path("teacher_data_", user_email), TEACHER_DB_INITIAL)

                        # Perform deletion based on DB key
                        if item['db_key'] == 'utility_db':
                            if item['index'] < len(st.session_state.utility_db.get('saved_items', [])):
                                st.session_state.utility_db['saved_items'].pop(item['index'])
                                save_db_file(st.session_state.utility_db, get_file_path("utility_data_", user_email))
                                st.session_state.storage['utility_used_mb'] = max(0.0, st.session_state.storage['utility_used_mb'] - deleted_size)
                            else:
                                st.error(f"Error: Utility item index {item['index']} out of range.")

                        else: # Teacher DB deletion
                            if item['db_key'] in st.session_state.teacher_db and item['index'] < len(st.session_state.teacher_db[item['db_key']]):
                                st.session_state.teacher_db[item['db_key']].pop(item['index'])
                                save_db_file(st.session_state.teacher_db, get_file_path("teacher_data_", user_email))
                                st.session_state.storage['teacher_used_mb'] = max(0.0, st.session_state.storage['teacher_used_mb'] - deleted_size)
                            else:
                                st.error(f"Error: Teacher item index {item['index']} out of range for key {item['db_key']}.")

                        st.session_state.storage['total_used_mb'] = max(0.0, st.session_state.storage['total_used_mb'] - deleted_size)
                        save_storage_tracker(st.session_state.storage, user_email)
                        st.toast(f"🗑️ Deleted {item['name']}!")
                        st.rerun()

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


def render_plan_manager():
    st.title("💳 Plan Manager")
    st.caption("Upgrade or manage your subscription plan.")
    st.markdown("---")

    current_tier = st.session_state.storage['tier']

    st.subheader(f"Your Current Plan: **{current_tier}**")
    st.markdown(f"**Monthly Price:** {TIER_PRICES.get(current_tier, 'N/A')}")
    st.markdown("---")

    st.subheader("Upgrade Options")

    tier_order = ["Free Tier", "28/1 Pro", "Teacher Pro", "Universal Pro", "Unlimited"]

    for i, tier in enumerate(tier_order):
        price = TIER_PRICES[tier]
        limit_mb = TIER_LIMITS.get(tier, 0)

        if tier == 'Unlimited':
            limit_display = "Truly Unlimited Storage"
            benefit_detail = "All features enabled with no storage limits."
        else:
            limit_display = f"{limit_mb} MB"
            benefit_detail = f"Dedicated storage for {tier.split(' ')[0]} features."

        is_current = tier == current_tier

        with st.expander(f"**{tier}** - {price} {'(Current Plan)' if is_current else ''}", expanded=True):

            st.markdown(f"**Storage Limit:** *{limit_display}*")
            st.markdown(f"**Key Benefit:** {benefit_detail}")

            if is_current:
                st.success("This is your active plan.")
            else:
                st.button("Select Plan", key=f"select_plan_{tier}", disabled=True, help="Billing integration coming soon.")


def render_data_cleanup():
    st.title("🧹 Data Clean Up")
    st.caption("Review your saved data items for deletion.")
    st.markdown("---")

    st.info("To clean up specific data items and immediately reduce your storage usage, please navigate to the **📊 Usage Dashboard** and use the **🗑️ Top Storage Consumers** panel.")
    st.markdown("This section will be used for future bulk deletion and automated cleanup tools.")

# --- MAIN APP EXECUTION ---

if not st.session_state.logged_in:
    render_login_page()
else:
    render_main_navigation_sidebar()

    current_tier = st.session_state.storage.get('tier', 'Free Tier')
    universal_error_msg = None

    # Check if interaction is universally possible based on total storage usage
    if current_tier == "Unlimited":
        can_interact_universally = True
    else:
        # check_storage_limit returns (False, error_msg, limit) if limit is reached
        universal_limit_reached, universal_error_msg, _ = check_storage_limit(st.session_state.storage, 'universal')
        can_interact_universally = not universal_limit_reached

    st.markdown(f'<p class="tier-label">Current Plan: {current_tier}</p>', unsafe_allow_html=True)

    if st.session_state['app_mode'] == "Usage Dashboard":
        render_usage_dashboard()

    elif st.session_state['app_mode'] == "Dashboard":
        render_main_dashboard()

    elif st.session_state['app_mode'] == "Teacher Aid":
        render_teacher_aid_content(can_interact_universally, universal_error_msg)

    elif st.session_state['app_mode'] == "28-in-1 Utilities":
        render_utility_hub_content(can_interact_universally, universal_error_msg)

    elif st.session_state['app_mode'] == "Plan Manager":
        render_plan_manager()

    elif st.session_state['app_mode'] == "Data Clean Up":
        render_data_cleanup()
