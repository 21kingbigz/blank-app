import streamlit as st
import os
import pandas as pd
from PIL import Image
from io import BytesIO
import json
import re
import random
import time

# --- Ensure you have google-genai installed and configured if you want real AI calls ---
try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    st.error("The 'google-genai' library is not installed. Please install it using: pip install google-genai")
    genai = None
    APIError = type("APIError", (Exception,), {})

# --- MOCK IMPORTS AND INITIAL DATA (REQUIRED FOR THE "FULL WORKING THING" SCRIPT) ---

# Mock the structure of external authentication and storage files
# In a real app, these would be separate files.

def load_users():
    return {"teacher@example.com": {"password": "password123", "tier": "Teacher Pro"}}
def load_plan_overrides(email):
    return {"limit": 100}

# Mock Storage Logic
UTILITY_DB_INITIAL = {"utility_history": [], "utility_count": 0}
TEACHER_DB_INITIAL = {"teacher_history": [], "teacher_count": 0}
TIER_LIMITS = {"Free Tier": 5, "Teacher Pro": 100, "Universal Pro": 150, "Unlimited": float('inf')}

def load_db_file(filename, initial_data):
    if filename not in st.session_state:
        st.session_state[filename] = initial_data.copy()
    return st.session_state[filename]

def save_db_file(filename, data):
    st.session_state[filename] = data
    return True

def load_storage_tracker():
    return load_db_file("storage_tracker", {})
def save_storage_tracker(data):
    save_db_file("storage_tracker", data)

def check_storage_limit(email, app_mode):
    storage_tracker = load_storage_tracker()
    count = storage_tracker.get(f"{email}_{app_mode}_count", 0)
    limit = TIER_LIMITS.get(st.session_state.get('user_tier'), TIER_LIMITS['Free Tier'])
    return count < limit, count, limit

def calculate_mock_save_size(content):
    return random.uniform(0.01, 0.5)

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

def logout():
    st.session_state.clear()
    st.rerun()

# --- END MOCK IMPORTS ---

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
client = None # Default to None

try:
    # Priority 1: Check for user-entered key in the current session
    api_key = st.session_state.get('user_gemini_api_key')

    # Priority 2: Check for key in environment variables or Streamlit secrets
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

    if api_key and genai:
        # 2. Only proceed to configure and initialize if the key is found
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel(MODEL)
    else:
        # Key not found or genai not imported, client remains None.
        pass

except Exception as e:
    client = None
    # st.error(f"Gemini API Setup Error: {e}") # Debugging
# --- END INITIALIZE GEMINI CLIENT ---

# --- SYSTEM INSTRUCTION LOADING (RAW CONTENT) ---
SYSTEM_INSTRUCTION_FALLBACK = """
You are the "28-in-1 Stateless AI Utility Hub." Your response MUST be the direct result of the selected function.

--- Teacher Resource Tags ---
The following terms trigger specific, detailed output formats when requested from the separate Teacher's Aid mode:

* **Unit Overview:** Output must include four sections: **A) Unit Objectives**, **B) Key Topics/Subtopics**, **C) Suggested Activities (3-5)**, and **D) Assessment Overview**.
* **Lesson Plan:** Output must follow a structured plan: **A) Objective**, **B) Materials**, **C) Procedure (Warm-up, Main Activity, Wrap-up)**, and **D) Assessment Strategy**.
* **Vocabulary List:** Output must be a list of terms, each entry containing: **A) Term**, **B) Concise Definition**, and **C) Example Sentence** relevant to the topic.
* **Worksheet:** Output must be a numbered list of **10 varied questions** (e.g., matching, short answer, fill-in-the-blank) followed by a separate **Answer Key** (10 items).
* **Quiz:** Output must be a **5-question Multiple Choice Quiz** with four options for each question, followed by a separate **Answer Key** (5 items).
* **Test:** Output must be organized into two main sections: **A) Multiple Choice (15 Questions)** and **B) Short/Long Answer (4 Questions)**, followed by a detailed **Answer Key/Rubric** (19 items total).
"""

try:
    with open("system_instruction.txt", "r") as f:
        SYSTEM_INSTRUCTION = f.read()
except FileNotFoundError:
    SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_FALLBACK
    # st.warning("`system_instruction.txt` file not found. Using hardcoded fallback instructions.")

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

