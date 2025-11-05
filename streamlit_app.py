import streamlit as st
import os
import pandas as pd
from PIL import Image
from io import BytesIO
import json
import re
import random
import time

# --- Ensure you have google-genai installed and configured ---
try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    genai = None
    APIError = type("APIError", (Exception,), {})
    st.error("The 'google-genai' library is not installed. AI features will be mocked. Please install it using: pip install google-genai")

# --- MOCK IMPORTS AND INITIAL DATA ---
def load_users():
    return {"teacher@example.com": {"password": "password123", "tier": "Teacher Pro"}}

# Mock Storage Logic (uses st.session_state instead of actual file system)
def load_db_file(filename, initial_data):
    if filename not in st.session_state:
        st.session_state[filename] = initial_data.copy()
    return st.session_state[filename]

def load_storage_tracker():
    return load_db_file("storage_tracker", {})

def logout():
    st.session_state.clear()
    st.rerun()

# Mock Auth Logic (simplified)
def render_login_page():
    st.sidebar.subheader("Login")
    with st.sidebar.form("login_form"):
        email = st.text_input("Email", value="teacher@example.com")
        password = st.text_input("Password", type="password", value="password123")
        submitted = st.form_submit_button("Login")
        if submitted:
            users = load_users()
            if email in users and users[email]["password"] == password:
                st.session_state['logged_in'] = True
                st.session_state['user_email'] = email
                st.session_state['user_tier'] = users[email]["tier"]
                st.success(f"Welcome, {email}!")
                st.rerun()
            else:
                st.error("Invalid email or password.")

# --- 0. CONFIGURATION AND CONSTANTS ---
WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash'
LOGO_FILENAME = "image_ffd419.png" 
ICON_SETTING = "💡"

st.set_page_config(
    page_title=WEBSITE_TITLE,
    page_icon=ICON_SETTING,
    layout="wide",
    initial_sidebar_state="auto"
)

# --- INITIALIZE GEMINI CLIENT (API Key Fix Implemented Here) ---
client = None

try:
    # Priority 1: User-entered key
    api_key = st.session_state.get('user_gemini_api_key')
    # Priority 2: Environment/Secrets key
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None)

    if api_key and genai:
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel(MODEL)
    else:
        pass # Client remains None, mock functions will be used

except Exception as e:
    client = None
    st.error(f"Gemini API Setup Error during initialization: {e}")

# --- SYSTEM INSTRUCTION (Defines the 6 distinct resource formats) ---
SYSTEM_INSTRUCTION = """
You are the "Teacher Aid AI." Your response MUST be the direct, full output of the selected resource format. Do not add conversational text or pre-amble.

--- Teacher Resource Tags ---

* **Unit Overview:** Output must include four sections: **A) Unit Objectives**, **B) Key Topics/Subtopics**, **C) Suggested Activities (3-5)**, and **D) Assessment Overview**.
* **Lesson Plan:** Output must follow a structured plan: **A) Objective**, **B) Materials**, **C) Procedure (Warm-up, Main Activity, Wrap-up)**, and **D) Assessment Strategy** (4 items).
* **Vocabulary List:** Output must be a list of terms, each entry containing: **A) Term**, **B) Concise Definition**, and **C) Example Sentence** relevant to the topic. (3 items per term).
* **Worksheet:** Output must be a numbered list of **10 varied questions** (e.g., matching, short answer, fill-in-the-blank) followed by a separate **Answer Key** (10 items).
* **Quiz:** Output must be a **5-question Multiple Choice Quiz** with four options for each question, followed by a separate **Answer Key** (5 items).
* **Test:** Output must be organized into two main sections: **A) Multiple Choice (15 Questions)** and **B) Short/Long Answer (4 Questions)**, followed by a detailed **Answer Key/Rubric** (19 items total).
"""

