import os
import pandas as pd
import psycopg2
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Excellence Model School - Salary Management", layout="wide"
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 24px;
        font-weight: bold;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Updated Neon Database Connection using Streamlit Secrets & SSL handling
@st.cache_resource
def init_connection():
  db_url = st.secrets["neon"]["connection_string"]
  # Agar string mein sslmode nahi hai toh automatically add kar dein
  if "sslmode" not in db_url:
    if "?" in db_url:
      db_url += "&sslmode=require"
    else:
      db_url += "?sslmode=require"
  return psycopg2.connect(db_url)


def run_query(query, params=None):
  conn = init_connection()
  with conn.cursor() as cur:
    cur.execute(query, params)
    try:
      return cur.fetchall()
    except Exception:
      conn.commit()
      return []


def execute_non_query(query, params=None):
  conn = init_connection()
  with conn.cursor() as cur:
    cur.execute(query, params)
    conn.commit()


# Initialize Database Table if not exists
def init_db():
  query = """
    CREATE TABLE IF NOT EXISTS salaries (
        id SERIAL PRIMARY KEY,
        campus VARCHAR(50),
        reg_no VARCHAR(50),
        name VARCHAR(100),
        designation VARCHAR(100),
        basic_salary NUMERIC DEFAULT 0,
        absent_days NUMERIC DEFAULT 0,
        late_days NUMERIC DEFAULT 0,
        deduction_late NUMERIC DEFAULT 0,
        days_in_month NUMERIC DEFAULT 30,
        considered_red_days NUMERIC DEFAULT 0,
        plus_one NUMERIC DEFAULT 0,
        reason VARCHAR(255),
        month_year VARCHAR(50)
    );
    """
  execute_non_query(query)


init_db()

# Authentication State Check
if "authenticated" not in st.session_state:
  st.session_state.authenticated = False

if not st.session_state.authenticated:
  st.markdown(
      "<h1 style='text-align: center;'>Excellence Model School</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<h3 style='text-align: center; color: gray;'>Salary Management Portal</h3>",
      unsafe_allow_html=True,
  )

  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.subheader("🔒 System Login")
    password_input = st.text_input("Enter Password", type="password")

    if st.button("Login", use_container_width=True):
      if password_input == "namuka112":
        st.session_state.authenticated = True
        st.success("Login Successful!")
        st.rerun()
      else:
        st.error("Invalid Password! Please try again.")
