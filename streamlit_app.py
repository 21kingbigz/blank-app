import streamlit as st
import os
import pandas as pd
from PIL import Image
from io import BytesIO
import json
import re
import random
import time
from datetime import datetime, timedelta

# --- 1. CORE LIBRARY IMPORTS AND FALLBACK SETUP ---
# This ensures the app doesn't crash if the Gemini library isn't installed.
try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    # Set up mock objects for graceful failure
    genai = None
    APIError = type("APIError", (Exception,), {})
    # st.error("The 'google-genai' library is not installed. AI features will be mocked.")

# --- 2. MOCK AUTHENTICATION AND STORAGE LOGIC ---
# In a real deployment, these functions would interact with a database or external service.

def load_users():
    """Loads mock user credentials."""
    return {"teacher@example.com": {"password": "password123", "tier": "Teacher Pro"}}

def load_db_file(filename: str, initial_data: dict) -> dict:
    """Mock database loader using Streamlit's session state."""
    if filename not in st.session_state:
        st.session_state[filename] = initial_data.copy()
    return st.session_state[filename]

def load_storage_tracker():
    """Returns the mock storage tracker."""
    return load_db_file("storage_tracker", {})

def logout():
    """Clears session state and forces a refresh to the login screen."""
    st.session_state.clear()
    st.rerun()

def render_login_page():
    """Renders the simplified login form in the sidebar."""
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

# --- 3. CONFIGURATION AND INITIAL SETUP ---

WEBSITE_TITLE = "Artorius"
MODEL = 'gemini-2.5-flash'
LOGO_FILENAME = "image_ffd419.png" # Assuming a logo file exists
ICON_SETTING = "💡"

st.set_page_config(
    page_title=WEBSITE_TITLE,
    page_icon=ICON_SETTING,
    layout="wide",
    initial_sidebar_state="auto"
)

# --- 4. GEMINI CLIENT INITIALIZATION (API Key Fix) ---
client = None

def initialize_gemini_client():
    """
    Initializes the Gemini client, prioritizing the user-entered API key
    from session state over environment/secrets variables.
    This resolves the issue where the App Settings key wasn't binding correctly.
    """
    global client
    
    # Priority 1: User-entered key from App Settings (session state)
    api_key = st.session_state.get('user_gemini_api_key')
    
    # Priority 2: Environment/Secrets key
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None)

    if api_key and genai:
        try:
            genai.configure(api_key=api_key)
            client = genai.GenerativeModel(MODEL)
            # st.success("Gemini client successfully configured.") # Optional debugging message
        except Exception as e:
            client = None
            # st.error(f"Gemini API Setup Error: {e}")
    else:
        client = None # Ensure client is None if the key is missing or library is unavailable

initialize_gemini_client()


# --- 5. SYSTEM INSTRUCTION (Defines the 6 distinct resource formats) ---
# This lengthy instruction block ensures the model provides structured output.
SYSTEM_INSTRUCTION = """
You are the "Teacher Aid AI." Your response MUST be the direct, full output of the selected resource format. Do not add conversational text or pre-amble. Adhere strictly to the rubric below.

--- Teacher Resource Tags and Rubrics ---

* **Unit Overview:** Output must include four mandatory, clearly labelled sections: **A) Unit Objectives** (3-5 objectives), **B) Key Topics/Subtopics** (4-6 core topics), **C) Suggested Activities (3-5)**, and **D) Assessment Overview** (main methods, e.g., Test, Project).
* **Lesson Plan:** Output must follow a structured plan with four main sections: **A) Objective** (The measurable learning outcome), **B) Materials** (List of items needed), **C) Procedure (Warm-up, Main Activity, Wrap-up)**, and **D) Assessment Strategy** (How learning is checked).
* **Vocabulary List:** Output must be a list of 5-10 terms, where each entry contains three parts: **A) Term**, **B) Concise Definition** (1-2 sentences), and **C) Example Sentence** relevant to the topic.
* **Worksheet:** Output must be a numbered list of **10 varied questions** (must include matching, short answer, and fill-in-the-blank types) followed immediately by a separate **Answer Key** listing 10 corresponding answers.
* **Quiz:** Output must be a concise, **5-question Multiple Choice Quiz** with four options (A, B, C, D) for each question, followed by a separate **Answer Key** listing 5 answers.
* **Test:** Output must be comprehensive, organized into two main sections: **A) Multiple Choice (15 Questions)** and **B) Short/Long Answer (4 Questions)**. This must be followed by a detailed **Answer Key/Rubric** covering all 19 items.
"""