# --- UI STYLING ---
st.markdown(
    """
    <style>
    .tier-label {
        font-size: 0.8em;
        color: #888;
        margin-top: -15px;
        margin-bottom: 20px;
    }
    .stRadio > label {
        padding-right: 0;
        margin-bottom: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- MOCK GENERATION FUNCTIONS (Used when AI Client fails) ---
def mock_generate_unit_overview(topic: str) -> str:
    return f"""### Unit Overview: {topic}
**A) Unit Objectives:** Students will identify key causes and major outcomes.
**B) Key Topics/Subtopics:** Causes, Key Figures, Timeline, and Aftermath.
**C) Suggested Activities (3-5):** 1. Primary Source Analysis. 2. Group Presentation. 3. Debate Exercise.
**D) Assessment Overview:** Comprehensive Test and a Unit Project.
"""
def mock_generate_lesson_plan(topic: str) -> str:
    return f"""### Lesson Plan: {topic}
**A) Objective:** Students will be able to describe the process.
**B) Materials:** Whiteboard, Markers, Handouts.
**C) Procedure:** Warm-up (10 min), Main Activity (30 min), Wrap-up (10 min).
**D) Assessment Strategy:** Exit ticket and observation.
"""
def mock_generate_vocabulary_list(topic: str) -> str:
    return f"""### Vocabulary List: {topic}
1. **Term:** Definition (Concise Definition). **Example Sentence:** (Sentence relevant to topic).
2. **Term:** Definition (Concise Definition). **Example Sentence:** (Sentence relevant to topic).
3. **Term:** Definition (Concise Definition). **Example Sentence:** (Sentence relevant to topic).
"""
def mock_generate_worksheet(topic: str) -> str:
    return f"""### Worksheet: {topic} (10 Questions)
1. Fill-in-the-Blank: ___. 2. Short Answer: ___. 3. Solve for X: ___. ... (Q4-Q10)
**--- Answer Key (10 items) ---**
1. Answer. 2. Answer. 3. Answer. ... (Answers 4-10)
"""
def mock_generate_quiz(topic: str) -> str:
    return f"""### Quiz: {topic} (5-Question Multiple Choice)
1. (Q1 text)? (A, B, C, D) 2. (Q2 text)? (A, B, C, D) 3. (Q3 text)? (A, B, C, D) 4. (Q4 text)? (A, B, C, D) 5. (Q5 text)? (A, B, C, D)
**--- Answer Key (5 items) ---**
1. C. 2. A. 3. B. 4. D. 5. A.
"""
def mock_generate_test(topic: str) -> str:
    return f"""### Test: {topic} (19 Questions Total)
