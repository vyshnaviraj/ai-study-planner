import os
import time
from dotenv import load_dotenv
import streamlit as st
import pandas as pd

# Try/except block for the AI-specific imports to handle potential errors
try:
    from langchain_groq import ChatGroq
    from langchain_core.output_parsers import StrOutputParser
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    st.warning("AI features are disabled. Make sure langchain-groq is installed.")

# Load environment variables
load_dotenv()

def LLM_Setup(prompt):
    """Function to generate AI responses using Groq's LLM API"""
    if not AI_AVAILABLE:
        return "AI functionality is currently unavailable. Please check your installation."
        
    try:
        # Check if API key exists
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "Missing API key. Please add GROQ_API_KEY to your .env file."
            
        model = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=api_key
        )

        parser = StrOutputParser()
        chain = model | parser
        output = chain.invoke(prompt)
        return output
    except Exception as e:
        error_msg = str(e)
        st.error(f"Error with AI generation: {error_msg}")
        return f"Could not generate AI response: {error_msg}"

# Input form for subjects and duration
st.title("FocusFlow")
st.subheader("Your AI-enhanced study planner")

# Initialize session state variables if they don't exist
if 'plan_generated' not in st.session_state:
    st.session_state['plan_generated'] = False
if 'table_data' not in st.session_state:
    st.session_state['table_data'] = []
if 'num_subjects' not in st.session_state:
    st.session_state['num_subjects'] = 1

# Function to update number of subjects
def update_num_subjects():
    st.session_state['num_subjects'] = st.session_state['num_subjects_input']

# User inputs
num_subjects = st.number_input(
    "Number of Subjects", 
    min_value=1, 
    max_value=20, 
    value=st.session_state['num_subjects'],
    step=1,
    key='num_subjects_input',
    on_change=update_num_subjects
)

with st.form("study_plan_form"):
    # Store the current number of subjects in session state
    st.session_state['num_subjects'] = num_subjects
    
    subject_data = []
    priority_options = ["High", "Medium", "Low"]
    
    # Create subject inputs in the form
    for i in range(st.session_state['num_subjects']):
        col1, col2 = st.columns([2, 1])
        with col1:
            subj = st.text_input(f"Subject {i+1}", key=f"subject_{i}")
        with col2:
            prio = st.selectbox(f"Priority {i+1}", priority_options, key=f"priority_{i}")
        subject_data.append({"subject": subj, "priority": prio})
    
    duration = st.text_input("Total Study Hours per Day", value="8")
    
    # Submit button
    submitted = st.form_submit_button("Generate Plan")
    
    if submitted:
        # Validate inputs
        if not all(sd["subject"] for sd in subject_data):
            st.error("Please enter names for all subjects.")
            st.stop()
            
        try:
            total_hours = float(duration)
            if total_hours <= 0:
                st.error("Total hours must be greater than zero.")
                st.stop()
        except ValueError:
            st.error("Please enter a valid number for total hours.")
            st.stop()

        # Process data and generate the plan
        with st.spinner("Generating your study plan..."):
            priority_weights = {"High": 3, "Medium": 2, "Low": 1}
            total_weight = sum(priority_weights[sd["priority"]] for sd in subject_data)
            
            if total_weight == 0:
                st.error("Unable to calculate time allocation. Please check your inputs.")
                st.stop()
            
            # Prepare the table data
            table_data = []
            for sd in subject_data:
                weight = priority_weights[sd["priority"]]
                allocated_time = (weight / total_weight) * total_hours
                hrs = int(allocated_time)
                mins = int((allocated_time - hrs) * 60)
                allocated_str = f"{hrs}hr" if mins == 0 else f"{hrs}hr {mins}min"

                
                # Only generate AI tips if the feature is available and enabled
                study_tips = "AI study tips unavailable. Please check your configuration."
                if AI_AVAILABLE:
                    prompt = f"""
                    Provide short, practical study tips for a student studying {sd["subject"]}.
                    They have allocated {hrs} hours and {mins} minutes for this subject with {sd["priority"]} priority.
                    Keep your response under 100 words and focus on study techniques, time management, 
                    and effective learning strategies specific to this subject.
                    """
                    try:
                        study_tips = LLM_Setup(prompt)
                    except Exception as e:
                        study_tips = f"Could not generate AI tips: {str(e)}"
                
                table_data.append({
                    "Subject": sd["subject"],
                    "Priority": sd["priority"],
                    "Allocated Time": allocated_str,
                    "Pomodoro Minutes": 25,  # Default Pomodoro time
                    "Completed": False,
                    "Study Tips": study_tips
                })
            
            # Save to session state
            st.session_state['table_data'] = table_data
            st.session_state['plan_generated'] = True
            
        st.success("Study plan generated successfully!")

