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


# Initialize Database Tables (Employees Master with Joining/Leaving tracking + Monthly Salaries)
def init_db():
  # Master Employees Table
  execute_non_query("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campus TEXT,
            reg_no TEXT,
            name TEXT,
            designation TEXT,
            basic_salary REAL DEFAULT 0,
            increment REAL DEFAULT 0,
            joining_month TEXT DEFAULT 'July 2026',
            status TEXT DEFAULT 'Active',
            leaving_month TEXT DEFAULT ''
        );
    """)

  # Monthly Attendance & Salary Records Table
  execute_non_query("""
        CREATE TABLE IF NOT EXISTS salaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campus TEXT,
            reg_no TEXT,
            name TEXT,
            designation TEXT,
            basic_salary REAL DEFAULT 0,
            absent_days REAL DEFAULT 0,
            late_days REAL DEFAULT 0,
            days_in_month REAL DEFAULT 30,
            considered_red_days REAL DEFAULT 0,
            reason TEXT,
            month_year TEXT
        );
    """)


init_db()

# Month mapping for chronological filtering
MONTH_ORDER = {
    "July 2026": 1,
    "August 2026": 2,
    "September 2026": 3,
    "October 2026": 4,
    "November 2026": 5,
    "December 2026": 6,
}


def get_month_index(m_str):
  return MONTH_ORDER.get(m_str, 1)


# Auto-migrate existing salary records into employees master if master is empty
def auto_migrate_employees():
  campuses = [
      "Kharadar",
      "Kharadar Extension",
      "Tower Campus",
      "Sony Campus",
      "Park View",
  ]
  for camp in campuses:
    count = run_query(
        "SELECT COUNT(*) FROM employees WHERE campus = ?;", (camp,)
    )
    if count and count[0][0] == 0:
      old_emps = run_query(
          """
                SELECT DISTINCT reg_no, name, designation, basic_salary 
                FROM salaries WHERE campus = ?;
            """,
          (camp,),
      )
      for emp in old_emps:
        r_no, name, desig, b_sal = emp
        if name:
          execute_non_query(
              """
                    INSERT INTO employees (campus, reg_no, name, designation, basic_salary, increment, joining_month, status, leaving_month)
                    VALUES (?, ?, ?, ?, ?, 0, 'July 2026', 'Active', '');
                """,
              (camp, r_no, name, desig, b_sal),
          )


auto_migrate_employees()

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
  # Sidebar Navigation
  st.sidebar.markdown("### 🏫 EMS Portals", unsafe_allow_html=True)
  campuses = [
      "Kharadar",
      "Kharadar Extension",
      "Tower Campus",
      "Sony Campus",
      "Park View",
  ]
  selected_campus = st.sidebar.selectbox("Select Campus", campuses)

  nav_mode = st.sidebar.radio(
      "Navigation Menu",
      ["Monthly Salary Sheet", "Staff Directory (Master & Increment)", "Summary"],
  )

  month_filter = st.sidebar.selectbox(
      "Select Month", list(MONTH_ORDER.keys())
  )

  st.sidebar.markdown("---")
  if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

  # 1. STAFF DIRECTORY / MASTER MANAGEMENT TAB
  if nav_mode == "Staff Directory (Master & Increment)":
    st.markdown(
        "<div class='main-header'>EXCELLENCE MODEL SCHOOL</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-header'>{selected_campus.upper()} BRANCH — Staff"
        " Directory & Increments</div>",
        unsafe_allow_html=True,
    )

    st.info(
        "💡 Manage staff master records here. You can add new employees, set"
        " their joining month, apply yearly increments, or mark status as"
        " 'Left' for departing staff without breaking historical past salary"
        " records."
    )

    emp_rows = run_query(
        """
            SELECT id, reg_no, name, designation, basic_salary, increment, joining_month, status, leaving_month 
            FROM employees WHERE campus = ? ORDER BY id;
        """,
        (selected_campus,),
    )

    if emp_rows:
      emp_df = pd.DataFrame(
          emp_rows,
          columns=[
              "ID",
              "Reg No",
              "Name",
              "Designation",
              "Basic Salary",
              "Yearly Increment",
              "Joining Month",
              "Status",
              "Leaving Month",
          ],
      )
    else:
      emp_df = pd.DataFrame(
          columns=[
              "ID",
              "Reg No",
              "Name",
              "Designation",
              "Basic Salary",
              "Yearly Increment",
              "Joining Month",
              "Status",
              "Leaving Month",
          ]
      )

    edited_emp_df = st.data_editor(
        emp_df,
        num_rows="dynamic",
        key=f"emp_master_{selected_campus}",
        column_config={
            "ID": None,
            "JoiningMonth": st.column_config.SelectboxColumn(
                "Joining Month",
                options=list(MONTH_ORDER.keys()),
                required=True,
            ),
            "Status": st.column_config.SelectboxColumn(
                "Status", options=["Active", "Left"], required=True
            ),
            "LeavingMonth": st.column_config.SelectboxColumn(
                "Leaving Month",
                options=[""] + list(MONTH_ORDER.keys()),
                required=False,
            ),
        },
    )

    if st.button("💾 Save Staff Directory Changes", use_container_width=True):
      execute_non_query(
          "DELETE FROM employees WHERE campus = ?;", (selected_campus,)
      )
      for idx, row in edited_emp_df.iterrows():
        if pd.isna(row["Name"]) or str(row["Name"]).strip() == "":
          continue
        execute_non_query(
            """
                    INSERT INTO employees (campus, reg_no, name, designation, basic_salary, increment, joining_month, status, leaving_month)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
            (
                selected_campus,
                str(row["Reg No"]) if pd.notna(row["Reg No"]) else "",
                str(row["Name"]),
                str(row["Designation"]) if pd.notna(row["Designation"]) else "",
                float(row["Basic Salary"])
                if pd.notna(row["Basic Salary"])
                else 0,
                float(row["Yearly Increment"])
                if pd.notna(row["Yearly Increment"])
                else 0,
                str(row["Joining Month"])
                if pd.notna(row["Joining Month"])
                else "July 2026",
                str(row["Status"]) if pd.notna(row["Status"]) else "Active",
                str(row["Leaving Month"])
                if pd.notna(row["Leaving Month"])
                else "",
            ),
        )
      st.success(
          "✅ Staff Master Directory updated successfully! Historical records"
          " remain fully protected."
      )
      st.rerun()

  # 2. MONTHLY SALARY SHEET TAB
  elif nav_mode == "Monthly Salary Sheet":
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
        f"<div class='sub-header'>{selected_campus.upper()} BRANCH — Salary Sheet"
        f" ({month_filter})</div>",
        unsafe_allow_html=True,
    )

    current_m_idx = get_month_index(month_filter)

    # Check if monthly records exist
    existing_rows = run_query(
        """
            SELECT id, reg_no, name, designation, basic_salary, absent_days, 
                   late_days, days_in_month, considered_red_days, reason 
            FROM salaries WHERE campus = ? and month_year = ? ORDER BY id;
        """,
        (selected_campus, month_filter),
    )

    if not existing_rows:
      # Filter master employees eligible for this month:
      # 1. Joining month index <= current month index
      # 2. Either Active OR (Left but leaving month index >= current month index)
      master_emps = run_query(
          """
                SELECT reg_no, name, designation, basic_salary, increment, joining_month, status, leaving_month 
                FROM employees WHERE campus = ?;
            """,
          (selected_campus,),
      )

      for emp in master_emps:
        r_no, name, desig, b_sal, inc, j_month, status, l_month = emp
        j_idx = get_month_index(j_month)

        # Check eligibility for current month filter
        if j_idx <= current_m_idx:
          if status == "Active" or (
              l_month and get_month_index(l_month) >= current_m_idx
          ):
            effective_basic = b_sal + inc  # Basic + Yearly Increment
            execute_non_query(
                """
                        INSERT INTO salaries (campus, reg_no, name, designation, basic_salary, absent_days, late_days, days_in_month, considered_red_days, reason, month_year)
                        VALUES (?, ?, ?, ?, ?, 0, 0, 30, 0, '', ?);
                    """,
                (
                    selected_campus,
                    r_no,
                    name,
                    desig,
                    effective_basic,
                    month_filter,
                ),
            )

      existing_rows = run_query(
          """
            SELECT id, reg_no, name, designation, basic_salary, absent_days, 
                   late_days, days_in_month, considered_red_days, reason 
            FROM salaries WHERE campus = ? AND month_year = ? ORDER BY id;
        """,
          (selected_campus, month_filter),
      )

    if existing_rows:
      df = pd.DataFrame(
          existing_rows,
          columns=[
              "ID",
              "Reg No",
              "Name",
              "Designation",
              "Basic Salary",
              "Absent Days",
              "Late Days",
              "Days in Month",
              "Considered Red Days",
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

      # Calculations
      df["Per Day"] = df.apply(
          lambda row: row["Basic Salary"] / row["Days in Month"]
          if row["Days in Month"] > 0
          else 0,
          axis=1,
      )
      df["Deduction Late"] = df["Late Days"] / 3.0
      df["Total Absent/Late Units"] = df["Absent Days"] + df["Deduction Late"]
      df["Net Deduction Units"] = df.apply(
          lambda row: max(
              0, row["Total Absent/Late Units"] - row["Considered Red Days"]
          ),
          axis=1,
      )
      df["Total Deduction Amount"] = df["Net Deduction Units"] * df["Per Day"]

      df["Plus 1"] = df.apply(
          lambda row: 1 if row["Absent Days"] == 0 and row["Late Days"] == 0 else 0,
          axis=1,
      )
      df["Total Final Salary"] = (
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
              "Total Final Salary",
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
              "Per Day",
              "Considered Red Days",
              "Total Deduction Amount",
              "Plus 1",
              "Total Final Salary",
              "Reason of Pending",
          ]
      )

    edited_df = st.data_editor(
        display_df,
        num_rows="fixed",
        key=f"salary_sheet_{selected_campus}_{month_filter}",
        column_config={
            "Basic Salary": st.column_config.NumberColumn(
                "Basic Salary", help="Editable for salary adjustments/increments"
            )
        },
    )

    col_save, col_dl = st.columns([1, 1])
    with col_save:
      if st.button("💾 Save Changes to Database", use_container_width=True):
        execute_non_query(
            "DELETE FROM salaries WHERE campus = ? AND month_year = ?;",
            (selected_campus, month_filter),
        )

        for idx, row in edited_df.iterrows():
          if pd.isna(row["Name"]) or str(row["Name"]).strip() == "":
            continue
          execute_non_query(
              """
                        INSERT INTO salaries (campus, reg_no, name, designation, basic_salary, absent_days, 
                                              late_days, days_in_month, considered_red_days, reason, month_year)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
              (
                  selected_campus,
                  str(row["Reg No"]) if pd.notna(row["Reg No"]) else "",
                  str(row["Name"]),
                  str(row["Designation"])
                  if pd.notna(row["Designation"])
                  else "",
                  float(row["Basic Salary"])
                  if pd.notna(row["Basic Salary"])
                  else 0,
                  float(row["Absent Days"])
                  if pd.notna(row["Absent Days"])
                  else 0,
                  float(row["Late Days"]) if pd.notna(row["Late Days"]) else 0,
                  float(row["Days in Month"])
                  if pd.notna(row["Days in Month"])
                  else 30,
                  float(row["Considered Red Days"])
                  if pd.notna(row["Considered Red Days"])
                  else 0,
                  str(row["Reason of Pending"])
                  if pd.notna(row["Reason of Pending"])
                  else "",
                  month_filter,
              ),
          )
        st.success("✅ Monthly salary sheet saved successfully!")
        st.rerun()

    with col_dl:
      if existing_rows:
        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download CSV / Excel Report",
            data=csv,
            file_name=f"{selected_campus}_Salary_{month_filter}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Branch Financial Summary Cards
    if existing_rows:
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
        st.metric(
            "Total Final Payout", f"Rs. {df['Total Final Salary'].sum():,.2f}"
        )

  # 3. NETWORK SUMMARY TAB
  elif nav_mode == "Summary":
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
            SELECT basic_salary, absent_days, late_days, days_in_month, considered_red_days 
            FROM salaries WHERE month_year = ?;
        """
    all_rows = run_query(all_q, (month_filter,))

    if summary_data and all_rows:
      total_staff_all = sum([r[1] for r in summary_data])
      total_basic_all = sum([r[2] for r in summary_data])

      tot_deductions = 0
      tot_final = 0
      for r in all_rows:
        b_sal, abs_d, late_d, dim, cred_d = r
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