**A) Multiple Choice (15 Questions):** 1. (Q1 text)? ... (Q2-Q15 text)
**B) Short/Long Answer (4 Questions):** 16. Describe X. 17. Analyze Y. 18. Define A. 19. Compare B and C.
**--- Answer Key/Rubric (19 items) ---**
**A) Multiple Choice:** 1. B, 2. D, ... (Answers for 3-15)
**B) Short/Long Answer Rubric:** 16. (4 Points) 17. (5 Points) 18. (3 Points) 19. (5 Points)
"""

TEACHER_RESOURCES = {
    "Unit Overview": mock_generate_unit_overview,
    "Lesson Plan": mock_generate_lesson_plan,
    "Vocabulary List": mock_generate_vocabulary_list,
    "Worksheet": mock_generate_worksheet,
    "Quiz": mock_generate_quiz,
    "Test": mock_generate_test,
}

# --- PAGE RENDERING FUNCTIONS ---

def render_usage_dashboard():
    """Renders the Usage Dashboard with 4 distinct charts and corrected data trend."""
    st.title("📊 Usage Dashboard")
    st.markdown("##### Resource Generation Analytics")
    st.markdown("---")

    # Mock Data with an UPWARD trend (Corrected)
    start_value = 50
    daily_growth = [random.randint(5, 20) for _ in range(30)]
    
    # Calculate cumulative resources generated (upward trend)
    resources_generated = [start_value + sum(daily_growth[:i+1]) for i in range(30)]

    data = {
        'Date': pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')),
        'Resources Generated': resources_generated,
        'Users Logged In': [random.randint(5, 50) for _ in range(30)],
        'Total Saved Items': [random.randint(10, 80) for _ in range(30)],
        'Worksheet': [random.randint(0, 30) for _ in range(30)],
        'Lesson Plan': [random.randint(0, 40) for _ in range(30)],
        'Quiz/Test Count': [random.randint(0, 25) for _ in range(30)],
    }
    df = pd.DataFrame(data).set_index('Date')

    # Graph 1 (Line Chart - Resources Generated Over Time - UPWARD TREND)
    st.subheader("1. Cumulative Resource Generation Trend")
    st.line_chart(df['Resources Generated'])

    st.markdown("---")

    # Graph 2 (Bar Chart - User Activity)
    st.subheader("2. Daily User Logins")
    st.bar_chart(df['Users Logged In'])

    st.markdown("---")

    # Graph 3 (Stacked Bar - Top 3 Resource Types Over Time)
    st.subheader("3. Top 3 Resource Types Generated (Last 30 Days)")
    top_resource_df = df[['Worksheet', 'Lesson Plan', 'Quiz/Test Count']]
    st.bar_chart(top_resource_df, use_container_width=True)

    st.markdown("---")

    # Graph 4 (Data Table - Saved Item Growth)
    st.subheader("4. Growth in Total Saved Items (Last 7 Days)")
    st.dataframe(df[['Total Saved Items']].tail(7), use_container_width=True)


def run_teacher_aid_generation(resource_type, topic, grade_level, client):
    """Handles the Teacher Aid generation workflow."""
    if not topic:
        st.error("Please enter a topic to generate a resource.")
        return

    st.info(f"Generating **{resource_type}** for **{topic}** (Grade {grade_level})...")

    if not client:
        # Fallback to Mock Generation if client is not initialized
        mock_func = TEACHER_RESOURCES.get(resource_type)
        if mock_func:
            time.sleep(1)
            return mock_func(topic)
        return None

    # --- AI GENERATION CALL ---
    prompt = f"Topic: {topic}. Grade Level: {grade_level}. Resource Type: {resource_type}."
    full_prompt = f"{SYSTEM_INSTRUCTION}\n\nBased on the resource type '{resource_type}', and the prompt: '{prompt}', generate the full, structured output according to the rubric."

    try:
        response = client.generate_content(
            full_prompt,
            system_instruction=SYSTEM_INSTRUCTION
        )
        return response.text
    except APIError as e:
        st.error(f"Gemini API Error: {e}. Falling back to mock data.")
        return TEACHER_RESOURCES[resource_type](topic)
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}. Falling back to mock data.")
        return TEACHER_RESOURCES[resource_type](topic)

def render_teacher_aid_content():
    st.title("✍️ Resource Generation")
    st.markdown("##### AI-Powered Teacher's Aid")
    st.markdown("---")

    resource_type = st.radio(
        "Select Resource Type:",
        list(TEACHER_RESOURCES.keys()),
        horizontal=True
    )

    topic = st.text_input("Topic/Subject (e.g., The causes and effects of the French Revolution)")
    col1, col2 = st.columns(2)
    with col1:
        grade_level = st.selectbox("Grade Level", ["K-2", "3-5", "6-8", "9-12", "College"])

    if st.button(f"Generate {resource_type}", use_container_width=True, type="primary"):
        if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
            st.error("Please log in to use the resource generation tool.")
            return

        with st.spinner("Contacting AI Model..."):
            generated_content = run_teacher_aid_generation(resource_type, topic, grade_level, client)

        if generated_content:
            st.session_state['last_generated_content'] = generated_content
            st.session_state['last_generated_type'] = resource_type
            st.session_state['last_generated_topic'] = topic

            st.subheader(f"Generated {resource_type} for: {topic}")
            st.markdown(generated_content)

            if st.button("Save to History", key="save_teacher_aid"):
                st.session_state['teacher_aid_history'] = st.session_state.get('teacher_aid_history', [])
                st.session_state['teacher_aid_history'].insert(0, {
                    "type": resource_type,
                    "topic": topic,
                    "content": generated_content,
                    "timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                st.success(f"{resource_type} saved to history!")


def render_saved_history_content():
    st.title("💾 Saved History")
    st.markdown("---")
    history = st.session_state.get('teacher_aid_history', [])
    if not history:
        st.info("No saved resources yet.")
        return
    st.write(f"Showing {len(history)} saved item(s):")
    for i, item in enumerate(history):
        with st.expander(f"**{item['type']}: {item['topic']}** - *Saved {item['timestamp']}*"):
            st.markdown(item['content'])
            if st.button("Delete", key=f"delete_{i}"):
                history.pop(i)
                st.session_state['teacher_aid_history'] = history
                st.success("Item deleted.")
                st.rerun()

def render_app_settings():
    st.title("⚙️ App Settings")
    st.markdown("---")
    st.subheader("Gemini API Key Configuration")
    st.markdown(
        """
        Enter your **Gemini API Key** below to manually configure the AI model for this session.
        This setting will override any key stored in your environment or secrets file.
        """
    )
    user_key = st.text_input(
        "API Key",
        type="password",
        value=st.session_state.get('user_gemini_api_key', '')
    )

    if st.button("Save & Apply Key"):
        if user_key and user_key.startswith("AIza"):
            st.session_state['user_gemini_api_key'] = user_key
            st.success("API Key saved and applied for this session! Rerunning app to initialize AI client.")
            st.rerun()
        elif not user_key:
            if 'user_gemini_api_key' in st.session_state:
                del st.session_state['user_gemini_api_key']
                st.warning("API Key cleared. Rerunning to fall back to secrets.")
                st.rerun()
            else:
                st.warning("Please enter a valid API key.")
        else:
            st.error("Invalid API Key format.")

    st.markdown("---")

    st.subheader("Account Details")
    st.write(f"**Current Tier:** {st.session_state.get('user_tier', 'Free Tier')}")

def render_tutorials_content():
    st.title("💡 Tutorials")
    st.markdown("---")
    st.markdown("""
    Welcome! Here is a brief guide on the main functions:
    ### 1. Resource Generation
    * **Goal:** Create tailored teaching materials quickly.
    * **Tip:** The output follows a strict structure (e.g., Test = 15 MC + 4 Long Answer).
    ### 2. Usage Dashboard
    * **Goal:** Monitor your resource generation trends and user activity.
    ### 3. API Key
    * **Crucial:** If AI generation fails, go to **App Settings** and ensure your Gemini API Key is entered correctly.
    """)

# --- MAIN APP EXECUTION FLOW (Simplified and direct) ---

def render_main_app():
    """Renders the sidebar navigation and calls the active page function."""
    
    # 1. Sidebar Navigation
    with st.sidebar:
        st.header(WEBSITE_TITLE)
        st.markdown(f'<div class="tier-label">Logged in as: {st.session_state.get("user_email")} | Tier: **{st.session_state.get("user_tier", "Free Tier")}**</div>', unsafe_allow_html=True)
        st.markdown("## 🍎 Teacher Aid")

        # Set default to Usage Dashboard if not set
        if 'app_mode' not in st.session_state:
            st.session_state['app_mode'] = "Usage Dashboard"
            
        app_mode = st.radio(
            "Navigation",
            ["Usage Dashboard", "Resource Generation", "Saved History", "App Settings", "Tutorials"],
            index=["Usage Dashboard", "Resource Generation", "Saved History", "App Settings", "Tutorials"].index(st.session_state['app_mode']),
            key='app_mode_radio'
        )
        st.session_state['app_mode'] = app_mode

        st.markdown("---")
        st.button("Logout", on_click=logout)

    # 2. Page Rendering
    if st.session_state['app_mode'] == "Usage Dashboard":
        render_usage_dashboard()
    elif st.session_state['app_mode'] == "Resource Generation":
        render_teacher_aid_content()
    elif st.session_state['app_mode'] == "Saved History":
        render_saved_history_content()
    elif st.session_state['app_mode'] == "App Settings":
        render_app_settings()
    elif st.session_state['app_mode'] == "Tutorials":
        render_tutorials_content()

# --- RUN APP ---

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    if 'user_email' not in st.session_state: st.session_state['user_email'] = "teacher@example.com"
    if 'user_tier' not in st.session_state: st.session_state['user_tier'] = "Teacher Pro"

if st.session_state['logged_in']:
    render_main_app()
else:
    render_login_page()