# --- TEACHER AID MOCK FUNCTIONS (Quiz and Test are now separate) ---
def mock_generate_unit_overview(topic: str) -> str:
    return f"""### Unit Overview: The American Civil War

**A) Unit Objectives:** Students will identify key causes, major battles, and resulting constitutional amendments.
**B) Key Topics/Subtopics:** Causes of the War, Key Battles (Gettysburg, Vicksburg), Emancipation Proclamation, Reconstruction.
**C) Suggested Activities (3-5):**
1. Primary Source Analysis of Lincoln's Speeches.
2. Debate: Was the Civil War inevitable?
3. Mapping the Western and Eastern Theatres.
**D) Assessment Overview:** A comprehensive Test (see Test format) and a Unit Project on a figure of their choice.
"""

def mock_generate_lesson_plan(topic: str) -> str:
    return f"""### Lesson Plan: Introduction to Photosynthesis

**A) Objective:** Students will be able to describe the process of photosynthesis and write its chemical equation.
**B) Materials:** Whiteboard, Markers, Green Plants, Flask of water, Overhead projector.
**C) Procedure:**
* **Warm-up (10 min):** Quick-write: What do plants need to survive?
* **Main Activity (30 min):** Lecture and Diagramming of the chemical equation. Group work on a flow-chart.
* **Wrap-up (10 min):** Exit ticket: Write the formula for photosynthesis.
**D) Assessment Strategy:** Formative assessment via the exit ticket; Summative assessment via the Unit Test.
"""

def mock_generate_vocabulary_list(topic: str) -> str:
    return f"""### Vocabulary List: Ancient Rome

1.  **Term:** Patrician
    * **Concise Definition:** A member of a noble family in ancient Rome.
    * **Example Sentence:** As a Patrician, he held significant political power and inherited wealth.
2.  **Term:** Plebeian
    * **Concise Definition:** A common person in ancient Rome.
    * **Example Sentence:** The Plebeians often protested for equal rights against the Patricians.
3.  **Term:** Aqueduct
    * **Concise Definition:** An artificial channel for conveying water, typically in the form of a bridge supported by tall columns.
    * **Example Sentence:** Roman engineering was defined by massive stone aqueducts.
"""

def mock_generate_worksheet(topic: str) -> str:
    return f"""### Worksheet: Basic Algebra Concepts (Answer Key Attached)

**Instructions:** Answer the following 10 questions.
1.  **Fill-in-the-Blank:** The letter used to represent an unknown value is called a(n) __________.
2.  **Short Answer:** Explain the distributive property.
3.  Solve for x: $3x - 5 = 10$.
4.  If $y = 2x + 1$, what is $y$ when $x = 4$?
... (Questions 5-10 continue)

**--- Answer Key ---**
1. Variable
2. Multiplying a sum by a number gives the same result as multiplying each addend by the number and then adding the products.
3. $x=5$
4. $y=9$
... (Answers 5-10 continue)
"""

def mock_generate_quiz(topic: str) -> str:
    return f"""### Quiz: The Renaissance (5 Questions)

1.  Which city is considered the birthplace of the Renaissance?
    * A) Rome
    * B) Venice
    * C) Florence
    * D) Naples
2.  What was Leonardo da Vinci famous for, besides art?
    * A) Political Theory
    * B) Engineering and Anatomy
    * C) Naval Command
    * D) Religious Reform
... (Questions 3-5 continue)

**--- Answer Key ---**
1. C) Florence
2. B) Engineering and Anatomy
3. (Answer for Q3)
4. (Answer for Q4)
5. (Answer for Q5)
"""

def mock_generate_test(topic: str) -> str:
    return f"""### Test: World War I and Its Aftermath (19 Questions)

**A) Multiple Choice (15 Questions)**
1.  What year did the United States enter WWI?
    * A) 1914
    * B) 1917
    * C) 1918
    * D) 1919
2.  Which country was NOT a member of the Central Powers?
    * A) Germany
    * B) Austria-Hungary
    * C) Ottoman Empire
    * D) Italy
... (Questions 3-15 continue)

**B) Short/Long Answer (4 Questions)**
16. Describe the key differences between trench warfare and the Eastern Front.
17. Analyze the impact of the Treaty of Versailles on Germany's political future.
18. Define and give an example of **total war**.
19. (Question 19)

**--- Answer Key/Rubric ---**
**A) Multiple Choice:** 1. B, 2. D, ... (Answers for 3-15)
**B) Short/Long Answer Rubric (Partial):**
16. (4 Points): Must mention stalemate on the Western Front, high mobility on the Eastern Front.
17. (5 Points): Must discuss punitive reparations, 'war guilt' clause, and territorial losses leading to political instability.
18. (3 Points): Must define total war (mobilization of all resources) and provide an example (e.g., rationing, propaganda).
19. (Answer for Q19)
"""