# --- 6. UI STYLING (For visual clarity) ---
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

# --- 7. MOCK GENERATION FUNCTIONS (Ensuring specific format adherence) ---

def mock_generate_unit_overview(topic: str) -> str:
    """Generates mock Unit Overview content based on the strict rubric."""
    return f"""### Unit Overview: {topic} (MOCK)
**A) Unit Objectives:**
1. Analyze the core themes of the {topic}.
2. Evaluate the historical context.
3. Synthesize information into a coherent argument.
**B) Key Topics/Subtopics:** Introduction, Primary Sources, Key Figures, Major Events, Conclusion.
**C) Suggested Activities (3-5):** 1. Timeline creation. 2. Paired reading. 3. Short essay response.
**D) Assessment Overview:** Final Test (70%) and Presentation (30%).
"""
def mock_generate_lesson_plan(topic: str) -> str:
    """Generates mock Lesson Plan content based on the strict rubric."""
    return f"""### Lesson Plan: {topic} (MOCK)
**A) Objective:** Students will accurately describe the main components of {topic}.
**B) Materials:** Whiteboard, internet access, copies of source material.
**C) Procedure:**
* Warm-up (5 min): Quick 2-question review.
* Main Activity (35 min): Guided discussion and note-taking.
* Wrap-up (5 min): Partner-share of key takeaways.
**D) Assessment Strategy:** Teacher observation during discussion and collection of notes.
"""
def mock_generate_vocabulary_list(topic: str) -> str:
    """Generates mock Vocabulary List content based on the strict rubric."""
    return f"""### Vocabulary List: {topic} (MOCK)
1. **Term:** Hegemony. **Concise Definition:** Dominance by one country or social group over others. **Example Sentence:** The state established economic hegemony over its neighbors.
2. **Term:** Paradigm. **Concise Definition:** A typical example or pattern of something; a model. **Example Sentence:** The discovery shifted the entire scientific paradigm.
3. **Term:** Synthesis. **Concise Definition:** The combination of ideas to form a theory or system. **Example Sentence:** Her final paper was a synthesis of three different theories.
"""
def mock_generate_worksheet(topic: str) -> str:
    """Generates mock Worksheet content (10 questions + 10 answers)."""
    return f"""### Worksheet: {topic} (10 Questions - MOCK)
1. **Fill-in-the-Blank:** The primary catalyst for this event was the __________.
2. **Matching:** Match 'A' to its corresponding outcome 'B'.
3. **Short Answer:** Briefly explain why the event occurred in 1865.
... (Questions 4-10 continue)
**--- Answer Key (10 items) ---**
1. Economic disparity. 2. A-Outcome 2. 3. Due to legislative change X. ... (Answers 4-10 continue)
"""
def mock_generate_quiz(topic: str) -> str:
    """Generates mock Quiz content (5 MC questions + 5 answers)."""
    return f"""### Quiz: {topic} (5-Question Multiple Choice - MOCK)
1. Which is the main factor? (A, B, C, D) 2. What year was X founded? (A, B, C, D) 3. Who wrote Y? (A, B, C, D) 4. Which is not true? (A, B, C, D) 5. The definition of Z is? (A, B, C, D)
**--- Answer Key (5 items) ---**
1. C. 2. A. 3. B. 4. D. 5. A.
"""
def mock_generate_test(topic: str) -> str:
    """Generates mock Test content (15 MC + 4 Long Answer + Rubric)."""
    return f"""### Test: {topic} (19 Questions Total - MOCK)
**A) Multiple Choice (15 Questions)**
1. What year did the event start? (A, B, C, D) ... (Q2-Q15 continue)
**B) Short/Long Answer (4 Questions)**
16. Describe the long-term economic effects. (6 points)
17. Analyze the primary source attached. (10 points)
18. Define and provide an example of concept Z. (4 points)
19. Compare and contrast two major viewpoints on this topic. (8 points)
**--- Answer Key/Rubric (19 items) ---**
**A) Multiple Choice:** 1. B, 2. D, ... (Answers for 3-15)
**B) Short/Long Answer Rubric:** 16. (Must cover inflation and unemployment). 17. (Must identify bias and main argument). 18. (Definition + Example). 19. (Requires minimum 2 points of comparison and 2 points of contrast).
"""

TEACHER_RESOURCES = {
    "Unit Overview": mock_generate_unit_overview,
    "Lesson Plan": mock_generate_lesson_plan,
    "Vocabulary List": mock_generate_vocabulary_list,
    "Worksheet": mock_generate_worksheet,
    "Quiz": mock_generate_quiz,
    "Test": mock_generate_test,
}


