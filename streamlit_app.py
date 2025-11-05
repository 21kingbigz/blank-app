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
# Note: Using image_ffd419.png as an example logo filename since it was uploaded
LOGO_FILENAME = "image_ffd419.png" # Assuming this is the correct logo file name
ICON_SETTING = "💡"

st.set_page_config(
    page_title=WEBSITE_TITLE,
    page_icon=ICON_SETTING,
    layout="wide",
    initial_sidebar_state="auto"
)

# --- INITIALIZE GEMINI CLIENT (CRITICAL FIX FOR API KEY RETRIEVAL) ---
client = None # Default to None

try:
    # 1. Safely retrieve the API key first
    api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

    if api_key:
        # 2. Only proceed to configure and initialize if the key is found
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel(MODEL)
        # st.success("Gemini Client successfully initialized!") # Optional feedback
    else:
        # Key not found, client remains None.
        pass # The "Using Mock Response" warning will handle this.

except Exception as e:
    # If genai configuration or model initialization fails for any reason
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

# --- 1. THE 28 FUNCTION LIST (Internal Mapping for Mocking) ---
# NOTE: Mock functions remain the same as previous iterations.

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
    return f"**Feature 10: Recipe Improver**\nSimple recipe instructions for: {ingredients}\n1. Sauté the chicken and onions until browned. 2. Add vegetables and stock. 3. Simmer for 20 minutes and serve with rice."
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
    "23. English & Literature Expert AI": "Analyze the theme of isolation in 'The