# Render the study plan table if generated
if st.session_state.get('plan_generated', False):
    st.write("### Your Study Plan")
    
    # Create a DataFrame for the main table view
    table_df = pd.DataFrame(st.session_state['table_data'])
    
    # Display only the main columns in the table
    if not table_df.empty:
        display_df = table_df[["Subject", "Priority", "Allocated Time", "Pomodoro Minutes"]]
        st.dataframe(display_df, use_container_width=True)
    
    # Create individual sections for each subject with timer functionality
    for idx, row in enumerate(st.session_state['table_data']):
        st.write("---")
        
        # Three columns for layout
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.subheader(row['Subject'])
            st.write(f"**Priority:** {row['Priority']}")
            st.write(f"**Allocated Time:** {row['Allocated Time']}")
            
            # Add the AI study tips in an expander
            if "Study Tips" in row and row["Study Tips"]:
                with st.expander("AI Study Tips", expanded=False):
                    st.write(row["Study Tips"])
        
        with col2:
            # Pomodoro timer settings
            pomodoro_key = f"pomodoro_{idx}"
            current_pomodoro = st.session_state['table_data'][idx].get('Pomodoro Minutes', 25)
            
            # Slider for pomodoro duration
            pomodoro_time = st.slider(
                f"Pomodoro duration (minutes)",
                min_value=5, 
                max_value=60, 
                value=current_pomodoro,
                step=5,
                key=pomodoro_key
            )
            
            # Update session state with new pomodoro time
            st.session_state['table_data'][idx]['Pomodoro Minutes'] = pomodoro_time
            
            # Timer countdown placeholder
            timer_placeholder = st.empty()
            
            # Function to handle the timer countdown
            def start_timer(subject, duration_minutes):
                start_time = time.time()
                end_time = start_time + (duration_minutes * 60)
                
                while time.time() < end_time:
                    remaining = end_time - time.time()
                    mins, secs = divmod(int(remaining), 60)
                    timer_placeholder.markdown(f"### ⏳ {mins:02d}:{secs:02d}")
                    time.sleep(1)
                
                # When timer finishes
                timer_placeholder.markdown("### ✅ Time's up!")
                
                # Get AI break suggestion if available
                if AI_AVAILABLE:
                    try:
                        break_prompt = f"""
                        The student just finished a {duration_minutes}-minute study session on {subject}.
                        Suggest a quick 5-minute break activity that will help refresh their mind. 
                        Keep it under 30 words and make it specific.
                        """
                        break_suggestion = LLM_Setup(break_prompt)
                        st.success(f"Break suggestion: {break_suggestion}")
                    except Exception:
                        st.info("Take a quick 5-minute break before continuing.")
                else:
                    st.info("Take a quick 5-minute break before continuing.")
            
            # Start timer button
            if st.button(f"Start Timer", key=f"start_{idx}"):
                start_timer(row['Subject'], pomodoro_time)
        
        with col3:
            # Completion checkbox
            completion_key = f"complete_{idx}"
            completed = st.checkbox(
                "Completed",
                value=row.get('Completed', False),
                key=completion_key
            )
            
            # Update session state with completion status
            st.session_state['table_data'][idx]['Completed'] = completed
            
            if completed:
                st.success("✅ Well done!")
    