import streamlit as st
import pandas as pd
import os
from datetime import datetime
import re
import csv
from io import StringIO # Needed for handling CSV data in Streamlit

# --- Global Configurations ---
# Note: In Streamlit, we often use a dedicated directory for data files.
# Using session state for data storage is generally better for web apps.

# Define the file path for the CSV (or use a simple name if running locally)
FILE_NAME = 'job_applications.csv' 
ALLOWED_STATUSES = ["Submitted", "Interviewing", "Rejected", "Not Submitted"]
URL_REGEX = r"https?://(?:www\.|(?!www\.))[a-zA-Z0-9]+\.[^\s]{2,}"
HEADERS = ['Job_Title', 'Company', 'Date_Submitted', 'Requirements_Matched', 'Link', 'Status', "Require_Enhancement"]

# --- Utility Functions ---

@st.cache_data
def load_data():
    """
    Loads data from the CSV file into a DataFrame.
    Uses Streamlit's cache to avoid re-reading the file unnecessarily.
    """
    if not os.path.exists(FILE_NAME):
        # Create an empty DataFrame with headers if the file doesn't exist
        df = pd.DataFrame(columns=HEADERS)
    else:
        try:
            df = pd.read_csv(FILE_NAME)
        except Exception:
            # Handle corrupted or empty file by starting fresh
            df = pd.DataFrame(columns=HEADERS)
    
    return df

def save_data(df):
    """Saves the current DataFrame back to the CSV file."""
    try:
        df.to_csv(FILE_NAME, index=False)
        st.success(f"Data saved successfully to {FILE_NAME}")
    except Exception as e:
        st.error(f"Error saving data: {e}")

# --- Core Application Functions (Simplified for Streamlit) ---

def show_data_view(df):
    """Displays the current job applications data."""
    st.header("📋 Job Applications Data")
    if df.empty:
        st.info("The tracker is currently empty. Add a new entry to get started!")
    else:
        st.dataframe(df, use_container_width=True)
        st.markdown(f"**Total Entries:** {len(df)}")

def show_add_entry_form(df):
    """Streamlit form for adding a new entry."""
    st.header("➕ Add New Job Application")

    with st.form("add_form", clear_on_submit=True):
        # 1. Collect inputs from the user
        job_title = st.text_input("1. Job Title (e.g., Senior Data Engineer):")
        company = st.text_input("2. Company Name:")
        
        # 3. Requirements
        requirements = st.text_input("3. Number of matched requirements (e.g., 7/10):")
        
        # 7. Enhancement
        require_enhancement = st.text_area("7. Learning Focus (Skills to develop for this role):")

        # 4. Link Validation
        job_link = st.text_input("4. Job Link Address (e.g., https://example.com/job):").strip()
        if job_link and not re.fullmatch(URL_REGEX, job_link):
            st.warning("❌ Invalid URL Format. Please enter a full link starting with http:// or https://.")
            
        # 5. Status Validation
        status = st.selectbox("5. Application Status:", options=ALLOWED_STATUSES)

        submitted = st.form_submit_button("💾 Save Entry")

        if submitted:
            if not job_title or not company or not job_link:
                st.error("Please fill in Job Title, Company, and Job Link.")
            elif job_link and not re.fullmatch(URL_REGEX, job_link):
                st.error("Please correct the URL format.")
            else:
                date_submitted = datetime.now().strftime('%Y-%m-%d %H:%M')
                new_entry = pd.DataFrame([{
                    'Job_Title': job_title,
                    'Company': company,
                    'Date_Submitted': date_submitted,
                    'Requirements_Matched': requirements,
                    'Link': job_link,
                    'Status': status,
                    'Require_Enhancement': require_enhancement
                }])
                
                # Append the new entry to the DataFrame
                updated_df = pd.concat([df, new_entry], ignore_index=True)
                save_data(updated_df)
                st.session_state.df = updated_df # Update session state
                st.experimental_rerun() # Rerun to refresh the view

def show_modify_entry_form(df):
    """Streamlit form for modifying existing entries."""
    st.header("✏️ Modify Existing Entry")
    
    if df.empty:
        st.info("No data available to modify.")
        return

    # Use a selectbox to pick the entry based on a key identifier
    df['Identifier'] = df['Job_Title'] + ' - ' + df['Company']
    identifier = st.selectbox("Select Entry to Modify:", df['Identifier'].unique())
    
    if identifier:
        # Get the row index for the selected entry
        selected_row = df[df['Identifier'] == identifier].iloc[0]
        update_index = selected_row.name
        
        st.markdown(f"**Modifying:** `{identifier}`")
        
        # Create dynamic inputs for all columns (excluding non-editable columns like Date)
        new_values = {}
        with st.form("modify_form"):
            for col in HEADERS:
                if col == 'Date_Submitted':
                    st.text(f"Date_Submitted: {selected_row[col]} (Not editable)")
                    new_values[col] = selected_row[col]
                elif col == 'Status':
                    new_values[col] = st.selectbox(f"New Status for {col}:", options=ALLOWED_STATUSES, index=ALLOWED_STATUSES.index(selected_row[col]))
                else:
                    new_values[col] = st.text_area(f"New Value for {col}:", value=selected_row[col], height=50)

            submitted = st.form_submit_button("✅ Apply Modifications")

            if submitted:
                # Apply changes to the original DataFrame
                for col in HEADERS:
                    df.loc[update_index, col] = new_values[col]
                
                save_data(df)
                st.session_state.df = df
                st.success(f"Entry modified successfully!")
                st.experimental_rerun()

def show_delete_form(df):
    """Streamlit form for deleting entries based on criteria."""
    st.header("🗑️ Delete/Filter Data")
    
    if df.empty:
        st.info("No data available to delete.")
        return

    col_to_filter = st.selectbox("Select Column to Filter/Delete By:", df.columns.tolist())
    
    if col_to_filter:
        unique_values = df[col_to_filter].unique().tolist()
        value_to_delete = st.selectbox(f"Select value in '{col_to_filter}' to DELETE:", unique_values)
        
        if st.button(f"🔥 Permanently Delete all rows where {col_to_filter} = {value_to_delete}"):
            
            # Apply deletion logic
            rows_before = len(df)
            df_filtered = df[df[col_to_filter] != value_to_delete]
            rows_removed = rows_before - len(df_filtered)
            
            if rows_removed > 0:
                save_data(df_filtered)
                st.session_state.df = df_filtered
                st.success(f"Successfully deleted {rows_removed} row(s) where '{col_to_filter}' was '{value_to_delete}'.")
                st.experimental_rerun()
            else:
                st.warning(f"No rows found with the value '{value_to_delete}' to delete.")

# --- Main Streamlit App Layout ---

# Initialize the DataFrame in Streamlit's session state if it doesn't exist
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# ----------------------------------------------------
st.title("💼 Job Application Tracker")
st.markdown("Use the sidebar to navigate.")
# ----------------------------------------------------

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["View Data", "Add Entry", "Modify Entry", "Delete Data"])

# --- Page Rendering Logic ---

current_df = st.session_state.df

if page == "View Data":
    show_data_view(current_df)
elif page == "Add Entry":
    show_add_entry_form(current_df)
elif page == "Modify Entry":
    show_modify_entry_form(current_df)
elif page == "Delete Data":
    show_delete_form(current_df)
