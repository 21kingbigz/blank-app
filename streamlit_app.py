import streamlit as st
import os
import pandas as pd
from PIL import Image
from io import BytesIO
import json
import re
import random
import traceback # Import traceback for detailed error logging

# --- CRITICAL FIX: Robust Imports for Gemini SDK ---
import google.generativeai as genai

# Attempt to import necessary components from their most likely locations,
# providing fallbacks in case of version mismatch/conflicts.

try:
    from google.generativeai import APIError # Primary location
except ImportError:
    try:
        from google.generativeai.errors import APIError # Secondary location
    except ImportError:
        # Fallback: Define a generic exception to allow the rest of the code to function
        class APIError(Exception):
            """Generic fallback for missing APIError class."""
            pass

try:
    from google.generativeai.types import GenerationConfig
except ImportError:
    # Fallback: Define a mock class if the official one is not found
    class GenerationConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    st.warning("⚠️ Could not import 'GenerationConfig'. Using a mock class.")


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

# --- SYSTEM INSTRUCTION LOADING (RAW CONTENT) ---
# CRITICAL FIX: This block MUST come before the Gemini Client Initialization.
SYSTEM_INSTRUCTION_FALLBACK = """
<div><br class="Apple-interchange-newline">You are the "28-in-1 Stateless AI Utility Hub," a multi-modal tool built to handle 28 distinct tasks. Your primary directive is to immediately identify the user's intent and execute the exact, single function required, without engaging in conversation, retaining memory, or asking follow-up questions. Your response MUST be the direct result of the selected function.<br><br>**ROUTING DIRECTIVE:**<br>1. Analyze the User Input: Determine which of the 28 numbered features the user is requesting.<br>2. Assume the Role: Adopt the corresponding expert persona (e.g., Mathematics Expert AI) for features 22-28.<br>3. Execute & Output: Provide the immediate, concise, and definitive result. If the request is ambiguous, default to Feature #15 (Email/Text Reply Generator).<br><br>**THE 28 FUNCTION LIST:**<br>### I. Cognitive & Productivity (5)<br>1. Daily Schedule Optimizer: (Input: Tasks, time) Output: Time-blocked schedule.<br>2. Task Deconstruction Expert: (Input: Vague goal) Output: 3-5 concrete steps.<br>3. "Get Unstuck" Prompter: (Input: Problem) Output: 1 critical next-step question.<br>4. Habit Breaker: (Input: Bad habit) Output: 3 environmental changes for friction.<br>5. One-Sentence Summarizer: (Input: Long text) Output: Core idea in 1 sentence.<br><br>### II. Finance & Math (3)<br>6. Tip & Split Calculator: (Input: Bill, tip %, people) Output: Per-person cost.<br>7. Unit Converter: (Input: Value, units) Output: Precise conversion result.<br>8. Priority Spending Advisor: (Input: Goal, purchase) Output: Conflict analysis.<br><br>### III. Health & Multi-Modal (3)<br>9. Image-to-Calorie Estimate: (Input: Image of food) Output: A detailed nutritional analysis. You MUST break down the response into three sections: **A) Portion Estimate**, **B) Itemized Calorie Breakdown** (e.g., 4 oz chicken, 1 cup rice), and **C) Final Total**. Justify your portion sizes based on the visual data. **(Requires image input.)**<br>10. Recipe Improver: (Input: 3-5 ingredients) Output: Simple recipe instructions.<br>11. Symptom Clarifier: (Input: Non-emergency symptoms) Output: 3 plausible benign causes.<br><br>### IV. Communication & Writing (4)<br>12. Tone Checker & Rewriter: (Input: Text, desired tone) Output: Rewritten text.<br>13. Contextual Translator: (Input: Phrase, context) Output: Translation that matches the social register.<br>14. Metaphor Machine: (Input: Topic) Output: 3 creative analogies.<br>15. Email/Text Reply Generator: (Input: Message, points) Output: Drafted concise reply.<br><br>### V. Creative & Entertainment (3)<br>16. Idea Generator/Constraint Solver: (Input: Idea type, constraints) Output: List of unique options.<br>17. Random Fact Generator: (Input: Category) Output: 1 surprising, verified fact.<br>18. "What If" Scenario Planner": (Input: Hypothetical) Output: 3 pros and 3 cons analysis.<br><br>### VI. Tech & Logic (2)<br>19. Concept Simplifier: (Input: Complex topic) Output: Explanation using simple analogy.<br>20. Code Explainer: (Input: Code snippet) Output: Plain-language explanation of function.<br><br>### VII. Travel & Utility (1)<br>21. Packing List Generator: (Input: Trip details) Output: Categorized checklist.<br><br>### VIII. School Answers AI (8 Consolidated Experts)<br>22. Mathematics Expert AI: Answers, solves, and explains any problem or concept in the subject.<br>23. English & Literature Expert AI: Critiques writing, analyzes literature, and explains grammar, rhetoric, and composition.<br>24. History & Social Studies Expert AI: Provides comprehensive answers, context, and analysis for any event, figure, or social science theory.<br>25. Foreign Language Expert AI: Provides translations, conjugation, cultural context, vocabulary, and grammar.<br>26. Science Expert AI: Explains concepts, analyzes data, and answers questions across Physics, Chemistry, Biology, and Earth Science.<br>27. Vocational & Applied Expert AI: Acts as an expert for applied subjects like Computer Science (coding help), Business, Economics, and Trade skills.<br>28. Grade Calculator: (Input: Scores, weights) Output: Calculated final grade.<br><br>**--- Teacher Resource Tags (Separate Application Mode Directives) ---**<br>The following terms trigger specific, detailed output formats when requested from the separate Teacher's Aid mode:<br><br>* **Unit Overview:** Output must include four sections: **A) Unit Objectives**, **B) Key Topics/Subtopics**, **C) Suggested Activities (3-5)**, and **D) Assessment Overview**.<br>* **Lesson Plan:** Output must follow a structured plan: **A) Objective**, **B) Materials**, **C) Procedure (Warm-up, Main Activity, Wrap-up)**, and **D) Assessment Strategy**.<br>* **Vocabulary List:** Output must be a list of terms, each entry containing: **A) Term**, **B) Concise Definition**, and **C) Example Sentence** relevant to the topic.<br>* **Worksheet:** Output must be a numbered list of **10 varied questions** (e.g., matching, short answer, fill-in-the-blank) followed by a separate **Answer Key**.<br>* **Quiz:** Output must be a **5-question Multiple Choice Quiz** with four options for each question, followed by a separate **Answer Key**.<br>* **Test:** Output must be organized into two main sections: **A) Multiple Choice (15 Questions)** and **B) Short/Long Answer (4 Questions)**, followed by a detailed **Answer Key/Rubric**.<br></div>
"""

