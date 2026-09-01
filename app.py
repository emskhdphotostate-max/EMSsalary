import base64
import io
import sqlite3
from fpdf import FPDF
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Excellence Model School - Salary Management ERP",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional Deep Purple SaaS / ERP Theme Custom Styling
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #2C1654;
        color: #ffffff;
    }
    [data-testid="stSidebar"] .stSelectbox label, 
    [data-testid="stSidebar"] .stRadio label, 
    [data-testid="stSidebar"] div {
        color: #ffffff !important;
    }
    /* Fix Logout Button Styling - Purple Text & White Background */
    [data-testid="stSidebar"] button {
        color: #2C1654 !important;
        background-color: #ffffff !important;
        font-weight: 700;
        border-radius: 6px;
    }
    .main-header {
        font-size: 26px;
        font-weight: 800;
        color: #2C1654;
        text-align: center;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 15px;
        color: #4B5563;
        text-align: center;
        margin-bottom: 20px;
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


# Initialize and Upgrade Database Tables safely
def init_db():
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

  cursor = init_connection().cursor()
  cursor.execute("PRAGMA table_info(employees);")
  columns = [col[1] for col in cursor.fetchall()]
  if "joining_month" not in columns:
    execute_non_query(
        "ALTER TABLE employees ADD COLUMN joining_month TEXT DEFAULT 'July 2026';"
    )
  if "status" not in columns:
    execute_non_query(
        "ALTER TABLE employees ADD COLUMN status TEXT DEFAULT 'Active';"
    )
  if "leaving_month" not in columns:
    execute_non_query(
        "ALTER TABLE employees ADD COLUMN leaving_month TEXT DEFAULT '';"
    )


init_db()

MONTH_ORDER = {
    "January 2026": 1,
    "February 2026": 2,
    "March 2026": 3,
    "April 2026": 4,
    "May 2026": 5,
    "June 2026": 6,
    "July 2026": 7,
    "August 2026": 8,
    "September 2026": 9,
    "October 2026": 10,
    "November 2026": 11,
    "December 2026": 12,
}


def get_month_index(m_str):
  return MONTH_ORDER.get(m_str, 7)


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
  # Professional Styled Login Screen with LOGO.png
  st.markdown(
      "<div style='text-align: center; padding-top: 15px;'>",
      unsafe_allow_html=True,
  )
  try:
    st.image("LOGO.png", width=110)
  except Exception:
    st.markdown("<h1>🎓</h1>", unsafe_allow_html=True)
  st.markdown(
      "<h1 style='color: #2C1654; margin-top: 10px; font-weight: 800;'>EXCELLENCE"
      " MODEL SCHOOL</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<h3 style='color: #4B5563; font-weight: 500; font-size: 17px;'>Salary"
      " Management ERP Portal</h3>",
      unsafe_allow_html=True,
  )
  st.markdown("</div>", unsafe_allow_html=True)

  col1, col2, col3 = st.columns([1, 1.2, 1])
  with col2:
    st.markdown(
        "<div style='background: #ffffff; padding: 30px; border-radius: 12px;"
        " box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #e5e7eb;"
        " margin-top: 10px;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h3"
        " style='color: #2C1654; text-align: center; margin-bottom:"
        " 20px; font-size: 20px;'>🔒 Secure System Login</h3>",
        unsafe_allow_html=True,
    )
    password_input = st.text_input(
        "Enter Password", type="password", key="login_pass"
    )

    if st.button("Login to Portal", use_container_width=True, type="primary"):
      if password_input == "namuka112":
        st.session_state.authenticated = True
        st.success("Login Successful!")
        st.rerun()
      else:
        st.error("Invalid Password! Please try again.")
    st.markdown("</div>", unsafe_allow_html=True)
else:
  # Sidebar Navigation with Clean Centered Logo & Text (Image 1 Fixed)
  with st.sidebar:
    st.markdown(
        "<div"
        " style='display: flex; flex-direction: column; align-items: center;"
        " justify-content: center; text-align: center; padding-top: 10px;"
        " width: 100%;'>",
        unsafe_allow_html=True,
    )
    try:
      st.image("LOGO.png", width=85)
    except Exception:
      st.markdown("### 🎓")
    st.markdown(
        "<h3 style='margin: 8px 0 0 0; font-size: 15px; color:"
        " #ffffff; text-align: center;'>EXCELLENCE MODEL SCHOOL</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size:11px; color:#d1d5db; margin: 2px 0 0 0;"
        " text-align: center;'>Enterprise Management ERP</p>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")

    campuses = [
        "Kharadar",
        "Kharadar Extension",
        "Tower Campus",
        "Sony Campus",
        "Park View",
    ]
    selected_campus = st.selectbox("Select Campus", campuses)

    nav_mode = st.radio(
        "Main Navigation",
        [
            "Monthly Salary Sheet",
            "Staff Directory (Master & Increment)",
            "Employee Yearly Ledger",
            "Salary Slip Generator",
            "Summary",
        ],
    )

    month_filter = st.selectbox(
        "Select Month", list(MONTH_ORDER.keys()), index=7
    )  # Default August 2026

    st.markdown("---")
    if st.button("🚪 Secure Logout", use_container_width=True):
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
        "Manage staff master records here. You can add new employees, set"
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
            "Joining Month": st.column_config.SelectboxColumn(
                "Joining Month",
                options=list(MONTH_ORDER.keys()),
                required=True,
            ),
            "Status": st.column_config.SelectboxColumn(
                "Status", options=["Active", "Left"], required=True
            ),
            "Leaving Month": st.column_config.SelectboxColumn(
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
        f"<div class='main-header'>EXCELLENCE MODEL SCHOOL</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-header'>{selected_campus.upper()} BRANCH — Salary Sheet"
        f" ({month_filter})</div>",
        unsafe_allow_html=True,
    )

    current_m_idx = get_month_index(month_filter)

    existing_rows = run_query(
        """
            SELECT id, reg_no, name, designation, basic_salary, absent_days, 
                   late_days, days_in_month, considered_red_days, reason 
            FROM salaries WHERE campus = ? AND month_year = ? ORDER BY id;
        """,
        (selected_campus, month_filter),
    )

    if not existing_rows:
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

        if j_idx <= current_m_idx:
          if status == "Active" or (
              l_month and get_month_index(l_month) >= current_m_idx
          ):
            effective_basic = b_sal + inc
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

    col_save, col_dl, col_pdf = st.columns([1, 1, 1])
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
            label="📥 Download CSV Report",
            data=csv,
            file_name=f"{selected_campus}_Salary_{month_filter}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_pdf:
      if existing_rows:
        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(
            0,
            8,
            "EXCELLENCE MODEL SCHOOL - CONSOLIDATED SALARY REPORT",
            0,
            1,
            "C",
        )
        pdf.set_font("Arial", "", 10)
        pdf.cell(
            0,
            6,
            f"Campus: {selected_campus} | Month: {month_filter}",
            0,
            1,
            "C",
        )
        pdf.ln(5)

        pdf.set_font("Arial", "B", 8)
        cols = [
            "Reg No",
            "Name",
            "Designation",
            "Basic",
            "Absent",
            "Late",
            "Days",
            "Per Day",
            "Deduction",
            "Final Pay",
        ]
        widths = [20, 45, 40, 22, 18, 18, 18, 22, 25, 25]
        for i, col in enumerate(cols):
          pdf.cell(widths[i], 7, col, 1, 0, "C")
        pdf.ln()

        pdf.set_font("Arial", "", 8)
        for idx, row in display_df.iterrows():
          pdf.cell(widths[0], 6, str(row["Reg No"]), 1, 0, "C")  # type: ignore
          pdf.cell(widths[1], 6, str(row["Name"])[:25], 1, 0, "L")  # type: ignore
          pdf.cell(widths[2], 6, str(row["Designation"])[:22], 1, 0, "L")  # type: ignore
          pdf.cell(widths[3], 6, f"{row['Basic Salary']:,.0f}", 1, 0, "R")  # type: ignore
          pdf.cell(widths[4], 6, str(row["Absent Days"]), 1, 0, "C")  # type: ignore
          pdf.cell(widths[5], 6, str(row["Late Days"]), 1, 0, "C")  # type: ignore
          pdf.cell(widths[6], 6, str(row["Days in Month"]), 1, 0, "C")  # type: ignore
          pdf.cell(widths[7], 6, f"{row['Per Day']:,.1f}", 1, 0, "R")  # type: ignore
          pdf.cell(
              widths[8], 6, f"{row['Total Deduction Amount']:,.1f}", 1, 0, "R"
          )  # type: ignore
          pdf.cell(widths[9], 6, f"{row['Total Final Salary']:,.1f}", 1, 0, "R")  # type: ignore
          pdf.ln()

        pdf_output = bytes(pdf.output())

        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_output,
            file_name=f"{selected_campus}_Salary_{month_filter}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

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

  # 3. EMPLOYEE YEARLY LEDGER & CHARTS TAB
  elif nav_mode == "Employee Yearly Ledger":
    st.markdown(
        "<div class='main-header'>EXCELLENCE MODEL SCHOOL</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-header'>{selected_campus.upper()} BRANCH — Employee"
        " Yearly Salary Ledger (Jan 2026 - Dec 2026)</div>",
        unsafe_allow_html=True,
    )

    emp_names_raw = run_query(
        "SELECT DISTINCT name FROM salaries WHERE campus = ? ORDER BY name;",
        (selected_campus,),
    )
    emp_names = [r[0] for r in emp_names_raw if r[0]]

    if emp_names:
      selected_employee = st.selectbox(
          "Select Employee for Yearly Ledger", emp_names
      )

      yearly_rows = run_query(
          """
                SELECT month_year, basic_salary, absent_days, late_days, days_in_month, 
                       considered_red_days, reason 
                FROM salaries WHERE campus = ? AND name = ?;
            """,
          (selected_campus, selected_employee),
      )

      if yearly_rows:
        y_data = []
        for yr in yearly_rows:
          m_yr, b_sal, abs_d, late_d, dim, cred_d, reason = yr
          per_day = b_sal / dim if dim > 0 else 0
          auto_ded_late = late_d / 3.0
          net_units = max(0, (abs_d + auto_ded_late) - cred_d)
          tot_ded = net_units * per_day
          p_one = 1 if abs_d == 0 and late_d == 0 else 0
          final_pay = b_sal - tot_ded + (p_one * per_day)

          y_data.append({
              "Month": m_yr,
              "Month Index": get_month_index(m_yr),
              "Basic Salary": b_sal,
              "Absent Days": abs_d,
              "Late Days": late_d,
              "Total Deduction": tot_ded,
              "Final Payout": final_pay,
          })

        y_df = pd.DataFrame(y_data)
        y_df = y_df.sort_values("Month Index").drop(columns=["Month Index"])

        st.markdown(
            f"#### Yearly Financial Record for: **{selected_employee}**"
        )
        st.dataframe(y_df, use_container_width=True)

        st.markdown("#### 📈 Yearly Salary & Deduction Trend")
        chart_df = y_df.set_index("Month")[["Basic Salary", "Final Payout"]]
        st.line_chart(chart_df)

        chart_ded = y_df.set_index("Month")[["Total Deduction"]]
        st.bar_chart(chart_ded)

        csv_emp = y_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"📥 Download {selected_employee} Yearly Report (CSV)",
            data=csv_emp,
            file_name=f"{selected_employee}_Yearly_Ledger_2026.csv",
            mime="text/csv",
            use_container_width=True,
        )
      else:
        st.info("No salary records found for this employee.")
    else:
      st.info(
          "No employee records available for this campus yet. Please save"
          " monthly salary sheets first."
      )

  # 4. INDIVIDUAL SALARY SLIP GENERATOR TAB (Image 3 Fixed: Logos Added)
  elif nav_mode == "Salary Slip Generator":
    # Top Section with Logo (First requested position in Image 3)
    c_img, c_title = st.columns([0.15, 0.85])
    with c_img:
      try:
        st.image("LOGO.png", width=70)
      except Exception:
        st.markdown("### 🎓")
    with c_title:
      st.markdown(
          "<div class='main-header' style='text-align: left; margin: 0;'>EXCELLENCE MODEL SCHOOL</div>",
          unsafe_allow_html=True,
      )
      st.markdown(
          f"<div class='sub-header' style='text-align: left; margin: 0;'>{selected_campus.upper()} BRANCH — Individual Salary Slip ({month_filter})</div>",
          unsafe_allow_html=True,
      )

    slip_emps = run_query(
        """
            SELECT reg_no, name, designation, basic_salary, absent_days, late_days, 
                   days_in_month, considered_red_days, reason 
            FROM salaries WHERE campus = ? AND month_year = ? ORDER BY name;
        """,
        (selected_campus, month_filter),
    )

    if slip_emps:
      emp_dict = {row[1]: row for row in slip_emps}
      selected_slip_name = st.selectbox(
          "Select Employee for Salary Slip", list(emp_dict.keys())
      )

      if selected_slip_name:
        r_no, name, desig, b_sal, abs_d, late_d, dim, cred_d, reason = emp_dict[
            selected_slip_name
        ]
        per_day = b_sal / dim if dim > 0 else 0
        auto_ded_late = late_d / 3.0
        tot_units = abs_d + auto_ded_late
        net_units = max(0, tot_units - cred_d)
        tot_ded = net_units * per_day
        p_one = 1 if abs_d == 0 and late_d == 0 else 0
        plus_amount = p_one * per_day
        final_pay = b_sal - tot_ded + plus_amount

        # Salary Slip Box with Logo inside (Second requested position in Image 3)
        st.markdown(
            f"""
            <div style="border: 2px solid #2C1654; padding: 25px; border-radius: 10px; background-color: #ffffff; color: #000000; max-width: 700px; margin: auto;">
                <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 5px;">
                    <img src="data:image/png;base64,{base64.b64encode(open('LOGO.png', 'rb').read()).decode() if __import__('os').path.exists('LOGO.png') else ''}" width="50" style="vertical-align: middle;">
                    <h3 style="color: #2C1654; margin: 0;">EXCELLENCE MODEL SCHOOL</h3>
                </div>
                <p style="text-align: center; font-size: 13px; color: gray; margin-top: 2px;">Campus: {selected_campus} | Salary Slip for {month_filter}</p>
                <hr style="border: 1px solid #2C1654;">
                <table style="width: 100%; font-size: 14px; margin-bottom: 15px;">
                    <tr>
                        <td><b>Employee Name:</b> {name}</td>
                        <td><b>Reg No:</b> {r_no}</td>
                    </tr>
                    <tr>
                        <td><b>Designation:</b> {desig}</td>
                        <td><b>Month:</b> {month_filter}</td>
                    </tr>
                </table>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;" border="1">
                    <tr style="background-color: #2C1654; color: white;">
                        <th style="padding: 6px; text-align: left;">Earnings / Particulars</th>
                        <th style="padding: 6px; text-align: right;">Amount (Rs.)</th>
                        <th style="padding: 6px; text-align: left;">Deductions / Details</th>
                        <th style="padding: 6px; text-align: right;">Amount (Rs.)</th>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">Basic Salary</td>
                        <td style="padding: 6px; text-align: right;">{b_sal:,.2f}</td>
                        <td style="padding: 6px;">Absent Days ({abs_d})</td>
                        <td style="padding: 6px; text-align: right;">-</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">Punctuality Bonus (+1)</td>
                        <td style="padding: 6px; text-align: right;">{plus_amount:,.2f}</td>
                        <td style="padding: 6px;">Late Days ({late_d} / 3)</td>
                        <td style="padding: 6px; text-align: right;">-</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">-</td>
                        <td style="padding: 6px; text-align: right;">-</td>
                        <td style="padding: 6px;">Total Deductions</td>
                        <td style="padding: 6px; text-align: right; color: red;">{tot_ded:,.2f}</td>
                    </tr>
                    <tr style="background-color: #f3f4f6; font-weight: bold;">
                        <td style="padding: 8px;">Gross Total</td>
                        <td style="padding: 8px; text-align: right;">{(b_sal + plus_amount):,.2f}</td>
                        <td style="padding: 8px;">Net Final Payout</td>
                        <td style="padding: 8px; text-align: right; color: green;">Rs. {final_pay:,.2f}</td>
                    </tr>
                </table>
                <p style="font-size: 12px; margin-top: 15px; color: gray;"><b>Remarks/Pending Reason:</b> {reason if reason else 'None'}</p>
                <div style="display: flex; justify-content: space-between; margin-top: 40px; font-size: 13px;">
                    <span>_________________________<br>Employee Signature</span>
                    <span>_________________________<br>Authorized Stamp & Sign</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        slip_pdf = FPDF(orientation="P", unit="mm", format="A4")
        slip_pdf.add_page()
        slip_pdf.set_font("Arial", "B", 16)
        slip_pdf.cell(0, 8, "EXCELLENCE MODEL SCHOOL", 0, 1, "C")
        slip_pdf.set_font("Arial", "", 10)
        slip_pdf.cell(
            0,
            6,
            f"Campus: {selected_campus} | Official Salary Slip",
            0,
            1,
            "C",
        )
        slip_pdf.ln(5)

        slip_pdf.set_font("Arial", "B", 10)
        slip_pdf.cell(0, 6, f"Billing Month: {month_filter}", 0, 1, "L")  # type: ignore
        slip_pdf.cell(
            0, 6, f"Employee Name: {name} (Reg No: {r_no})", 0, 1, "L"
        )  # type: ignore
        slip_pdf.cell(0, 6, f"Designation: {desig}", 0, 1, "L")  # type: ignore
        slip_pdf.ln(5)

        slip_pdf.set_font("Arial", "B", 10)
        slip_pdf.cell(90, 7, "Particulars", 1, 0, "L")
        slip_pdf.cell(100, 7, "Amount (PKR)", 1, 1, "R")

        slip_pdf.set_font("Arial", "", 10)
        slip_pdf.cell(90, 6, "Basic Salary", 1, 0, "L")
        slip_pdf.cell(100, 6, f"{b_sal:,.2f}", 1, 1, "R")

        slip_pdf.cell(
            90,
            6,
            f"Attendance Adjustments (Absent: {abs_d}, Late: {late_d})",
            1,
            0,
            "L",
        )
        slip_pdf.cell(100, 6, f"-{tot_ded:,.2f}", 1, 1, "R")

        slip_pdf.cell(
            90,
            6,
            "Punctuality Bonus (+1 Day if 0 absence/late)",
            1,
            0,
            "L",
        )
        slip_pdf.cell(100, 6, f"+{plus_amount:,.2f}", 1, 1, "R")

        slip_pdf.set_font("Arial", "B", 10)
        slip_pdf.cell(90, 8, "Net Final Payout", 1, 0, "L")
        slip_pdf.cell(100, 8, f"Rs. {final_pay:,.2f}", 1, 1, "R")
        slip_pdf.ln(10)

        slip_pdf.set_font("Arial", "", 9)
        slip_pdf.cell(
            0,
            6,
            f"Remarks / Pending Reason: {reason if reason else 'None'}",
            0,
            1,
            "L",
        )
        slip_pdf.ln(25)

        slip_pdf.cell(95, 6, "____________________________", 0, 0, "L")
        slip_pdf.cell(95, 6, "____________________________", 0, 1, "R")
        slip_pdf.cell(95, 6, "Employee Signature", 0, 0, "L")
        slip_pdf.cell(95, 6, "Authorized Stamp & Signature", 0, 1, "R")

        slip_pdf_output = bytes(slip_pdf.output())

        st.download_button(
            label=f"📥 Download {name} Salary Slip (PDF)",
            data=slip_pdf_output,
            file_name=f"Salary_Slip_{name.replace(' ', '_')}_{month_filter}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
      st.info(
          "No salary records available for this month. Please generate or save"
          " the Monthly Salary Sheet first."
      )

  # 5. NETWORK SUMMARY TAB
  elif nav_mode == "Summary":
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
