import streamlit as st
import pandas as pd
import os
from datetime import datetime
import re
import csv
from io import StringIO 

# --- Global Configurations ---
# Default local file name. This is used if the user doesn't set a Drive path.
DEFAULT_FILE_NAME = 'job_applications.csv' 
ALLOWED_STATUSES = ["Submitted", "Interviewing", "Rejected", "Not Submitted"]
URL_REGEX = r"https?://(?:www\.|(?!www\.))[a-zA-Z0-9]+\.[^\s]{2,}"
HEADERS = ['Job_Title', 'Company', 'Date_Submitted', 'Requirements_Matched', 'Link', 'Status', "Require_Enhancement"]

# --- State and Utility Functions ---

def load_data():
    """
    Loads data from the file path stored in session state.
    """
    file_path = st.session_state.file_path
    
    if not os.path.exists(file_path):
        # Create the necessary folder structure if it's a Drive path
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # Create a header-only CSV file
            df = pd.DataFrame(columns=HEADERS)
            df.to_csv(file_path, index=False)
            st.toast("New data file initialized.", icon="📝")
            return df
        except Exception:
            # Fallback to an empty DataFrame if path creation fails (e.g., read-only cloud environment)
            st.error(f"Could not initialize file path: {file_path}. Using an empty table.")
            return pd.DataFrame(columns=HEADERS)
    else:
        try:
            df = pd.read_csv(file_path)
            # Ensure columns are correct if file was just created/empty
            if df.empty and not df.columns.tolist() == HEADERS:
                df = pd.DataFrame(columns=HEADERS)
            return df
        except Exception as e:
            st.error(f"Error reading file at {file_path}. Error: {e}")
            return pd.DataFrame(columns=HEADERS)

def save_data(df):
    """Saves the current DataFrame back to the file path in session state."""
    file_path = st.session_state.file_path
    try:
        df.to_csv(file_path, index=False)
        st.toast(f"Data saved successfully to {file_path}", icon="💾")
    except Exception as e:
        st.error(f"Error saving data to {file_path}: {e}")

# --- Streamlit UI Pages/Functions ---

def show_configuration():
    """Page for configuring the file path, including Google Drive option."""
    st.header("⚙️ Data Source Configuration")
    
    st.warning("🚨 **IMPORTANT:** If using Google Drive, you MUST first ensure the Drive volume is mounted and accessible to your Python environment (e.g., running `drive.mount()` in Google Colab). Streamlit Cloud CANNOT do this automatically.")

    current_path = st.session_state.file_path
    st.markdown(f"**Current Data Path:** `{current_path}`")
    
    new_path = st.text_input(
        "Enter new file path (e.g., /content/drive/MyDrive/JobData/tracker.csv):",
        value=current_path
    )
    
    if st.button("Apply New Path"):
        st.session_state.file_path = new_path
        # Force reload of data with the new path
        st.session_state.df = load_data()
        st.success(f"File path updated and data reloaded from: {new_path}")


def show_data_view(df):
    """Displays the current job applications data."""
    st.header("📋 Job Applications Data")
    st.markdown(f"Data Source: `{st.session_state.file_path}`")
    if df.empty:
        st.info("The tracker is currently empty. Add a new entry to get started!")
    else:
        st.dataframe(df, use_container_width=True)
        st.markdown(f"**Total Entries:** {len(df)}")


def show_add_entry_form(df):
    """Streamlit form for adding a new entry."""
    st.header("➕ Add New Job Application")

    with st.form("add_form", clear_on_submit=True):
        job_title = st.text_input("1. Job Title (e.g., Senior Data Engineer):")
        company = st.text_input("2. Company Name:")
        requirements = st.text_input("3. Number of matched requirements (e.g., 7/10):")
        require_enhancement = st.text_area("7. Learning Focus (Skills to develop for this role):")
        job_link = st.text_input("4. Job Link Address (e.g., https://example.com/job):").strip()
        status = st.selectbox("5. Application Status:", options=ALLOWED_STATUSES)

        submitted = st.form_submit_button("💾 Save Entry")

        if submitted:
            if not job_title or not company or not job_link:
                st.error("Please fill in Job Title, Company, and Job Link.")
            elif not re.fullmatch(URL_REGEX, job_link):
                st.error("❌ Invalid URL Format. Please enter a full link starting with http:// or https://.")
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
                
                updated_df = pd.concat([df, new_entry], ignore_index=True)
                save_data(updated_df)
                st.session_state.df = updated_df
                st.experimental_rerun()


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
        selected_row = df[df['Identifier'] == identifier].iloc[0]
        update_index = selected_row.name
        
        st.markdown(f"**Modifying:** `{identifier}`")
        
        # Create dynamic inputs for all columns
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


# --- Main Streamlit App Layout and State Initialization ---

st.title("💼 Job Application Tracker")
st.markdown("Use the sidebar to navigate.")

# 1. Initialize Session State Variables
if 'file_path' not in st.session_state:
    # Use the hardcoded path from your previous input as the initial default
    st.session_state.file_path = '/content/drive/MyDrive/Job Tracker/job_applications (5).csv'
if 'df' not in st.session_state:
    st.session_state.df = load_data()


# 2. Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["View Data", "Add Entry", "Modify Entry", "Delete Data", "Configuration"])

# 3. Page Rendering Logic

current_df = st.session_state.df

if page == "View Data":
    show_data_view(current_df)
elif page == "Add Entry":
    show_add_entry_form(current_df)
elif page == "Modify Entry":
    show_modify_entry_form(current_df)
elif page == "Delete Data":
    show_delete_form(current_df)
elif page == "Configuration":
    show_configuration()