try:
    # This must be defined before the client uses it.
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

# --- INITIALIZE GEMINI CLIENT (FINAL, CORRECT FIX) ---
client = None # Default to None
api_key_source = "None"

try:
    api_key = None
    
    # 1. Prioritize Streamlit secrets
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        api_key_source = "Streamlit Secrets"
    # 2. Fallback to os.getenv 
    elif os.getenv("GEMINI_API_KEY"):
        api_key = os.getenv("GEMINI_API_KEY")
        api_key_source = "Environment Variable"

    if api_key and api_key.strip():
        # Use the standard, modern configuration method
        genai.configure(api_key=api_key) 
        
        # CRITICAL FIX: Pass system instruction at model instantiation.
        # This works because SYSTEM_INSTRUCTION is now DEFINED above this block.
if api_key and api_key.strip():
        # Use the standard, modern configuration method
        genai.configure(api_key=api_key) 
        
        # CRITICAL FIX: Pass system instruction at model instantiation.
        # This works because SYSTEM_INSTRUCTION is now DEFINED above this block.
        client = genai.GenerativeModel(MODEL, system_instruction=SYSTEM_INSTRUCTION) 
        # Success message 'st.sidebar.success(...)' removed to display nothing on successful connection, as requested.
    else:
        st.sidebar.warning("⚠️ Gemini API Key not found or is empty. Running in MOCK MODE.")
        