TEACHER_RESOURCES = {
    "Unit Overview": mock_generate_unit_overview,
    "Lesson Plan": mock_generate_lesson_plan,
    "Vocabulary List": mock_generate_vocabulary_list,
    "Worksheet": mock_generate_worksheet,
    "Quiz": mock_generate_quiz,
    "Test": mock_generate_test,
}

# --- APPLICATION MODES ---
def render_usage_dashboard():
    """
    Renders the Usage Dashboard with 4 distinct analytical graphs/views.
    """
    st.title("📊 Usage Dashboard")
    st.markdown("##### Resource Generation Analytics")
    st.markdown("---")

    # Mock Data for Dashboard
    data = {
        'Date': pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')),
        'Resources Generated': [random.randint(20, 150) for _ in range(30)],
        'Users Logged In': [random.randint(5, 50) for _ in range(30)],
        'Total Saved Items': [random.randint(10, 80) for _ in range(30)],
        'Worksheet': [random.randint(0, 30) for _ in range(30)],
        'Lesson Plan': [random.randint(0, 40) for _ in range(30)],
        'Quiz/Test': [random.randint(0, 25) for _ in range(30)],
    }
    df = pd.DataFrame(data).set_index('Date')

    # Row 1: Key Metrics
    st.subheader("Key Performance Indicators (KPIs)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Resources Generated (Lifetime)", "1,245", "+12% MoM")
    col2.metric("Active Teacher Users", "150", "30 New")
    col3.metric("Storage Used", "1.2 GB", "-50 MB")

    st.markdown("---")

    # Row 2: Graph 1 (Line Chart - Resources Generated Over Time)
    st.subheader("1. Daily Resource Generation Trend")
    st.line_chart(df['Resources Generated'])

    # Row 3: Graph 2 (Bar Chart - User Activity)
    st.subheader("2. Daily User Logins")
    st.bar_chart(df['Users Logged In'])

    st.markdown("---")

    # Row 4: Graph 3 (Stacked Bar - Top 3 Resource Types Over Time)
    st.subheader("3. Top 3 Resource Types Generated (Last 30 Days)")
    top_resource_df = df[['Worksheet', 'Lesson Plan', 'Quiz/Test']]
    st.bar_chart(top_resource_df, use_container_width=True)

    # Row 5: Graph 4 (Data Table - Saved Item Growth)
    st.subheader("4. Growth in Saved Items (Last 7 Days)")
    st.dataframe(df[['Total Saved Items']].tail(7), use_container_width=True)

    st.markdown("---")


def run_teacher_aid_generation(resource_type, topic, grade_level, client):
    """Handles the Teacher Aid generation workflow (Mocked AI call)."""
    if not topic:
        st.error("Please enter a topic to generate a resource.")
        return

    st.info(f"Generating **{resource_type}** for **{topic}** (Grade {grade_level})...")

    # --- MOCK GENERATION ---
    mock_func = TEACHER_RESOURCES.get(resource_type)
    if mock_func:
        time.sleep(1) # Simulate generation time
        mock_output = mock_func(topic)
        st.subheader(f"Generated {resource_type}:")
        st.markdown(mock_output)
        return mock_output

    st.error("Generation function not found for this resource type.")
    return None

