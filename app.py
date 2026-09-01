import sqlite3
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Excellence Model School - Salary Management ERP",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional Custom Styling (SaaS / ERP Theme)
st.markdown(
    """
    <style>
    .main-header {
        font-size: 28px;
        font-weight: 800;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 5px;
    }
    .sub-header {
        font-size: 16px;
        color: #4B5563;
        text-align: center;
        margin-bottom: 25px;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# SQLite Database Connection
def init_connection():
  conn = sqlite3.connect("school_salaries.db", check_same_thread=False)
  return conn


def run_query(query, params=None):
  conn = init_connection()
  cursor = conn.cursor()
  if params:
    cursor.execute(query, params)
  else:
    cursor.execute(query)
  try:
    return cursor.fetchall()
  except Exception:
    conn.commit()
    return []


def execute_non_query(query, params=None):
  conn = init_connection()
  cursor = conn.cursor()
  if params:
    cursor.execute(query, params)
  else:
    cursor.execute(query)
  conn.commit()


# Initialize Database Table
def init_db():
  query = """
    CREATE TABLE IF NOT EXISTS salaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campus TEXT,
        reg_no TEXT,
        name TEXT,
        designation TEXT,
        basic_salary REAL DEFAULT 0,
        absent_days REAL DEFAULT 0,
        late_days REAL DEFAULT 0,
        deduction_late REAL DEFAULT 0,
        days_in_month REAL DEFAULT 30,
        considered_red_days REAL DEFAULT 0,
        plus_one REAL DEFAULT 0,
        reason TEXT,
        month_year TEXT
    );
    """
  execute_non_query(query)


init_db()

# Authentication State Check
if "authenticated" not in st.session_state:
  st.session_state.authenticated = False

if not st.session_state.authenticated:
  st.markdown(
      "<h1 style='text-align: center; color: #1E3A8A;'>🏫 EXCELLENCE"
      " MODEL SCHOOL</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<h3 style='text-align: center; color: gray;'>Salary Management ERP"
      " Portal</h3>",
      unsafe_allow_html=True,
  )

  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.subheader("🔒 Secure System Login")
    password_input = st.text_input("Enter Password", type="password")

    if st.button("Login to Portal", use_container_width=True):
      if password_input == "namuka112":
        st.session_state.authenticated = True
        st.success("Login Successful!")
        st.rerun()
      else:
        st.error("Invalid Password! Please try again.")
else:
  # Sidebar Navigation for Campuses and Summary Tab
  st.sidebar.markdown("### 🏫 EMS Portals", unsafe_allow_html=True)
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
      "Select Month",
      [
          "July 2026",
          "August 2026",
          "September 2026",
          "October 2026",
          "November 2026",
          "December 2026",
      ],
  )

  st.sidebar.markdown("---")
  if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

  if selected_tab != "Summary":
    st.markdown(
        "<div style='text-align: center;'><span"
        " style='font-size:32px;'>🎓</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='main-header'>EXCELLENCE MODEL SCHOOL</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-header'>{selected_tab.upper()} BRANCH — Salary Sheet"
        f" ({month_filter})</div>",
        unsafe_allow_html=True,
    )

    # Fetch Data from Database
    query = """
            SELECT id, reg_no, name, designation, basic_salary, absent_days, late_days, 
                   deduction_late, days_in_month, considered_red_days, plus_one, reason 
            FROM salaries WHERE campus = ? AND month_year = ? ORDER BY id;
        """
    rows = run_query(query, (selected_tab, month_filter))

    if rows:
      df = pd.DataFrame(
          rows,
          columns=[
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
          ],
      )
      df["Basic Salary"] = pd.to_numeric(df["Basic Salary"]).fillna(0)
      df["Absent Days"] = pd.to_numeric(df["Absent Days"]).fillna(0)
      df["Late Days"] = pd.to_numeric(df["Late Days"]).fillna(0)
      df["Days in Month"] = pd.to_numeric(df["Days in Month"]).fillna(30)
      df["Considered Red Days"] = pd.to_numeric(
          df["Considered Red Days"]
      ).fillna(0)

      # Per Day Calculation
      df["Per Day"] = df.apply(
          lambda row: row["Basic Salary"] / row["Days in Month"]
          if row["Days in Month"] > 0
          else 0,
          axis=1,
      )

      # AUTOMATIC LATE DEDUCTION RULE: 3 Late Days = 1 Deduction Unit
      df["Deduction Late"] = df["Late Days"] / 3.0

      # Total Deduction Pool = Absent Days + Late Deduction Units
      df["Total Absent/Late Units"] = df["Absent Days"] + df["Deduction Late"]

      # Net Deduction Units after subtracting Considered Red Days (cannot be less than 0)
      df["Net Deduction Units"] = df.apply(
          lambda row: max(
              0, row["Total Absent/Late Units"] - row["Considered Red Days"]
          ),
          axis=1,
      )

      df["Total Deduction Amount"] = df["Net Deduction Units"] * df["Per Day"]

      # AUTOMATIC PLUS 1 RULE: If 0 Absent Days and 0 Late Days, Plus 1 becomes 1 automatically
      df["Plus 1"] = df.apply(
          lambda row: 1 if row["Absent Days"] == 0 and row["Late Days"] == 0 else 0,
          axis=1,
      )

      # Final Salary Calculation
      df["Final Salary"] = (
          df["Basic Salary"]
          - df["Total Deduction Amount"]
          + (df["Plus 1"] * df["Per Day"])
      )

      display_df = df[
          [
              "Reg No",
              "Name",
              "Designation",
              "Basic Salary",
              "Absent Days",
              "Late Days",
              "Deduction Late",
              "Days in Month",
              "Per Day",
              "Considered Red Days",
              "Total Deduction Amount",
              "Plus 1",
              "Final Salary",
              "Reason of Pending",
          ]
      ]
    else:
      display_df = pd.DataFrame(
          columns=[
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
      )

    edited_df = st.data_editor(display_df, num_rows="dynamic", key=selected_tab)

    col_save, col_dl = st.columns([1, 1])
    with col_save:
      if st.button("💾 Save Changes to Database", use_container_width=True):
        delete_query = (
            "DELETE FROM salaries WHERE campus = ? AND month_year = ?;"
        )
        execute_non_query(delete_query, (selected_tab, month_filter))

        for idx, row in edited_df.iterrows():
          if pd.isna(row["Name"]) or str(row["Name"]).strip() == "":
            continue

          # Re-calculate Plus 1 for saving to database based on editor values
          abs_val = (
              float(row["Absent Days"]) if pd.notna(row["Absent Days"]) else 0
          )
          late_val = float(row["Late Days"]) if pd.notna(row["Late Days"]) else 0
          p_one_val = 1 if abs_val == 0 and late_val == 0 else 0

          insert_query = """
                        INSERT INTO salaries (campus, reg_no, name, designation, basic_salary, absent_days, 
                                              late_days, deduction_late, days_in_month, considered_red_days, plus_one, reason, month_year)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """
          execute_non_query(
              insert_query,
              (
                  selected_tab,
                  str(row["Reg No"]) if pd.notna(row["Reg No"]) else "",
                  str(row["Name"]),
                  str(row["Designation"])
                  if pd.notna(row["Designation"])
                  else "",
                  float(row["Basic Salary"])
                  if pd.notna(row["Basic Salary"])
                  else 0,
                  abs_val,
                  late_val,
                  float(row["Deduction Late"])
                  if pd.notna(row["Deduction Late"])
                  else 0,
                  float(row["Days in Month"])
                  if pd.notna(row["Days in Month"])
                  else 30,
                  float(row["Considered Red Days"])
                  if pd.notna(row["Considered Red Days"])
                  else 0,
                  p_one_val,
                  str(row["Reason of Pending"])
                  if pd.notna(row["Reason of Pending"])
                  else "",
                  month_filter,
              ),
          )
        st.success(
            "✅ Records and automatic Plus 1 attendance bonus updated!"
        )
        st.rerun()

    with col_dl:
      if rows:
        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download CSV / Excel Report",
            data=csv,
            file_name=f"{selected_tab}_Salary_{month_filter}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Campus Totals Summary Cards
    if rows:
      st.markdown("### 📊 Branch Financial Summary")
      m1, m2, m3, m4 = st.columns(4)
      with m1:
        st.metric("Total Staff", f"{len(df)}")
      with m2:
        st.metric(
            "Total Basic Salary", f"Rs. {df['Basic Salary'].sum():,.2f}"
        )
      with m3:
        st.metric(
            "Total Deductions", f"Rs. {df['Total Deduction Amount'].sum():,.2f}"
        )
      with m4:
        st.metric("Total Final Payout", f"Rs. {df['Final Salary'].sum():,.2f}")

  else:
    # CONSOLIDATED SUMMARY TAB (All Campuses)
    st.markdown(
        "<div style='text-align: center;'><span"
        " style='font-size:32px;'>📈</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='main-header'>EXCELLENCE MODEL SCHOOL</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-header'>CONSOLIDATED SALARY SUMMARY REPORT —"
        f" {month_filter}</div>",
        unsafe_allow_html=True,
    )

    sum_query = """
            SELECT campus, COUNT(id) as total_staff, SUM(basic_salary) as total_basic 
            FROM salaries WHERE month_year = ? GROUP BY campus;
        """
    summary_data = run_query(sum_query, (month_filter,))

    all_q = """
            SELECT basic_salary, absent_days, late_days, deduction_late, days_in_month, considered_red_days, plus_one 
            FROM salaries WHERE month_year = ?;
        """
    all_rows = run_query(all_q, (month_filter,))

    if summary_data and all_rows:
      total_staff_all = sum([r[1] for r in summary_data])
      total_basic_all = sum([r[2] for r in summary_data])

      tot_deductions = 0
      tot_final = 0
      for r in all_rows:
        b_sal, abs_d, late_d, ded_l, dim, cred_d, p_one = r
        per_day = b_sal / dim if dim > 0 else 0
        auto_ded_late = late_d / 3.0
        total_units = abs_d + auto_ded_late
        net_units = max(0, total_units - cred_d)
        total_ded = net_units * per_day
        auto_p_one = 1 if abs_d == 0 and late_d == 0 else 0
        f_sal = b_sal - total_ded + (auto_p_one * per_day)
        tot_deductions += total_ded
        tot_final += f_sal

      st.markdown("### 🌟 Overall Network Analytics")
      k1, k2, k3, k4 = st.columns(4)
      with k1:
        st.metric("Total Network Staff", f"{total_staff_all}")
      with k2:
        st.metric("Total Basic Budget", f"Rs. {total_basic_all:,.2f}")
      with k3:
        st.metric("Total Deductions", f"Rs. {tot_deductions:,.2f}")
      with k4:
        st.metric("Grand Total Final Payout", f"Rs. {tot_final:,.2f}")

      st.markdown("---")
      st.subheader("Campus-wise Breakdown")
      sum_df = pd.DataFrame(
          summary_data,
          columns=["Campus Name", "Total Employees", "Total Basic Salary"],
      )
      st.dataframe(sum_df, use_container_width=True)

      sum_csv = sum_df.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Download Consolidated Summary Report (CSV)",
          data=sum_csv,
          file_name=f"EMS_Consolidated_Summary_{month_filter}.csv",
          mime="text/csv",
          use_container_width=True,
      )
    else:
      st.info(
          "No data entered yet across campuses for summary and total calculation."
      )