except APIError as e:
    client = None
    st.sidebar.error(f"❌ Gemini API Setup Error: {e}")
    st.sidebar.info("Please ensure your Gemini API Key is valid and active.")
except Exception as e:
    client = None
    # Log the full exception for remote debugging via Streamlit Cloud's logs
    st.sidebar.error(f"❌ Unexpected Setup Error during Gemini client initialization. See Streamlit logs for details.")
    st.exception(e)
    
# --- END INITIALIZE GEMINI CLIENT ---


# --- 1. THE 28 FUNCTION LIST (Internal Mapping for Mocking) ---
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
    return f"**Feature 10: Recipe Improver**\nSimple recipe instructions for: {ingredients}\n1. Sauté the chicken and onions until browned. 3. Add vegetables and stock. 4. Simmer for 20 minutes and serve with rice."
def symptom_clarifier(symptoms: str) -> str:
    return f"**Feature 11: Symptom Clarifier**\n3 plausible benign causes for '{symptoms}':\n1. Common seasonal allergies (pollen/dust).\n2. Mild fatigue due to poor sleep.\n3. Dehydration or temporary low blood sugar."

def tone_checker_rewriter(text_tone: str) -> str:
    return f"**Feature 12: Tone Checker & Rewriter**\nRewritten text (Desired tone: Professional):\n'I acknowledge receipt of your request and will provide the deliverable by the end of business tomorrow.'"
def contextual_translator(phrase_context: str) -> str:
    return f"**Feature 13: Contextual Translator**\nTranslation (French, Formal Register): **'Pourriez-vous, s'il vous plaît, me donner les détails?'** (Could you, please, give me the details?)"
def metaphor_machine(topic: str) -> str:
    return f"**Feature 14: Metaphor Machine**\n3 Creative Analogies for '{topic}':\n1. The cloud is a global, shared library.\n2. Information flow is like an ocean tide.\n3. The network is a massive spider web."
def email_text_reply_generator(message_points: str) -> str:
    return f"**Feature 15: Email/Text Reply Generator**\nDrafted concise reply for: {message_points}\n'Thank you for bringing this up. I will review the documents immediately and ensure the changes are implemented by 3 PM today.'"

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

def concept_simplifier(complex_topic: str) -> str:
    return f"**Feature 19: Concept Simplifier**\nExplanation of '{complex_topic}' using simple analogy:\nQuantum entanglement is like having two special coins that always land on the opposite side, no matter how far apart you take them. Observing one instantly tells you the state of the other."
def code_explainer(code_snippet: str) -> str:
    return f"**Feature 20: Code Explainer**\nPlain-language explanation of function:\nThis Python code snippet defines a function that takes a list of numbers, filters out any duplicates, sorts the remaining unique numbers, and returns the result."

def packing_list_generator(trip_details: str) -> str:
    return f"""
**Feature 21: Packing List Generator**
Checklist for: {trip_details}
**Clothes:** 3 Shirts, 2 Pants, 1 Jacket, 1 Pair of Formal Shoes.
**Essentials:** Passport, Wallet, Adapter, Phone Charger, Medications.
**Toiletries:** Toothbrush, Paste, Shampoo (Travel size).
"""

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
        "3. 'Get Unstuck' Prompter": get_unstuck_prompter, # <--- FIXED HERE
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
    "3. 'Get Unstuck' Prompter": "I can't figure out the opening paragraph for my essay.", # <--- FIXED HERE
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