def render_teacher_aid_content():
    st.title("✍️ Resource Generation")
    st.markdown("##### AI-Powered Teacher's Aid")
    st.markdown("---")

    # Resource Selection (All 6 distinct types)
    resource_type = st.radio(
        "Select Resource Type:",
        list(TEACHER_RESOURCES.keys()),
        horizontal=True
    )

    # Input Fields
    topic = st.text_input("Topic/Subject (e.g., Introduction to Photosynthesis)")
    col1, col2 = st.columns(2)
    with col1:
        grade_level = st.selectbox("Grade Level", ["K-2", "3-5", "6-8", "9-12", "College"])

    # Generation Button
    if st.button(f"Generate {resource_type}", use_container_width=True, type="primary"):
        if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
            st.error("Please log in to use the resource generation tool.")
            return

        # Check API Key Status
        if not client:
            st.error("AI Client is not initialized. Please ensure your Gemini API Key is set correctly in **App Settings**.")
            return

        with st.spinner("Contacting AI Model..."):
            generated_content = run_teacher_aid_generation(resource_type, topic, grade_level, client)

        if generated_content:
            st.session_state['last_generated_content'] = generated_content
            st.session_state['last_generated_type'] = resource_type
            st.session_state['last_generated_topic'] = topic

            # Mock Save Logic
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
    st.markdown("##### Review and Reuse Generated Resources")
    st.markdown("---")

    history = st.session_state.get('teacher_aid_history', [])

    if not history:
        st.info("No saved resources yet. Use the 'Resource Generation' tab to create and save content.")
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

    # --- API Key Input (Fixing the binding issue) ---
    st.subheader("Gemini API Key Configuration")
    st.markdown(
        """
        Enter your **Gemini API Key** below to manually configure the AI model for this session.
        This key takes priority over any key saved in the deployment secrets.
        """
    )
    # Use a consistent key for session state
    user_key = st.text_input(
        "API Key",
        type="password",
        value=st.session_state.get('user_gemini_api_key', '')
    )

    if st.button("Save & Apply Key"):
        # Very basic validation
        if user_key and user_key.startswith("AIza"):
            st.session_state['user_gemini_api_key'] = user_key
            st.session_state['api_key_applied'] = True
            st.success("API Key saved and applied for this session! Rerunning app to initialize AI client.")
            st.rerun()
        elif not user_key:
            # Clear the key if the user submits an empty field
            if 'user_gemini_api_key' in st.session_state:
                del st.session_state['user_gemini_api_key']
                st.session_state['api_key_applied'] = False
                st.warning("API Key cleared. Falling back to Streamlit Secrets.")
                st.rerun()
            else:
                st.warning("Please enter a valid API key.")
        else:
            st.error("Invalid API Key format. Key must start with 'AIza...'")

    st.markdown("---")

    # --- Existing Settings ---
    st.subheader("Tier & Limits")
    st.write(f"**Current Tier:** {st.session_state.get('user_tier', 'Free Tier')}")
    st.write("Limits and subscription details go here.")

def render_tutorials_content():
    st.title("💡 Tutorials")
    st.markdown("##### Learn How to Maximize Your Teacher's Aid")
    st.markdown("---")
    st.markdown("""
    Welcome! Here is a brief guide on the main functions:

    ### 1. Resource Generation (The core tool)
    * **Goal:** Create tailored teaching materials quickly.
    * **How to Use:**
        1.  Select the desired resource type (e.g., Unit Overview, Quiz).
        2.  Enter a detailed **Topic** (e.g., "The causes and effects of the French Revolution").
        3.  Click **Generate**.
    * **Tip:** The more detailed your topic, the better the output!

    ### 2. Saved History
    * **Goal:** Keeps a repository of all generated resources.
    * **How to Use:** After generating content, click the **'Save to History'** button that appears below the result.

    ### 3. Usage Dashboard
    * **Goal:** Monitor your resource usage and track user activity.
    * **What to look for:** Trends in generation, peak usage times, and the popularity of different resource types.
    """)

# --- MAIN APP LOGIC ---

def render_main_app():
    # 1. Sidebar Navigation
    with st.sidebar:
        try:
            # Attempt to display the logo file (must be in the same directory or accessible path)
            logo = Image.open(LOGO_FILENAME)
            st.image(logo, use_column_width=True)
        except FileNotFoundError:
            st.header(WEBSITE_TITLE)

        st.markdown(f'<div class="tier-label">Logged in as: {st.session_state.get("user_email")} | Tier: **{st.session_state.get("user_tier")}**</div>', unsafe_allow_html=True)

        st.markdown("## 🍎 Teacher Aid")

        app_mode = st.radio(
            "Navigation",
            ["Usage Dashboard", "Resource Generation", "Saved History", "App Settings", "Tutorials"],
            index=0 if st.session_state.get('app_mode') == "Usage Dashboard" else (
                1 if st.session_state.get('app_mode') == "Resource Generation" else (
                2 if st.session_state.get('app_mode') == "Saved History" else (
                3 if st.session_state.get('app_mode') == "App Settings" else 4
            ))),
        )
        st.session_state['app_mode'] = app_mode

        st.markdown("---")
        st.button("Logout", on_click=logout)

    # 2. Page Rendering based on Selection
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
    else:
        # Default to Dashboard
        render_usage_dashboard()

# --- RUN APP ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    # Set default app mode to the dashboard upon initial load before login
    st.session_state['app_mode'] = "Usage Dashboard"


if st.session_state['logged_in']:
    render_main_app()
else:
    render_login_page()
