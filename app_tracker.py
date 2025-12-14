import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import re

# --- Global Configurations ---
# The database file will be stored in the root of the GitHub repo.
DB_FILE = 'tracker.db' 
TABLE_NAME = 'applications'
ALLOWED_STATUSES = ["Submitted", "Interviewing", "Rejected", "Not Submitted"]
URL_REGEX = r"https?://(?:www\.|(?!www\.))[a-zA-Z0-9]+\.[^\s]{2,}"
HEADERS = ['Job_Title', 'Company', 'Date_Submitted', 'Requirements_Matched', 'Link', 'Status', "Require_Enhancement"]

# --- Core Data Persistence Functions ---

@st.cache_resource
def get_db_connection():
    """
    Establishes a connection to the SQLite database.
    Uses st.cache_resource to ensure the connection object is reused across reruns.
    """
    try:
        # Connects to the database file. If it doesn't exist, it creates it.
        conn = sqlite3.connect(DB_FILE)
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

def initialize_database(conn):
    """
    Creates the applications table if it doesn't exist.
    """
    try:
        cursor = conn.cursor()
        # SQL statement to create the table
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            Job_Title TEXT,
            Company TEXT,
            Date_Submitted TEXT,
            Requirements_Matched TEXT,
            Link TEXT,
            Status TEXT,
            Require_Enhancement TEXT
        );
        """
        cursor.execute(create_table_sql)
        conn.commit()
        # st.toast("Database table initialized.")
    except Exception as e:
        st.error(f"Error initializing database table: {e}")


@st.cache_data(show_spinner="Loading application data from SQLite...")
def load_data_from_db():
    """
    Loads all data from the SQLite table into a Pandas DataFrame.
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame(columns=HEADERS)

    try:
        # Use Pandas to read the entire SQL table into a DataFrame
        df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
        df = df.reindex(columns=HEADERS, fill_value='')
        return df
    except Exception as e:
        st.error(f"Error reading data from table: {e}")
        return pd.DataFrame(columns=HEADERS)


def save_data_to_db(df):
    """
    Saves the complete DataFrame back to the SQLite table, replacing the old data.
    This ensures all historical data and changes are saved atomically.
    """
    conn = get_db_connection()
    if conn is None:
        return

    try:
        # 'replace' argument ensures the old table content is deleted and replaced 
        # with the current, complete DataFrame state (old + new rows/changes).
        df.to_sql(TABLE_NAME, conn, if_exists='replace', index=False)
        conn.commit()
        st.toast("Data saved successfully to SQLite database.", icon="💾")
    except Exception as e:
        st.error(f"Error saving data to database: {e}")


# --- INITIAL SETUP ---
conn = get_db_connection()
if conn:
    initialize_database(conn)

# --- Streamlit UI Pages/Functions ---

def show_configuration():
    """
    Configuration page (simplified for SQLite, as the file is fixed).
    """
    st.header("⚙️ Data Source Configuration")
    
    st.success(f"Database is currently using a persistent SQLite file: `{DB_FILE}`.")
    st.info("Your data is saved directly to this file in the repository.")

    st.markdown("---")
    
    # --- CRITICAL FIX: Clear cache and force reload ---
    if st.button("🔄 **Clear Streamlit Cache and Force Full Reload**", type="primary"):
        st.cache_data.clear()
        st.session_state.df = load_data_from_db() 
        st.success("Cache cleared and data reloaded successfully!")
        st.rerun() 


def show_data_view(df):
    """Displays the current job applications data."""
    st.header("📋 Job Applications Data (Historical View)")
    st.markdown(f"Data Source: SQLite Database (`{DB_FILE}`) | Table: `{TABLE_NAME}`")
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
                save_data_to_db(updated_df) 
                st.session_state.df = updated_df
                st.rerun()


def show_modify_entry_form(df):
    """Streamlit form for modifying existing entries."""
    st.header("✏️ Modify Existing Entry")
    
    if df.empty:
        st.info("No data available to modify.")
        return

    df_temp = df.copy()
    df_temp['Identifier'] = df_temp['Job_Title'].astype(str) + ' - ' + df_temp['Company'].astype(str)
    identifier = st.selectbox("Select Entry to Modify:", df_temp['Identifier'].unique())
    
    if identifier:
        selected_row = df_temp[df_temp['Identifier'] == identifier].iloc[0]
        update_index = selected_row.name
        
        st.markdown(f"**Modifying:** `{identifier}`")
        
        new_values = {}
        with st.form("modify_form"):
            for col in HEADERS:
                if col == 'Date_Submitted':
                    st.text(f"Date_Submitted: {selected_row[col]} (Not editable)")
                    new_values[col] = selected_row[col]
                elif col == 'Status':
                    current_status = str(selected_row[col]) if str(selected_row[col]) in ALLOWED_STATUSES else ALLOWED_STATUSES[0]
                    new_values[col] = st.selectbox(f"New Status for {col}:", options=ALLOWED_STATUSES, index=ALLOWED_STATUSES.index(current_status))
                else:
                    new_values[col] = st.text_area(f"New Value for {col}:", value=selected_row[col], height=50)

            submitted = st.form_submit_button("✅ Apply Modifications")

            if submitted:
                for col in HEADERS:
                    df.loc[update_index, col] = new_values[col]
                
                save_data_to_db(df) 
                st.session_state.df = df
                st.success(f"Entry modified successfully!")
                st.rerun()


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
            df_filtered = df[df[col_to_filter].astype(str) != str(value_to_delete)] 
            rows_removed = rows_before - len(df_filtered)
            
            if rows_removed > 0:
                save_data_to_db(df_filtered) 
                st.session_state.df = df_filtered
                st.success(f"Successfully deleted {rows_removed} row(s) where '{col_to_filter}' was '{value_to_delete}'.")
                st.rerun()
            else:
                st.warning(f"No rows found with the value '{value_to_delete}' to delete.")


# --- Main Streamlit App Layout and State Initialization ---

st.title("💼 Job Application Tracker")
st.markdown("Use the sidebar to navigate.")

# 1. Initialize Session State Variables
if 'df' not in st.session_state:
    st.session_state.df = load_data_from_db()


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