# --- AI GENERATION FUNCTION (FINAL VERSION) ---
def run_ai_generation(feature_function_key: str, prompt_text: str, uploaded_image: Image.Image = None) -> str:
    """
    Executes the selected feature function. Uses the real Gemini API if available,
    otherwise falls back to the mock functions.
    """

    # 1. Fallback/Mock execution
    if client is None:
        st.warning("⚠️ **MOCK MODE:** Gemini Client is NOT initialized. Using Mock Response.")
        selected_function = None
        
        # Check Utility Mappings
        for category_features in UTILITY_CATEGORIES.values():
            if feature_function_key in category_features:
                selected_function = category_features[feature_function_key]
                break
        
        is_teacher_aid_proxy = feature_function_key == "Teacher_Aid_Routing"
        
        if selected_function:
            if feature_function_key == "9. Image-to-Calorie Estimate":
                return selected_function(uploaded_image, prompt_text)
            else:
                return selected_function(prompt_text)
        elif is_teacher_aid_proxy:
            # --- CRITICAL FIX: Detailed Mock Responses for Teacher Aid Resources ---
            if "Unit Overview" in prompt_text:
                topic = prompt_text.replace("Unit Overview", "").strip() or "a new unit"
                return f"""
**Teacher Aid Resource: Unit Overview**
**Request:** *{prompt_text}*

---

### Unit Overview: {topic.title()}

**A) Unit Objectives:**
1.  Students will be able to identify key concepts and theories related to {topic}.
2.  Students will be able to analyze the impact of {topic} on real-world scenarios.
3.  Students will be able to critically evaluate different perspectives on {topic}.

**B) Key Topics/Subtopics:**
* Introduction to {topic}
* Historical Context and Development
* Major Theories and Principles
* Applications and Case Studies
* Future Implications

**C) Suggested Activities (3-5):**
1.  **Debate:** Organize a classroom debate on a controversial aspect of {topic}.
2.  **Research Project:** Assign small groups to research and present on a specific subtopic.
3.  **Concept Mapping:** Students create visual concept maps connecting key terms.
4.  **Guest Speaker:** Invite an expert in the field to speak to the class.
5.  **Field Trip:** Visit a relevant museum or institution (if applicable).

**D) Assessment Overview:**
* Formative: Quizzes after each subtopic, participation in discussions.
* Summative: A final essay (25%), a group presentation (25%), and a comprehensive test (50%).
"""
            elif "Lesson Plan" in prompt_text:
                topic = prompt_text.replace("Lesson Plan", "").strip() or "a specific lesson"
                return f"""
**Teacher Aid Resource: Lesson Plan**
**Request:** *{prompt_text}*

---

### Lesson Plan: Introduction to {topic.title()}

**A) Objective:**
* Students will be able to define {topic} and explain its basic principles.
* Students will be able to provide at least two examples of {topic} in daily life.

**B) Materials:**
* Whiteboard or projector
* Markers/pens
* Handout with key terms
* Short video clip (5 minutes) related to {topic}

**C) Procedure:**
* **Warm-up (10 min):** Ask students to brainstorm what they already know about {topic}. Write ideas on the board.
* **Main Activity (30 min):**
    * Teacher explains core concepts using visual aids.
    * Show video clip and discuss.
    * Students work in pairs to answer questions on the handout.
* **Wrap-up (10 min):** Review answers as a class. Assign a quick write for homework: "What is one new thing you learned about {topic} today?"

**D) Assessment Strategy:**
* Informal: Observe student participation in discussions and pair work.
* Formative: Collect and review quick writes for understanding.
"""
            elif "Vocabulary List" in prompt_text:
                topic = prompt_text.replace("Vocabulary List", "").strip() or "general science"
                return f"""
**Teacher Aid Resource: Vocabulary List**
**Request:** *{prompt_text}*

---

### Vocabulary List: {topic.title()}

1.  **Term:** Photosynthesis
    * **Concise Definition:** The process by which green plants and some other organisms use sunlight to synthesize foods from carbon dioxide and water.
    * **Example Sentence:** During **photosynthesis**, plants absorb carbon dioxide from the atmosphere.
2.  **Term:** Ecosystem
    * **Concise Definition:** A biological community of interacting organisms and their physical environment.
    * **Example Sentence:** The rainforest is a complex **ecosystem** teeming with biodiversity.
3.  **Term:** Hypothesis
    * **Concise Definition:** A proposed explanation made on the basis of limited evidence as a starting point for further investigation.
    * **Example Sentence:** Her **hypothesis** was that increased sunlight would lead to faster plant growth.
4.  **Term:** Molecule
    * **Concise Definition:** A group of atoms bonded together, representing the smallest fundamental unit of a chemical compound that can take part in a chemical reaction.
    * **Example Sentence:** A water **molecule** is made of two hydrogen atoms and one oxygen atom.
5.  **Term:** Gravity
    * **Concise Definition:** The force that attracts a body toward the center of the earth, or toward any other physical body having mass.
    * **Example Sentence:** **Gravity** keeps our feet on the ground and planets in orbit.
"""
            elif "Worksheet" in prompt_text:
                topic = prompt_text.replace("Worksheet", "").strip() or "basic math"
                return f"""
**Teacher Aid Resource: Worksheet**
**Request:** *{prompt_text}*

---

### Worksheet: {topic.title()} Practice

**Instructions:** Answer all questions to the best of your ability.

1.  What is the capital city of France? (Short Answer)
2.  Fill in the blank: The Earth orbits the ______.
3.  Match the following:
    a) Dog             i) Feline
    b) Cat             ii) Canine
4.  Solve: $5 \times 7 = $ _____.
5.  List three primary colors.
6.  True or False: Birds are mammals.
7.  What is the main function of the heart?
8.  If you have 12 apples and eat 3, how many are left?
9.  Write a sentence using the word "magnificent."
10. Name a famous scientist.

---

### Answer Key:
1.  Paris
2.  Sun
3.  a) ii, b) i
4.  35
5.  Red, Yellow, Blue
6.  False
7.  To pump blood throughout the body.
8.  9
9.  (Accept any grammatically correct sentence using "magnificent")
10. (Accept any famous scientist, e.g., Albert Einstein, Marie Curie)
"""
            elif "Quiz" in prompt_text:
                topic = prompt_text.replace("Quiz", "").strip() or "general knowledge"
                return f"""
**Teacher Aid Resource: Quiz**
**Request:** *{prompt_text}*

---

### Quiz: {topic.title()}

**Instructions:** Choose the best answer for each question.

1.  What is the largest ocean on Earth?
    a) Atlantic Ocean
    b) Indian Ocean
    c) Arctic Ocean
    d) Pacific Ocean
2.  Who painted the Mona Lisa?
    a) Vincent van Gogh
    b) Pablo Picasso
    c) Leonardo da Vinci
    d) Claude Monet
3.  Which planet is known as the "Red Planet"?
    a) Venus
    b) Mars
    c) Jupiter
    d) Saturn
4.  What is the chemical symbol for water?
    a) O2
    b) CO2
    c) H2O
    d) NaCl
5.  How many continents are there?
    a) 5
    b) 6
    c) 7
    d) 8

---

### Answer Key:
1.  d) Pacific Ocean
2.  c) Leonardo da Vinci
3.  b) Mars
4.  c) H2O
5.  c) 7
"""
            elif "Test" in prompt_text:
                topic = prompt_text.replace("Test", "").strip() or "comprehensive review"
                return f"""
**Teacher Aid Resource: Test**
**Request:** *{prompt_text}*

---

### Test: {topic.title()} Comprehensive Exam

**A) Multiple Choice (15 Questions):**
*Instructions: Select the best answer for each question.*

1.  Question 1 about {topic}?
    a) Option A
    b) Option B
    c) Option C
    d) Option D
2.  Question 2 about {topic}?
    a) Option A
    b) Option B
    c) Option C
    d) Option D
... (13 more multiple choice questions) ...
15. Question 15 about {topic}?
    a) Option A
    b) Option B
    c) Option C
    d) Option D

**B) Short/Long Answer (4 Questions):**
*Instructions: Answer the following questions in complete sentences or paragraphs.*

1.  Explain the primary causes and effects of [key event/concept in topic]. (Short Answer)
2.  Compare and contrast two different perspectives on [another key concept in topic]. (Short Answer)
3.  Describe in detail how [element A] influences [element B] within the context of {topic}. Provide specific examples. (Long Answer)
4.  Propose a solution to a problem related to {topic} and justify your reasoning. (Long Answer)

---

### Answer Key/Rubric:

**Multiple Choice Answers:**
1.  [Correct Answer]
2.  [Correct Answer]
...
15. [Correct Answer]

**Short/Long Answer Rubric:**

* **Question 1 (5 points):**
    * 5 pts: Comprehensive explanation of both causes and effects with accurate details.
    * 3 pts: Partial explanation or some inaccuracies.
    * 1 pt: Minimal or incorrect information.
* **Question 2 (5 points):**
    * 5 pts: Clear comparison and contrast of two perspectives with supporting details.
    * 3 pts: Adequate comparison but lacking depth or minor inaccuracies.
    * 1 pt: Unclear or incorrect comparison.
* **Question 3 (10 points):**
    * 10 pts: Detailed description with relevant examples, demonstrating deep understanding.
    * 6 pts: Good description, but examples may be weak or understanding is not fully demonstrated.
    * 3 pts: Basic description with limited or no examples.
* **Question 4 (10 points):**
    * 10 pts: Well-reasoned solution with strong justification.
    * 6 pts: Plausible solution with some justification, but may lack depth.
    * 3 pts: Basic or unclear solution with weak justification.
"""
            else:
                # Default generic response for Teacher Aid if no specific tag is found
                return f"""
**Teacher Aid Resource Generation (MOCK - Generic)**

**Request:** *{prompt_text}*

---

### Generic Resource Output
The system has received your request. For a more structured output, please include a specific **Resource Tag** in your prompt, such as: **Unit Overview**, **Lesson Plan**, **Vocabulary List**, **Worksheet**, **Quiz**, or **Test**.

**Example:** "Create a **Lesson Plan** for teaching fractions."

---
*This is a mock response because the Gemini API is not connected or the request did not match a specific teacher resource tag.*
"""
            # --- END CRITICAL FIX FOR TEACHER AID MOCK RESPONSES ---
        else:
            return "Error: Feature not found or not yet implemented."

    # 2. Real AI execution (if client is available)
    try:
        contents = []
        if feature_function_key == "9. Image-to-Calorie Estimate" and uploaded_image:
            # Convert PIL Image to BytesIO for sending to Gemini
            img_byte_arr = BytesIO()
            uploaded_image.save(img_byte_arr, format=uploaded_image.format or 'PNG')
            img_byte_arr = img_byte_arr.getvalue()

            contents.append(genai.types.Blob(mime_type="image/jpeg", data=img_byte_arr))

        contents.append(prompt_text)

        # System instruction is now set at model instantiation (in the setup block). 
        # Create an empty config object to satisfy the required argument.
        generation_config = GenerationConfig()

        response = client.generate_content(
            contents=contents,
            generation_config=generation_config
        )
        return response.text

    except APIError as e:
        return f"Gemini API Error: Could not complete request. Details: {e}"
    except Exception as e:
        return f"An unexpected error occurred during AI generation: {e}"


