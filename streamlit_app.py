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
try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    genai = None
    APIError = type("APIError", (Exception,), {})

# --- 2. MOCK AUTHENTICATION AND STORAGE LOGIC ---
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
LOGO_FILENAME = "image_ffd419.png" 
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
    """Initializes the Gemini client, prioritizing the user-entered API key."""
    global client
    
    api_key = st.session_state.get('user_gemini_api_key')
    
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None)

    if api_key and genai:
        try:
            genai.configure(api_key=api_key)
            client = genai.GenerativeModel(MODEL)
        except Exception as e:
            client = None
    else:
        client = None 

initialize_gemini_client()


# --- 5. SYSTEM INSTRUCTION (FIXED: NO PRESET COUNTS) ---
SYSTEM_INSTRUCTION = """
You are the "Teacher Aid AI." Your response MUST be the direct, full output of the selected resource format. Do not add conversational text or pre-amble. Adhere strictly to the rubric below.

--- Teacher Resource Tags and Rubrics ---

* **Unit Overview:** Output must include four mandatory, clearly labelled sections: **A) Unit Objectives**, **B) Key Topics/Subtopics**, **C) Suggested Activities**, and **D) Assessment Overview**.
* **Lesson Plan:** Output must follow a structured plan with four main sections: **A) Objective**, **B) Materials**, **C) Procedure (Warm-up, Main Activity, Wrap-up)**, and **D) Assessment Strategy**.
* **Vocabulary List:** Output must be a list of terms, where each entry contains three parts: **A) Term**, **B) Concise Definition**, and **C) Example Sentence** relevant to the topic.
* **Worksheet:** Output must be a numbered list of varied questions (e.g., matching, short answer, fill-in-the-blank) followed immediately by a separate **Answer Key** corresponding to the generated questions.
* **Quiz:** Output must be a Multiple Choice Quiz with four options (A, B, C, D) for each question, followed by a separate **Answer Key**. The number of questions will be determined by the user's prompt.
* **Test:** Output must be organized into two main sections: **A) Multiple Choice Questions** and **B) Short/Long Answer Questions**. This must be followed by a detailed **Answer Key/Rubric** covering all generated items. The number of questions will be determined by the user's prompt.
"""