# --- 8. PAGE RENDERING FUNCTIONS ---

def render_usage_dashboard():
    """
    Renders the Usage Dashboard with 4 distinct charts and KPI metrics.
    Data is generated to show a positive, upward trend.
    """
    st.title("📊 Usage Dashboard")
    st.markdown("##### Resource Generation Analytics")
    st.markdown("---")

    # --- Data Generation (Ensuring Upward Trend) ---
    num_days = 30
    date_range = pd.to_datetime(pd.date_range(end=datetime.now(), periods=num_days, freq='D'))
    
    # Calculate Resources Generated (Cumulative, Upward Trend)
    start_cumulative = 100 
    daily_increase = [random.randint(5, 20) for _ in range(num_days)]
    resources_generated = [start_cumulative + sum(daily_increase[:i+1]) for i in range(num_days)]
    
    # Other Mock Data
    daily_logins = [random.randint(5, 50) for _ in range(num_days)]
    saved_items = [random.randint(10, 80) for _ in range(num_days)]
    
    data = {
        'Date': date_range,
        'Resources Generated': resources_generated,
        'Users Logged In': daily_logins,
        'Total Saved Items': saved_items,
        'Worksheet': [random.randint(0, 30) for _ in range(num_days)],
        'Lesson Plan': [random.randint(0, 40) for _ in range(num_days)],
        'Quiz/Test Count': [random.randint(0, 25) for _ in range(num_days)],
    }
    df = pd.DataFrame(data).set_index('Date')

    # --- KPI Row ---
    st.subheader("Key Performance Indicators (KPIs)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Resources Generated (Lifetime)", f"{resources_generated[-1]:,}", "+15% MoM")
    col2.metric("Average Daily Logins (30D)", f"{df['Users Logged In'].mean():.1f}", "Stable")
    col3.metric("Storage Used (Mock GB)", f"{resources_generated[-1] * 0.001:.2f}", "Growing")
    st.markdown("---")


    # Graph 1 (Line Chart - Cumulative Resources Generated)
    st.subheader("1. Cumulative Resource Generation Trend (Growth)")
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