else:
  # Sidebar Navigation for 5 Campuses and Summary Tab
  st.sidebar.title("🏫 School Portals")
  campuses = [
      "Kharadar",
      "Kharadar Extension",
      "Tower Campus",
      "Sony Campus",
      "Park View",
      "Summary",
  ]
  selected_tab = st.sidebar.selectbox("Select Campus / Tab", campuses)

  month_filter = st.sidebar.selectbox(
      "Select Month", ["July 2026", "August 2026", "September 2026"]
  )

  if selected_tab != "Summary":
    st.markdown(
        f"<div class='main-header'>EXCELLENCE MODEL SCHOOL -"
        f" {selected_tab.upper()} BRANCH</div>",
        unsafe_allow_html=True,
    )
    st.subheader(f"Salary Sheet for the Month of {month_filter}")

    # Fetch Data from Database
    query = """
            SELECT id, reg_no, name, designation, basic_salary, absent_days, late_days, 
                   deduction_late, days_in_month, considered_red_days, plus_one, reason 
            FROM salaries WHERE campus = %s AND month_year = %s ORDER BY id;
        """
    rows = run_query(query, (selected_tab, month_filter))

    columns = [
        "ID",
        "Reg No",
        "Name",
        "Designation",
        "Basic Salary",
        "Absent Days",
        "Late Days",
        "Deduction Late",
        "Days in Month",
        "Considered Red Days",
        "Plus 1",
        "Reason of Pending",
    ]

    if rows:
      df = pd.DataFrame(rows, columns=columns)
    else:
      df = pd.DataFrame(columns=columns)

    if not df.empty:
      # Data Type Cleaning
      df["Basic Salary"] = pd.to_numeric(df["Basic Salary"]).fillna(0)
      df["Absent Days"] = pd.to_numeric(df["Absent Days"]).fillna(0)
      df["Late Days"] = pd.to_numeric(df["Late Days"]).fillna(0)
      df["Deduction Late"] = pd.to_numeric(df["Deduction Late"]).fillna(0)
      df["Days in Month"] = pd.to_numeric(df["Days in Month"]).fillna(30)
      df["Considered Red Days"] = pd.to_numeric(
          df["Considered Red Days"]
      ).fillna(0)
      df["Plus 1"] = pd.to_numeric(df["Plus 1"]).fillna(0)

      # Automatic Formulas Calculation
      df["Per Day"] = df.apply(
          lambda row: row["Basic Salary"] / row["Days in Month"]
          if row["Days in Month"] > 0
          else 0,
          axis=1,
      )
      df["Ded for Absent"] = df["Absent Days"] * df["Per Day"]
      df["Total Deduction"] = df["Ded for Absent"] + df["Deduction Late"]
      df["Considered Red Amount"] = df["Considered Red Days"] * df["Per Day"]
      df["Final Salary"] = (
          df["Basic Salary"]
          - df["Total Deduction"]
          + df["Considered Red Amount"]
          + (df["Plus 1"] * df["Per Day"])
      )

      display_df = df[
          [
              "Reg No",
              "Name",
              "Designation",
              "Basic Salary",
              "Absent Days",
              "Ded for Absent",
              "Late Days",
              "Deduction Late",
              "Days in Month",
              "Per Day",
              "Total Deduction",
              "Considered Red Days",
              "Considered Red Amount",
              "Plus 1",
              "Final Salary",
              "Reason of Pending",
          ]
      ]

      edited_df = st.data_editor(display_df, num_rows="dynamic", key=selected_tab)

      if st.button("💾 Save Changes to Database"):
        delete_query = (
            "DELETE FROM salaries WHERE campus = %s AND month_year = %s;"
        )
        execute_non_query(delete_query, (selected_tab, month_filter))

        for idx, row in edited_df.iterrows():
          insert_query = """
                        INSERT INTO salaries (campus, reg_no, name, designation, basic_salary, absent_days, 
                                              late_days, deduction_late, days_in_month, considered_red_days, plus_one, reason, month_year)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """
          execute_non_query(
              insert_query,
              (
                  selected_tab,
                  row["Reg No"],
                  row["Name"],
                  row["Designation"],
                  row["Basic Salary"],
                  row["Absent Days"],
                  row["Late Days"],
                  row["Deduction Late"],
                  row["Days in Month"],
                  row["Considered Red Days"],
                  row["Plus 1"],
                  row["Reason of Pending"],
                  month_filter,
              ),
          )
        st.success("✅ Records and automatic formulas updated successfully!")
        st.rerun()
    else:
      st.info("No records found for this campus. Add new rows using the grid.")

  else:
    # SUMMARY TAB (Aggregating all 5 campuses automatically)
    st.markdown(
        "<div class='main-header'>EXCELLENCE MODEL SCHOOL - CONSOLIDATED"
        " SUMMARY</div>",
        unsafe_allow_html=True,
    )
    st.subheader(f"Summary Report for {month_filter} (All Campuses)")

    sum_query = """
            SELECT campus, COUNT(id) as total_staff, SUM(basic_salary) as total_basic 
            FROM salaries WHERE month_year = %s GROUP BY campus;
        """
    summary_data = run_query(sum_query, (month_filter,))

    if summary_data:
      sum_df = pd.DataFrame(
          summary_data,
          columns=["Campus Name", "Total Employees", "Total Basic Salary"],
      )
      st.dataframe(sum_df, use_container_width=True)
    else:
      st.info("No data entered yet across campuses for summary calculation.")

  if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()