# --- 6. UI STYLING (FIX: Increased Size for Readability) ---
st.markdown(
    """
    <style>
    /* Base Font Size Increase */
    html, body, [class*="stApp"] {
        font-size: 110%; 
    }
    
    /* Header Scaling */
    h1 { font-size: 2.5em !important; }
    h2 { font-size: 2.0em !important; }
    h3 { font-size: 1.5em !important; }

    /* Key UI Elements */
    .stRadio > label {
        padding-right: 0;
        margin-bottom: 8px; 
        font-size: 1.1em;   
    }
    
    /* Input/Select Labels */
    .stTextInput label, .stSelectbox label {
        font-size: 1.15em;
        font-weight: bold;
    }

    /* Smaller elements (like tier tag) */
    .tier-label {
        font-size: 1.0em; 
        color: #888;
        margin-top: -10px; 
        margin-bottom: 25px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 7. MOCK GENERATION FUNCTIONS (FIXED: Outputs Instructions, not Content) ---

def mock_generate_unit_overview(topic: str) -> str:
    """Mock output provides the instruction set for the requested resource."""
    return f"""### Unit Overview Generation Instructions (MOCK)

This output was generated by the mock system because the API key is missing.

**To create the Unit Overview for '{topic}', the AI was instructed to:**
1.  Define 3-5 **Unit Objectives**.
2.  List 4-6 **Key Topics/Subtopics**.
3.  Suggest 3-5 **Activities**.
4.  Provide an **Assessment Overview** (e.g., Test and Project).
"""
def mock_generate_lesson_plan(topic: str) -> str:
    """Mock output provides the instruction set for the requested resource."""
    return f"""### Lesson Plan Generation Instructions (MOCK)

This output was generated by the mock system because the API key is missing.

**To create the Lesson Plan for '{topic}', the AI was instructed to:**
1.  Define a single, measurable **Objective**.
2.  List **Materials** needed.
3.  Structure a **Procedure** into Warm-up, Main Activity, and Wrap-up.
4.  Provide an **Assessment Strategy**.
"""
def mock_generate_vocabulary_list(topic: str) -> str:
    """Mock output provides the instruction set for the requested resource."""
    return f"""### Vocabulary List Generation Instructions (MOCK)

This output was generated by the mock system because the API key is missing.

**To create the Vocabulary List for '{topic}', the AI was instructed to:**
1.  Generate 5-10 terms relevant to the topic.
2.  For each term, provide a **Concise Definition** and an **Example Sentence**.
"""
def mock_generate_worksheet(topic: str) -> str:
    """Mock output provides the instruction set for the requested resource."""
    return f"""### Worksheet Generation Instructions (MOCK)

This output was generated by the mock system because the API key is missing.

**To create the Worksheet for '{topic}', the AI was instructed to:**
1.  Generate a numbered list of varied questions (matching, short answer, fill-in-the-blank). The number of questions should be based on the user's specific prompt.
2.  Follow this immediately with a corresponding **Answer Key**.
"""
def mock_generate_quiz(topic: str) -> str:
    """Mock output provides the instruction set for the requested resource."""
    return f"""### Quiz Generation Instructions (MOCK)

This output was generated by the mock system because the API key is missing.

**To create the Quiz for '{topic}', the AI was instructed to:**
1.  Generate Multiple Choice Questions with four options (A, B, C, D). **The number of questions is set by the user's prompt.**
2.  Follow this immediately with a corresponding **Answer Key**.
"""
def mock_generate_test(topic: str) -> str:
    """Mock output provides the instruction set for the requested resource."""
    return f"""### Test Generation Instructions (MOCK)

This output was generated by the mock system because the API key is missing.

**To create the Test for '{topic}', the AI was instructed to:**
1.  Generate a Test organized into **A) Multiple Choice Questions** and **B) Short/Long Answer Questions**. **The number of questions for both sections is set by the user's prompt.**
2.  Follow this immediately with a detailed **Answer Key/Rubric**.
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
    """Renders the Usage Dashboard with 4 distinct charts and KPI metrics."""
    st.title("📊 Usage Dashboard")
    st.markdown("##### Resource Generation Analytics")
    st.markdown("---")

    # --- Data Generation (Ensuring Upward Trend) ---
    num_days = 30
    date_range = pd.to_datetime(pd.date_range(end=datetime.now(), periods=num_days, freq='D'))
    
    start_cumulative = 100 
    daily_increase = [random.randint(5, 20) for _ in range(num_days)]
    resources_generated = [start_cumulative + sum(daily_increase[:i+1]) for i in range(num_days)]
    
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
    The prompt is built to rely on the user's input for specific resource details (like question count).
    """
    if not topic:
        return ""

    st.info(f"Generating **{resource_type}** for **{topic}** (Grade {grade_level})...")

    if not client:
        # Fallback to Mock Generation (now outputs instructions)
        mock_func = TEACHER_RESOURCES.get(resource_type)
        if mock_func:
            time.sleep(1) # Simulate network latency
            return mock_func(topic)
        return "Error: Generation logic not found."

    # --- AI GENERATION CALL (Actual content generation relies on prompt) ---
    prompt = f"Topic: {topic}. Grade Level: {grade_level}. Resource Type: {resource_type}. **Include all requested question counts or specifications mentioned in the Topic field.**"
    
    full_prompt = f"{SYSTEM_INSTRUCTION}\n\nBased on the resource type '{resource_type}', and the prompt: '{prompt}', generate the full, structured output according to the rubric."

    try:
        response = client.generate_content(
            full_prompt,
            system_instruction=SYSTEM_INSTRUCTION
        )
        # For actual AI output, we just return the text
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

    # Input Fields - Topic should contain specific counts (e.g., "10 MC questions")
    st.markdown(f"**Topic/Subject** (If creating a Quiz or Test, specify the question count here, e.g., 'The French Revolution: create 8 MC questions and 2 long answer questions')")
    topic = st.text_input("Topic/Subject Input")
    
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
            # IMPORTANT: Re-initialize client immediately after saving
            initialize_gemini_client() 
            st.success("API Key saved and applied for this session! Rerunning app to confirm initialization.")
            st.rerun()
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
    * **Crucial Tip:** When generating a **Quiz** or **Test**, you must specify the exact number of questions you want in the **Topic/Subject** input field (e.g., "12 multiple choice questions on atomic structure"). The AI will follow your count.
    * **Structure:** The output will follow a strict format (e.g., Test = Multiple Choice section + Long Answer section + Answer Key).
    
    ### 2. Usage Dashboard
    The dashboard helps you track your usage patterns.
    * **Cumulative Trend:** Monitor your overall resource creation rate.
    * **Resource Breakdown:** See which resource types (Worksheet, Lesson Plan, etc.) you use the most.

    ### 3. Troubleshooting: API Key
    If the generation button runs but only gives mock instruction output, or throws an error:
    * Go to **App Settings**.
    * Enter your valid **Gemini API Key** and click **Save & Apply Key**. This resolves connectivity issues instantly.
    """)

# --- 9. MAIN APP EXECUTION FLOW ---

def render_main_app():
    """Handles sidebar navigation and directs rendering to the correct page function."""
    
    # 1. Sidebar Setup
    with st.sidebar:
        st.header(WEBSITE_TITLE)
        st.markdown(f'<div class="tier-label">Logged in as: {st.session_state.get("user_email")} | Tier: **{st.session_state.get("user_tier", "Free Tier")}**</div>', unsafe_allow_html=True)
        st.markdown("## 🍎 Teacher Aid")

        if 'app_mode' not in st.session_state:
            st.session_state['app_mode'] = "Usage Dashboard"
            
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
    if 'user_email' not in st.session_state: st.session_state['user_email'] = "teacher@example.com"
    if 'user_tier' not in st.session_state: st.session_state['user_tier'] = "Teacher Pro"

if st.session_state['logged_in']:
    render_main_app()
else:
    render_login_page()