def run_teacher_aid_generation(resource_type: str, topic: str, grade_level: str, client) -> str:
    """
    Executes the generation process using the AI client or a mock function.
    Ensures the prompt includes the resource type and grade level for structured output.
    """
    if not topic:
        return ""

    st.info(f"Generating **{resource_type}** for **{topic}** (Grade {grade_level})...")

    if not client:
        # Fallback to Mock Generation
        mock_func = TEACHER_RESOURCES.get(resource_type)
        if mock_func:
            time.sleep(1) # Simulate network latency
            return mock_func(topic)
        return "Error: Generation logic not found."

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
    """Renders the Resource Generation interface."""
    st.title("✍️ Resource Generation")
    st.markdown("##### AI-Powered Teacher's Aid")
    st.markdown("---")

    # Resource Selection - Uses the 6 distinct types
    resource_type = st.radio(
        "Select Resource Type:",
        list(TEACHER_RESOURCES.keys()),
        horizontal=True
    )

    # Input Fields
    topic = st.text_input("Topic/Subject (e.g., The causes and effects of the French Revolution)")
    col1, col2 = st.columns(2)
    with col1:
        grade_level = st.selectbox("Grade Level", ["K-2", "3-5", "6-8", "9-12", "College"])

    if st.button(f"Generate {resource_type}", use_container_width=True, type="primary"):
        if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
            st.error("Please log in to use the resource generation tool.")
            return
        
        # Check if client is available before running
        if not client:
            st.warning("AI Client not fully initialized. Generating mock data. Please check **App Settings** for API key configuration.")
            
        with st.spinner("Contacting AI Model..."):
            generated_content = run_teacher_aid_generation(resource_type, topic, grade_level, client)

        if generated_content:
            st.session_state['last_generated_content'] = generated_content
            st.session_state['last_generated_type'] = resource_type
            st.session_state['last_generated_topic'] = topic

            st.subheader(f"Generated {resource_type} for: {topic}")
            st.markdown(generated_content)

            # Save Button
            if st.button("Save to History", key="save_teacher_aid"):
                st.session_state['teacher_aid_history'] = st.session_state.get('teacher_aid_history', [])
                st.session_state['teacher_aid_history'].insert(0, {
                    "type": resource_type,
                    "topic": topic,
                    "content": generated_content,
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                st.success(f"{resource_type} saved to history!")


def render_saved_history_content():
    """Renders the history of generated and saved resources."""
    st.title("💾 Saved History")
    st.markdown("---")
    history = st.session_state.get('teacher_aid_history', [])
    if not history:
        st.info("No saved resources yet. Use 'Resource Generation' to create and save content.")
        return
    st.write(f"Showing {len(history)} saved item(s):")
    
    # Display history items in reverse chronological order
    for i, item in enumerate(history):
        with st.expander(f"**{item['type']}: {item['topic']}** - *Saved {item['timestamp']}*"):
            st.markdown(item['content'])
            if st.button("Delete", key=f"delete_{i}"):
                history.pop(i)
                st.session_state['teacher_aid_history'] = history
                st.success("Item deleted.")
                st.rerun()

def render_app_settings():
    """Renders the application settings, including the crucial API Key input."""
    st.title("⚙️ App Settings")
    st.markdown("---")
    
    # --- API Key Configuration (The Fix) ---
    st.subheader("Gemini API Key Configuration")
    st.markdown(
        """
        Enter your **Gemini API Key** below to manually configure the AI model for this session.
        This setting will override any key stored in your environment or secrets file,
        ensuring the AI functions **work** immediately.
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
            st.rerun() # Rerun forces the client initialization to pick up the new key
        elif not user_key:
            if 'user_gemini_api_key' in st.session_state:
                del st.session_state['user_gemini_api_key']
                st.warning("API Key cleared. Rerunning to fall back to secrets.")
                st.rerun()
            else:
                st.warning("Please enter a valid API key.")
        else:
            st.error("Invalid API Key format. It should start with 'AIza'.")

    st.markdown("---")

    # --- Account Information ---
    st.subheader("Account Details")
    st.write(f"**User Email:** {st.session_state.get('user_email', 'N/A')}")
    st.write(f"**Current Tier:** {st.session_state.get('user_tier', 'Free Tier')}")
    st.markdown("_Contact support to upgrade your subscription._")


def render_tutorials_content():
    """Renders the help and tutorial section."""
    st.title("💡 Tutorials")
    st.markdown("##### Guidance on using the Teacher Aid Application")
    st.markdown("---")
    st.markdown("""
    ### 1. Resource Generation
    This is the core tool where the magic happens.
    * **Select Resource:** Choose the specific format you need (Unit Overview, Lesson Plan, etc.). Remember, **Quiz** is 5 MC questions, and **Test** is 15 MC + 4 Long Answer.
    * **Topic Input:** Provide clear, detailed instructions here. The quality of your input dictates the quality of the AI's output.
    
    ### 2. Usage Dashboard
    The dashboard helps you track your usage patterns.
    * **Cumulative Trend:** Monitor your overall resource creation rate.
    * **Resource Breakdown:** See which resource types (Worksheet, Lesson Plan, etc.) you use the most.

    ### 3. Troubleshooting: API Key
    If the generation button runs but only gives mock data, or throws an error:
    * Go to **App Settings**.
    * Enter your valid **Gemini API Key** and click **Save & Apply Key**. This resolves connectivity issues instantly.
    """)

# --- 9. MAIN APP EXECUTION FLOW ---

def render_main_app():
    """Handles sidebar navigation and directs rendering to the correct page function."""
    
    # 1. Sidebar Setup
    with st.sidebar:
        # Display logo or title
        st.header(WEBSITE_TITLE)
        st.markdown(f'<div class="tier-label">Logged in as: {st.session_state.get("user_email")} | Tier: **{st.session_state.get("user_tier", "Free Tier")}**</div>', unsafe_allow_html=True)
        st.markdown("## 🍎 Teacher Aid")

        # Set default to Usage Dashboard
        if 'app_mode' not in st.session_state:
            st.session_state['app_mode'] = "Usage Dashboard"
            
        # Navigation Radio Button
        navigation_options = ["Usage Dashboard", "Resource Generation", "Saved History", "App Settings", "Tutorials"]
        
        app_mode = st.radio(
            "Navigation",
            navigation_options,
            index=navigation_options.index(st.session_state['app_mode']),
            key='app_mode_radio'
        )
        st.session_state['app_mode'] = app_mode

        st.markdown("---")
        st.button("Logout", on_click=logout)

    # 2. Page Routing
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

# --- 10. ENTRY POINT ---

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    # Set mock defaults for first run
    if 'user_email' not in st.session_state: st.session_state['user_email'] = "teacher@example.com"
    if 'user_tier' not in st.session_state: st.session_state['user_tier'] = "Teacher Pro"

if st.session_state['logged_in']:
    render_main_app()
else:
    render_login_page()