# --- CATEGORY AND FEATURE MAPPING (REST OF FILE CONTENT FOLLOWS) ---
# ... [The rest of your UTILITY_CATEGORIES, FEATURE_EXAMPLES, and rendering functions] ...

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
    # NOTE: The old 'teacher_output' and 'teacher_view' states are now obsolete/deleted.


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
                # Removed obsolete teacher view state reset
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

                    generated_output = run_ai_generation(
                        feature_function_key=selected_feature,
                        prompt_text=prompt_input,
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


# --- TEACHER AID RENDERERS (FIXED TO MULTIPLE TABS) ---
def render_teacher_aid_content(can_interact, universal_error_msg):
    st.title("🎓 Teacher Aid Hub")
    st.caption("Generate specialized educational resources using dedicated tabs for each resource type.")
    st.markdown("---")

    if not can_interact:
        st.error(f"🛑 **ACCESS BLOCKED:** {universal_error_msg}. Cannot interact.")
        return

    # Pass the save check results to the generation tab
    can_save_teacher, teacher_error_msg, teacher_limit = check_storage_limit(st.session_state.storage, 'teacher_save')
    
    # Define the Resource Tags to be used as tab names
    RESOURCE_TAGS = [
        "Unit Overview", "Lesson Plan", "Vocabulary List", 
        "Worksheet", "Quiz", "Test"
    ]
    
    # Dictionary to store outputs for each tab, to keep them separate
    if 'teacher_outputs_by_type' not in st.session_state:
        st.session_state['teacher_outputs_by_type'] = {tag: "" for tag in RESOURCE_TAGS}

    # Create the tabs (6 resource tabs + 1 history tab = 7 tabs)
    tabs = st.tabs(RESOURCE_TAGS + ["📚 Saved History"])

    # Loop through each resource tag to create its corresponding tab content
    for i, resource_type in enumerate(RESOURCE_TAGS):
        with tabs[i]:
            st.subheader(f"Generate {resource_type}")
            
            example_input_map = {
                "Unit Overview": f"Create a **Unit Overview** for 7th-grade history on ancient civilizations.",
                "Lesson Plan": f"Develop a **Lesson Plan** for a high school chemistry class covering chemical reactions.",
                "Vocabulary List": f"Generate a **Vocabulary List** for an English class on Shakespearean terminology.",
                "Worksheet": f"Provide a **Worksheet** for pre-algebra students practicing order of operations.",
                "Quiz": f"Make a **Quiz** on the basic functions of a plant cell.",
                "Test": f"Create a **Test** for a 9th-grade biology course on genetics."
            }
            example_prompt_snippet = example_input_map.get(resource_type, f"Create a **{resource_type}** on your topic.")
            st.markdown(f'<p class="example-text">Example Prompt: <code>{example_prompt_snippet}</code></p>', unsafe_allow_html=True)

            teacher_prompt = st.text_area(
                f"Enter your specific topic and details (The tag **{resource_type}** will be automatically added):",
                placeholder=f"e.g., 'on the causes and effects of the American Civil War' for a {resource_type}",
                height=150,
                key=f"teacher_ai_prompt_{resource_type.replace(' ', '_')}"
            )
            
            # The prompt sent to the AI function must contain the Resource Tag to trigger the mock/AI routing
            final_prompt = f"{resource_type} {teacher_prompt}".strip()

            if st.button(f"Generate {resource_type}", key=f"teacher_generate_btn_{resource_type.replace(' ', '_')}", use_container_width=True):
                if not teacher_prompt:
                    st.warning("Please enter a topic and details for the resource.")
                    st.session_state['teacher_outputs_by_type'][resource_type] = "" 
                    return

                feature_key_proxy = "Teacher_Aid_Routing" # All teacher aid goes through this proxy

                with st.spinner(f"Generating specialized {resource_type} resource..."):
                    generated_output = run_ai_generation(
                        feature_function_key=feature_key_proxy,
                        prompt_text=final_prompt,
                        uploaded_image=None
                    )
                    st.session_state['teacher_outputs_by_type'][resource_type] = generated_output

                    if can_save_teacher:
                        data_to_save = {
                            "timestamp": pd.Timestamp.now().isoformat(),
                            "request_type": resource_type, # Save the specific type
                            "request": final_prompt[:100] + "..." if len(final_prompt) > 100 else final_prompt,
                            "output_size_bytes": calculate_mock_save_size(generated_output),
                            "output_content": generated_output
                        }

                        st.session_state.teacher_db['history'].append(data_to_save)
                        save_db_file(get_file_path("teacher_data_", st.session_state.current_user), st.session_state.teacher_db)

                        mock_size = data_to_save["output_size_bytes"]
                        st.session_state.storage['current_teacher_storage'] += mock_size
                        st.session_state.storage['current_universal_storage'] += mock_size
                        save_storage_tracker(st.session_state.storage, st.session_state.current_user)

                        st.success(f"{resource_type} saved to Teacher History (Mock Size: {mock_size} bytes).")
                    else:
                        st.error(f"⚠️ **Teacher History Save Blocked:** {teacher_error_msg}. Result is displayed below but not saved.")

            st.markdown("---")
            st.subheader(f"Generated {resource_type} Output")
            if st.session_state['teacher_outputs_by_type'].get(resource_type):
                st.markdown(st.session_state['teacher_outputs_by_type'][resource_type])
            else:
                st.info(f"Your generated {resource_type} will appear here.")

    # --- Saved History Tab (Last tab) ---
    history_tab_index = len(RESOURCE_TAGS)
    with tabs[history_tab_index]: # Access the last tab
        st.subheader("Teacher Aid Saved History")
        
        # CRITICAL FIX: Ensure all history entries have 'request_type' for display
        teacher_history = st.session_state.teacher_db['history']
        for item in teacher_history:
            if 'request_type' not in item:
                # Infer type from the prompt text for old entries
                item['request_type'] = next((tag for tag in RESOURCE_TAGS if tag in item['request']), 'Resource')
        
        teacher_df = pd.DataFrame(teacher_history)

        if not teacher_df.empty:
            teacher_df['timestamp'] = pd.to_datetime(teacher_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            # Drop the 'output_content' column for the main table view to keep it clean
            display_df = teacher_df.drop(columns=['output_content'], errors='ignore')
            display_df['request_snippet'] = display_df['request'].str.slice(0, 50) + '...'
            
            # Ensure 'request_type' exists for display
            if 'request_type' not in display_df.columns:
                 display_df['request_type'] = 'Resource'
                 
            st.dataframe(
                display_df[['timestamp', 'request_type', 'request_snippet', 'output_size_bytes']].sort_values(by='timestamp', ascending=False), 
                use_container_width=True
            )
            
            history_indices = teacher_df.index.tolist()
            if history_indices:
                selected_row_index_teacher = st.selectbox(
                    "Select History Item for Full Content View:", 
                    history_indices, 
                    format_func=lambda i: f"[{i+1}] {display_df.loc[i, 'request_type']} - {display_df.loc[i, 'request_snippet']}", 
                    key="teacher_history_selector"
                )
                
                if selected_row_index_teacher is not None and not teacher_df.empty:
                    st.markdown("---")
                    st.subheader("Full Resource Content")
                    # Use a text_area for better readability of large content
                    st.text_area(
                        f"Content for {teacher_df.loc[selected_row_index_teacher, 'request_type']}: {teacher_df.loc[selected_row_index_teacher, 'request']}",
                        teacher_df.loc[selected_row_index_teacher, 'output_content'],
                        height=300,
                        key="full_teacher_content_display"
                    )
        else:
            st.info("No teacher resources have been saved yet.")


# --- USAGE DASHBOARD RENDERER (GRAPHS RESTORED) ---
def render_usage_dashboard():
    st.title("📊 Usage Dashboard")
    st.markdown("---")
    st.subheader(f"Current Plan: {st.session_state.storage['tier']} ({TIER_PRICES.get(st.session_state.storage['tier'])})")

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
