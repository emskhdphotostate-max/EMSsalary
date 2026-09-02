import base64
import io
import os
import re
from fpdf import FPDF
import pandas as pd
import psycopg2
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Excellence Model School - Salary Management ERP",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional Enterprise Deep Navy Theme Custom Styling
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #0b1329;
        color: #9ca3af;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    [data-testid="stSidebar"] .stSelectbox label, 
    [data-testid="stSidebar"] .stRadio label, 
    [data-testid="stSidebar"] div {
        color: #e5e7eb !important;
    }
    [data-testid="stSidebar"] .stRadio {
        margin-top: 5px;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
        gap: 6px !important;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
        background-color: transparent;
        padding: 9px 12px;
        border-radius: 8px;
        border: 1px solid transparent;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
        background-color: rgba(255, 255, 255, 0.05);
        border-color: rgba(255, 255, 255, 0.1);
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[data-checked="true"] {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
        border-color: #3b82f6;
        box-shadow: 0 4px 12px rgba(29, 78, 216, 0.4);
    }
    [data-testid="stSidebar"] button {
        color: #ffffff !important;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        font-weight: 600;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.5);
    }
    .main-header {
        font-size: 26px;
        font-weight: 800;
        color: #111827;
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
    .section-title {
        font-size: 18px;
        font-weight: 700;
        color: #111827;
        margin-top: 25px;
        margin-bottom: 10px;
        border-bottom: 2px solid #111827;
        padding-bottom: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_connection():
  db_url = st.secrets.get("DATABASE_URL")
  if not db_url:
    st.error("⚠️ DATABASE_URL not found in Streamlit Secrets!")
    st.stop()
  db_url = db_url.strip().strip('"').strip("'")
  db_url = re.sub(r"([&?])channel_binding=[^&]*", "", db_url)
  db_url = db_url.replace("&&", "&").replace("?&", "?")
  if db_url.endswith("&") or db_url.endswith("?"):
    db_url = db_url[:-1]
  if "?" not in db_url:
    db_url += "?sslmode=require"
  elif "sslmode=" not in db_url:
    db_url += "&sslmode=require"
  return psycopg2.connect(db_url)


def run_query(query, params=None):
  conn = init_connection()
  cursor = conn.cursor()
  if params:
    cursor.execute(query, params)
  else:
    cursor.execute(query)
  try:
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result
  except Exception:
    conn.commit()
    cursor.close()
    conn.close()
    return []


def execute_non_query(query, params=None):
  conn = init_connection()
  cursor = conn.cursor()
  if params:
    cursor.execute(query, params)
  else:
    cursor.execute(query)
  conn.commit()
  cursor.close()
  conn.close()


def get_next_employee_id(selected_campus):
  if "Extension" in selected_campus:
    prefix = "KH EXT-"
  elif "Tower" in selected_campus:
    prefix = "TW-"
  elif "Sony" in selected_campus:
    prefix = "SONY-"
  elif "Park View" in selected_campus:
    prefix = "PV-"
  else:
    prefix = "KH-"
  try:
    query = (
        "SELECT reg_no FROM employees WHERE campus = %s ORDER BY id DESC LIMIT"
        " 1;"
    )
    result = run_query(query, (selected_campus,))
    if result and result[0] and result[0][0]:
      numbers = re.findall(r"\d+", result[0][0])
      next_num = int(numbers[-1]) + 1 if numbers else 1
      return f"{prefix}{next_num}"
  except Exception:
    pass
  return f"{prefix}1"


def init_db():
  execute_non_query("""
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            campus TEXT,
            reg_no TEXT,
            name TEXT,
            father_name TEXT,
            designation TEXT,
            staff_category TEXT DEFAULT 'Teaching Staff',
            basic_salary REAL DEFAULT 0,
            increment REAL DEFAULT 0,
            joining_month TEXT DEFAULT 'July 2026',
            status TEXT DEFAULT 'Active',
            leaving_month TEXT DEFAULT ''
        );
    """)
  execute_non_query("""
        CREATE TABLE IF NOT EXISTS salaries (
            id SERIAL PRIMARY KEY,
            campus TEXT,
            reg_no TEXT,
            name TEXT,
            designation TEXT,
            staff_category TEXT DEFAULT 'Teaching Staff',
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


if "authenticated" not in st.session_state:
  st.session_state.authenticated = False

if not st.session_state.authenticated:
  logo_html = (
      f'<img src="data:image/png;base64,{base64.b64encode(open("LOGO.png", "rb").read()).decode()}" width="90" style="margin-bottom: 10px; border-radius: 10px; box-shadow: 0 3px 8px rgba(0,0,0,0.15);">'
      if os.path.exists("LOGO.png")
      else '<h1 style="margin:0;">🎓</h1>'
  )
  st.markdown(
      f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; margin-top: 40px; margin-bottom: 20px;">
            {logo_html}
            <h1 style="color: #111827; margin: 5px 0 0 0; font-weight: 800; font-size: 32px;">EXCELLENCE MODEL SCHOOL</h1>
            <p style="color: #4B5563; font-weight: 600; font-size: 16px; margin-top: 5px;">Salary Management ERP Portal</p>
        </div>
        """,
      unsafe_allow_html=True,
  )

  col1, col2, col3 = st.columns([1, 1.2, 1])
  with col2:
    st.markdown(
        """
        <div style="background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 6px 20px rgba(17,24,39,0.08); border: 1px solid #e5e7eb;">
            <h3 style="color: #111827; text-align: center; margin-bottom: 20px; font-size: 20px; font-weight: 700;">🔒 Secure System Login</h3>
        </div>
        """,
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
else:
  with st.sidebar:
    logo_sidebar = (
        f'<img src="data:image/png;base64,{base64.b64encode(open("LOGO.png", "rb").read()).decode()}" width="32" style="border-radius: 6px; vertical-align: middle; margin-right: 8px;">'
        if os.path.exists("LOGO.png")
        else '<span style="font-size: 20px; vertical-align: middle; margin-right: 8px;">🎓</span>'
    )
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; padding: 4px 0 12px 0;">
            {logo_sidebar}
            <span style="font-size: 14px; color: #ffffff; font-weight: 700; line-height: 1.2;">EXCELLENCE MODEL SCHOOL</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_campus = st.selectbox(
        "Select Campus",
        [
            "Kharadar",
            "Kharadar Extension",
            "Tower Campus",
            "Sony Campus",
            "Park View",
        ],
    )

    nav_mode = st.radio(
        "Main Navigation",
        [
            "📊 Monthly Salary Sheet",
            "➕ Add New Employee",
            "directory Staff Directory",
            "📅 Employee Yearly Ledger",
            "💬 Salary Slip Generator",
            "📈 Summary",
        ],
        label_visibility="collapsed",
    )

    clean_nav_mode = nav_mode.split(" ", 1)[1] if " " in nav_mode else nav_mode

    month_filter = st.selectbox(
        "Select Month", list(MONTH_ORDER.keys()), index=7
    )
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="background-color: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); padding: 14px; border-radius: 12px; margin-bottom: 15px;">
            <div style="font-size: 13px; font-weight: 700; color: #ffffff; margin-bottom: 4px;">Neon Database</div>
            <div style="font-size: 11px; color: #9ca3af; line-height: 1.4; margin-bottom: 10px;">Cloud synchronization active for school branches & records.</div>
            <div style="background-color: rgba(255, 255, 255, 0.1); border-radius: 4px; height: 6px; width: 100%; margin-bottom: 10px; overflow: hidden;">
                <div style="background-color: #3b82f6; width: 65%; height: 100%;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: #9ca3af;">
                <span>Active Sync</span>
                <span style="color: #60a5fa; cursor: pointer;">Upgrade Plan</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: space-between; padding-top: 5px; border-top: 1px solid rgba(255, 255, 255, 0.08);">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="background-color: #3b82f6; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px;">SK</div>
                <div>
                    <div style="font-size: 13px; font-weight: 600; color: #ffffff;">SSKAZAMA</div>
                    <div style="font-size: 10px; color: #9ca3af;">Admin Portal</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
    if st.button("🚪 Logout Session", use_container_width=True):
      st.session_state.authenticated = False
      st.rerun()

  if clean_nav_mode == "Add New Employee":
    st.markdown(
        "<div class='main-header'>EXCELLENCE MODEL SCHOOL</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='sub-header'>Add New Employee & Staff Registration</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
      new_campus = st.selectbox(
          "Select Campus for New Employee",
          [
              "Kharadar",
              "Kharadar Extension",
              "Tower Campus",
              "Sony Campus",
              "Park View",
          ],
          index=[
              "Kharadar",
              "Kharadar Extension",
              "Tower Campus",
              "Sony Campus",
              "Park View",
          ].index(selected_campus),
      )
      auto_generated_id = get_next_employee_id(new_campus)
      new_reg_no = st.text_input(
          "Registration / Employee ID", value=auto_generated_id
      )
      new_name = st.text_input("Staff Name")
      new_father_name = st.text_input("Father's Name")

    with col2:
      new_staff_category = st.selectbox(
          "Staff Category", ["Admin Staff", "Teaching Staff", "Non-Teaching Staff"]
      )
      new_designation = st.text_input("Designation (e.g. Teacher, Clerk, Maid)")
      new_basic_salary = st.number_input(
          "Basic Salary (Rs.)", min_value=0.0, step=1000.0, value=25000.0
      )
      new_joining_month = st.selectbox(
          "Joining Month (Start Month)", list(MONTH_ORDER.keys()), index=7
      )
      new_status = st.selectbox(
          "Employment Status", ["Active", "Left"], index=0
      )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(
        "➕ Register New Employee in Database",
        type="primary",
        use_container_width=True,
    ):
      if not new_name.strip() or not new_reg_no.strip():
        st.error(
            "⚠️ Please fill in at least the Employee ID and Staff Name fields!"
        )
      else:
        existing_check = run_query(
            "SELECT id FROM employees WHERE campus = %s AND reg_no = %s;",
            (new_campus, new_reg_no),
        )
        if existing_check:
          st.error(
              f"⚠️ Employee ID '{new_reg_no}' already exists in {new_campus}"
              " campus!"
          )
        else:
          execute_non_query(
              """
                    INSERT INTO employees (campus, reg_no, name, father_name, designation, staff_category, basic_salary, increment, joining_month, status, leaving_month)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, %s, '');
                """,
              (
                  new_campus,
                  new_reg_no,
                  new_name,
                  new_father_name,
                  new_designation,
                  new_staff_category,
                  new_basic_salary,
                  new_joining_month,
                  new_status,
              ),
          )
          st.success(
              f"✅ Successfully registered {new_name} for {new_campus}!"
          )
          st.balloons()

  elif clean_nav_mode == "Staff Directory":
    st.markdown(
        "<div class='main-header'>EXCELLENCE MODEL SCHOOL</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-header'>{selected_campus.upper()} BRANCH — Staff"
        " Directory & Increments</div>",
        unsafe_allow_html=True,
    )

    emp_rows = run_query(
        """
            SELECT id, reg_no, name, father_name, designation, staff_category, basic_salary, increment, joining_month, status, leaving_month 
            FROM employees WHERE campus = %s ORDER BY staff_category, id;
        """,
        (selected_campus,),
    )
    emp_df = (
        pd.DataFrame(
            emp_rows,
            columns=[
                "ID",
                "Reg No",
                "Name",
                "Father's Name",
                "Designation",
                "Staff Category",
                "Basic Salary",
                "Yearly Increment",
                "Joining Month",
                "Status",
                "Leaving Month",
            ],
        )
        if emp_rows
        else pd.DataFrame(
            columns=[
                "ID",
                "Reg No",
                "Name",
                "Father's Name",
                "Designation",
                "Staff Category",
                "Basic Salary",
                "Yearly Increment",
                "Joining Month",
                "Status",
                "Leaving Month",
            ]
        )
    )

    edited_emp_df = st.data_editor(
        emp_df,
        num_rows="dynamic",
        key=f"emp_master_{selected_campus}",
        column_config={
            "ID": None,
            "Staff Category": st.column_config.SelectboxColumn(
                "Staff Category",
                options=[
                    "Admin Staff",
                    "Teaching Staff",
                    "Non-Teaching Staff",
                ],
                required=True,
            ),
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
          "DELETE FROM employees WHERE campus = %s;", (selected_campus,)
      )
      for idx, row in edited_emp_df.iterrows():
        if pd.isna(row["Name"]) or str(row["Name"]).strip() == "":
          continue
        execute_non_query(
            """
                    INSERT INTO employees (campus, reg_no, name, father_name, designation, staff_category, basic_salary, increment, joining_month, status, leaving_month)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
            (
                selected_campus,
                str(row["Reg No"]) if pd.notna(row["Reg No"]) else "",
                str(row["Name"]),
                str(row["Father's Name"])
                if pd.notna(row["Father's Name"])
                else "",
                str(row["Designation"]) if pd.notna(row["Designation"]) else "",
                str(row["Staff Category"])
                if pd.notna(row["Staff Category"])
                else "Teaching Staff",
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
      st.success("✅ Staff Master Directory updated successfully!")
      st.rerun()

  elif clean_nav_mode == "Monthly Salary Sheet":
    st.markdown(
        "<div class='main-header'>EXCELLENCE MODEL SCHOOL</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-header'>{selected_campus.upper()} BRANCH — Salary Sheet"
        f" ({month_filter})</div>",
        unsafe_allow_html=True,
    )

    current_m_idx = get_month_index(month_filter)
    master_emps = run_query(
        """
            SELECT reg_no, name, designation, staff_category, basic_salary, increment, joining_month, status, leaving_month 
            FROM employees WHERE campus = %s;
        """,
        (selected_campus,),
    )

    for emp in master_emps:
      r_no, name, desig, s_cat, b_sal, inc, j_month, status, l_month = emp
      j_idx = get_month_index(j_month)
      is_eligible = (
          True
          if j_idx <= current_m_idx
          and (
              status == "Active"
              or (
                  status == "Left"
                  and l_month
                  and current_m_idx <= get_month_index(l_month)
              )
          )
          else False
      )

      existing_entry = run_query(
          """
                SELECT id FROM salaries WHERE campus = %s AND month_year = %s AND reg_no = %s;
            """,
          (selected_campus, month_filter, r_no),
      )

      effective_basic = b_sal + inc
      if is_eligible and not existing_entry:
        execute_non_query(
            """
                    INSERT INTO salaries (campus, reg_no, name, designation, staff_category, basic_salary, absent_days, late_days, days_in_month, considered_red_days, reason, month_year)
                    VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 30, 0, '', %s);
                """,
            (
                selected_campus,
                r_no,
                name,
                desig,
                s_cat if s_cat else "Teaching Staff",
                effective_basic,
                month_filter,
            ),
        )
      elif not is_eligible and existing_entry:
        execute_non_query(
            """
                    DELETE FROM salaries WHERE campus = %s AND month_year = %s AND reg_no = %s;
                """,
            (selected_campus, month_filter, r_no),
        )

    existing_rows = run_query(
        """
            SELECT id, reg_no, name, designation, staff_category, basic_salary, absent_days, 
                   late_days, days_in_month, considered_red_days, reason 
            FROM salaries WHERE campus = %s AND month_year = %s ORDER BY staff_category, id;
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
              "Staff Category",
              "Basic Salary",
              "Absent Days",
              "Late Days",
              "Days in Month",
              "Considered Red Days",
              "Remarks",
          ],
      )
      df["Basic Salary"] = pd.to_numeric(df["Basic Salary"]).fillna(0)
      df["Absent Days"] = (
          pd.to_numeric(df["Absent Days"]).fillna(0).astype(int)
      )
      df["Late Days"] = pd.to_numeric(df["Late Days"]).fillna(0).astype(int)
      df["Days in Month"] = (
          pd.to_numeric(df["Days in Month"]).fillna(30).astype(int)
      )
      df["Considered Red Days"] = (
          pd.to_numeric(df["Considered Red Days"]).fillna(0).astype(int)
      )

      df["Per Day"] = df.apply(
          lambda row: row["Basic Salary"] / row["Days in Month"]
          if row["Days in Month"] > 0
          else 0,
          axis=1,
      )
      df["Deduction Late"] = df["Late Days"].apply(
          lambda x: int(x // 3) if pd.notna(x) else 0
      )
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

      full_display_df = df[
          [
              "Staff Category",
              "Reg No",
              "Name",
              "Designation",
              "Basic Salary",
              "Absent Days",
              "Late Days",
              "Total Absent/Late Units",
              "Considered Red Days",
              "Days in Month",
              "Per Day",
              "Total Deduction Amount",
              "Plus 1",
              "Total Final Salary",
              "Remarks",
          ]
      ]
    else:
      full_display_df = pd.DataFrame(
          columns=[
              "Staff Category",
              "Reg No",
              "Name",
              "Designation",
              "Basic Salary",
              "Absent Days",
              "Late Days",
              "Total Absent/Late Units",
              "Considered Red Days",
              "Days in Month",
              "Per Day",
              "Total Deduction Amount",
              "Plus 1",
              "Total Final Salary",
              "Remarks",
          ]
      )

    categories = ["Admin Staff", "Teaching Staff", "Non-Teaching Staff"]
    cat_dfs = {}

    for cat in categories:
      st.markdown(
          f"<div class='section-title'>📌 {cat}</div>",
          unsafe_allow_html=True,
      )
      cat_subset = full_display_df[full_display_df["Staff Category"] == cat]
      work_df = cat_subset.drop(columns=["Staff Category"])

      edited_cat_df = st.data_editor(
          work_df,
          num_rows="fixed",
          key=f"salary_sheet_{selected_campus}_{month_filter}_{cat}",
          column_config={
              "Reg No": st.column_config.TextColumn("Reg No", width="small"),
              "Name": st.column_config.TextColumn("Staff Name", width="medium"),
              "Designation": st.column_config.TextColumn(
                  "Designation", width="large"
              ),
              "Basic Salary": st.column_config.NumberColumn(
                  "Basic", format="%,.0f"
              ),
              "Absent Days": st.column_config.NumberColumn(
                  "Abs", format="%d", step=1
              ),
              "Late Days": st.column_config.NumberColumn(
                  "Late", format="%d", step=1
              ),
              "Total Absent/Late Units": st.column_config.NumberColumn(
                  "Total Abs+Late", format="%d"
              ),
              "Considered Red Days": st.column_config.NumberColumn(
                  "Considered", format="%d", step=1
              ),
              "Days in Month": st.column_config.NumberColumn(
                  "Days", format="%d", step=1
              ),
              "Per Day": st.column_config.NumberColumn(
                  "Per Day", format="%,.1f"
              ),
              "Total Deduction Amount": st.column_config.NumberColumn(
                  "Deduction", format="%,.1f"
              ),
              "Plus 1": st.column_config.NumberColumn("Plus 1", format="%d"),
              "Total Final Salary": st.column_config.NumberColumn(
                  "Final Pay", format="%,.0f"
              ),
              "Remarks": st.column_config.TextColumn("Remarks", width="large"),
          },
      )

      if not edited_cat_df.empty:
        sub_basic = edited_cat_df["Basic Salary"].sum()
        sub_ded = edited_cat_df["Total Deduction Amount"].sum()
        sub_final = edited_cat_df["Total Final Salary"].sum()
        st.markdown(
            f"""
            <div style="background-color: #f3f4f6; padding: 10px 15px; border-radius: 6px; font-weight: bold; margin-bottom: 20px; display: flex; justify-content: space-between; border-left: 5px solid #111827;">
                <span>Total {cat}:</span>
                <span>Basic: Rs. {sub_basic:,.0f} | Deductions: Rs. {sub_ded:,.1f} | <span style="color: green;">Final Payout: Rs. {sub_final:,.0f}</span></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

      edited_cat_df["Staff Category"] = cat
      cat_dfs[cat] = edited_cat_df

    all_edited_combined = pd.concat(cat_dfs.values(), ignore_index=True)
    if not all_edited_combined.empty:
      grand_basic = all_edited_combined["Basic Salary"].sum()
      grand_ded = all_edited_combined["Total Deduction Amount"].sum()
      grand_final = all_edited_combined["Total Final Salary"].sum()
      st.markdown(
          f"""
          <div style="background: linear-gradient(135deg, #111827 0%, #1f2937 100%); color: white; padding: 15px 20px; border-radius: 8px; font-weight: bold; font-size: 16px; margin-top: 15px; margin-bottom: 25px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
              🏆 GRAND TOTAL ({selected_campus.upper()} BRANCH) — Basic: Rs. {grand_basic:,.0f} | Deductions: Rs. {grand_ded:,.1f} | Final Payout: Rs. {grand_final:,.0f}
          </div>
          """,
          unsafe_allow_html=True,
      )

    col_save, col_dl, col_pdf = st.columns([1, 1, 1])
    with col_save:
      if st.button("💾 Save Changes to Database", use_container_width=True):
        execute_non_query(
            "DELETE FROM salaries WHERE campus = %s AND month_year = %s;",
            (selected_campus, month_filter),
        )
        for idx, row in all_edited_combined.iterrows():
          if pd.isna(row["Name"]) or str(row["Name"]).strip() == "":
            continue
          r_no = str(row["Reg No"]) if pd.notna(row["Reg No"]) else ""
          name = str(row["Name"])
          desig = str(row["Designation"]) if pd.notna(row["Designation"]) else ""
          s_cat = (
              str(row["Staff Category"])
              if pd.notna(row["Staff Category"])
              else "Teaching Staff"
          )

          execute_non_query(
              """
                        INSERT INTO salaries (campus, reg_no, name, designation, staff_category, basic_salary, absent_days, 
                                              late_days, days_in_month, considered_red_days, reason, month_year)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
              (
                  selected_campus,
                  r_no,
                  name,
                  desig,
                  s_cat,
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
                  str(row["Remarks"]) if pd.notna(row["Remarks"]) else "",
                  month_filter,
              ),
          )
          # Also sync name/designation/reg_no update back to master employees table if needed
          execute_non_query(
              """
                        UPDATE employees SET name = %s, designation = %s, staff_category = %s 
                        WHERE campus = %s AND reg_no = %s;
                    """,
              (name, desig, s_cat, selected_campus, r_no),
          )

        st.success(
            "✅ Monthly salary sheet & employee info saved successfully to"
            " Neon!"
        )
        st.rerun()

    with col_dl:
      if existing_rows:
        csv = all_edited_combined.to_csv(index=False).encode("utf-8")
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

        if os.path.exists("LOGO.png"):
          pdf.image("LOGO.png", x=12, y=10, w=16)

        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(17, 24, 39)
        pdf.cell(0, 8, "EXCELLENCE MODEL SCHOOL", 0, 1, "C")
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(75, 85, 99)
        pdf.cell(
            0,
            6,
            "CONSOLIDATED SALARY REPORT & ATTENDANCE SUMMARY",
            0,
            1,
            "C",
        )

        pdf.set_font("Arial", "", 10)
        pdf.cell(
            0,
            6,
            f"Campus: {selected_campus}  |  Billing Month: {month_filter}",
            0,
            1,
            "C",
        )
        pdf.ln(4)
        pdf.set_draw_color(17, 24, 39)
        pdf.set_line_width(0.6)
        pdf.line(10, pdf.get_y(), 287, pdf.get_y())
        pdf.ln(6)

        grand_basic_pdf = 0
        grand_ded_pdf = 0
        grand_final_pdf = 0

        for cat in categories:
          cat_data = all_edited_combined[
              all_edited_combined["Staff Category"] == cat
          ]
          if cat_data.empty:
            continue

          pdf.set_font("Arial", "B", 12)
          pdf.set_text_color(17, 24, 39)
          pdf.cell(0, 8, f"{cat}", 0, 1, "L")

          pdf.set_font("Arial", "B", 8)
          pdf.set_fill_color(17, 24, 39)
          pdf.set_text_color(255, 255, 255)

          cols = [
              "Reg No",
              "Staff Name",
              "Designation",
              "Basic",
              "Abs",
              "Late",
              "Tot Abs+Late",
              "Considered",
              "Days",
              "Per Day",
              "Deduction",
              "Final Pay",
              "Remarks",
          ]
          widths = [15, 36, 32, 17, 10, 10, 18, 16, 11, 16, 17, 18, 43]

          for i, col in enumerate(cols):
            pdf.cell(widths[i], 7, col, 1, 0, "C", fill=True)
          pdf.ln()

          pdf.set_font("Arial", "", 7.5)
          pdf.set_text_color(0, 0, 0)
          fill_row = False

          sub_basic = cat_data["Basic Salary"].sum()
          sub_ded = cat_data["Total Deduction Amount"].sum()
          sub_final = cat_data["Total Final Salary"].sum()

          grand_basic_pdf += sub_basic
          grand_ded_pdf += sub_ded
          grand_final_pdf += sub_final

          for idx, row in cat_data.iterrows():
            if fill_row:
              pdf.set_fill_color(243, 244, 246)
            else:
              pdf.set_fill_color(255, 255, 255)

            pdf.cell(widths[0], 6, str(row["Reg No"]), 1, 0, "C", fill=True)
            pdf.cell(widths[1], 6, str(row["Name"])[:18], 1, 0, "L", fill=True)
            pdf.cell(
                widths[2], 6, str(row["Designation"])[:18], 1, 0, "L", fill=True
            )
            pdf.cell(
                widths[3],
                6,
                f"{row['Basic Salary']:,.0f}",
                1,
                0,
                "R",
                fill=True,
            )
            pdf.cell(
                widths[4], 6, str(int(row["Absent Days"])), 1, 0, "C", fill=True
            )
            pdf.cell(
                widths[5], 6, str(int(row["Late Days"])), 1, 0, "C", fill=True
            )
            pdf.cell(
                widths[6],
                6,
                str(int(row["Total Absent/Late Units"])),
                1,
                0,
                "C",
                fill=True,
            )
            pdf.cell(
                widths[7],
                6,
                str(int(row["Considered Red Days"])),
                1,
                0,
                "C",
                fill=True,
            )
            pdf.cell(
                widths[8],
                6,
                str(int(row["Days in Month"])),
                1,
                0,
                "C",
                fill=True,
            )
            pdf.cell(
                widths[9], 6, f"{row['Per Day']:,.1f}", 1, 0, "R", fill=True
            )
            pdf.cell(
                widths[10],
                6,
                f"{row['Total Deduction Amount']:,.1f}",
                1,
                0,
                "R",
                fill=True,
            )
            pdf.cell(
                widths[11],
                6,
                f"{row['Total Final Salary']:,.0f}",
                1,
                0,
                "R",
                fill=True,
            )
            pdf.cell(
                widths[12],
                6,
                str(row["Remarks"])[:25] if pd.notna(row["Remarks"]) else "",
                1,
                0,
                "L",
                fill=True,
            )
            pdf.ln()
            fill_row = not fill_row

          pdf.set_font("Arial", "B", 8.5)
          pdf.set_fill_color(229, 231, 235)
          pdf.cell(sum(widths[:3]), 6, f"Total {cat}:", 1, 0, "R", fill=True)
          pdf.cell(widths[3], 6, f"{sub_basic:,.0f}", 1, 0, "R", fill=True)
          pdf.cell(sum(widths[4:10]), 6, "", 1, 0, "C", fill=True)
          pdf.cell(widths[10], 6, f"{sub_ded:,.2f}", 1, 0, "R", fill=True)
          pdf.cell(widths[11], 6, f"{sub_final:,.0f}", 1, 0, "R", fill=True)
          pdf.cell(widths[12], 6, "", 1, 0, "C", fill=True)
          pdf.ln(8)

        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(17, 24, 39)
        pdf.set_text_color(255, 255, 255)
        grand_label = (
            f"GRAND TOTAL ({selected_campus.upper()} BRANCH) -- Basic: Rs."
            f" {grand_basic_pdf:,.0f} | Deductions: Rs. {grand_ded_pdf:,.2f} |"
            f" Final Payout: Rs. {grand_final_pdf:,.0f}"
        )
        pdf.cell(sum(widths), 8, grand_label, 1, 1, "C", fill=True)
        pdf.ln(10)

        pdf.set_font("Arial", "B", 13)
        pdf.set_text_color(17, 24, 39)
        pdf.cell(
            0,
            8,
            f"SUMMARY (SALARY) - {month_filter}",
            0,
            1,
            "C",
        )
        pdf.ln(3)

        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(0, 0, 0)
        pdf.set_text_color(255, 255, 255)

        sum_cols = [
            "S.NO",
            "CAMPUSES",
            "TOTAL SALARY",
            "DEDUCTION",
            "CONSIDERED",
            "PLUS 1",
            "PAYABLE",
        ]
        sum_widths = [14, 65, 38, 35, 35, 30, 40]

        for i, c_name in enumerate(sum_cols):
          pdf.cell(sum_widths[i], 7, c_name, 1, 0, "C", fill=True)
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(0, 0, 0)

        list_campuses = [
            "Kharadar",
            "Kharadar Extension",
            "Tower Campus",
            "Sony Campus",
            "Park View",
        ]
        display_campus_names = [
            "KHARADAR",
            "KHARADAR EXTENSION",
            "TOWER",
            "SONY MORNING",
            "PARK VIEW",
        ]

        net_tot_sal = 0
        net_tot_ded = 0
        net_tot_cred = 0
        net_tot_plus1 = 0
        net_tot_payable = 0

        for idx_c, cmp_name in enumerate(list_campuses):
          c_rows = run_query(
              """
                    SELECT basic_salary, absent_days, late_days, days_in_month, considered_red_days 
                    FROM salaries WHERE campus = %s AND month_year = %s;
                """,
              (cmp_name, month_filter),
          )

          c_sal_sum = 0
          c_ded_sum = 0
          c_cred_sum = 0
          c_p1_sum = 0
          c_pay_sum = 0

          if c_rows:
            for r in c_rows:
              b_sal, abs_d, late_d, dim, cred_d = r
              per_day = b_sal / dim if dim > 0 else 0
              auto_ded_late = int(late_d // 3)
              net_units = max(0, (abs_d + auto_ded_late) - cred_d)
              tot_ded = net_units * per_day
              cred_amt = cred_d * per_day
              p_one = 1 if abs_d == 0 and late_d == 0 else 0
              plus_amt = p_one * per_day
              final_pay = b_sal - tot_ded + plus_amt

              c_sal_sum += b_sal
              c_ded_sum += tot_ded
              c_cred_sum += cred_amt
              c_p1_sum += plus_amt
              c_pay_sum += final_pay

          net_tot_sal += c_sal_sum
          net_tot_ded += c_ded_sum
          net_tot_cred += c_cred_sum
          net_tot_plus1 += c_p1_sum
          net_tot_payable += c_pay_sum

          p1_str = f"{c_p1_sum:,.0f}" if c_p1_sum > 0 else "-"
          ded_str = f"{c_ded_sum:,.0f}" if c_ded_sum > 0 else "0"
          cred_str = f"{c_cred_sum:,.0f}" if c_cred_sum > 0 else "0"
          sal_str = f"{c_sal_sum:,.0f}" if c_sal_sum > 0 else "0"
          pay_str = f"{c_pay_sum:,.0f}" if c_pay_sum > 0 else "0"

          pdf.cell(sum_widths[0], 6, str(idx_c + 1), 1, 0, "C")
          pdf.cell(sum_widths[1], 6, display_campus_names[idx_c], 1, 0, "L")
          pdf.cell(sum_widths[2], 6, sal_str, 1, 0, "R")
          pdf.cell(sum_widths[3], 6, ded_str, 1, 0, "R")
          pdf.cell(sum_widths[4], 6, cred_str, 1, 0, "R")
          pdf.cell(sum_widths[5], 6, p1_str, 1, 0, "C")
          pdf.cell(sum_widths[6], 6, pay_str, 1, 0, "R")
          pdf.ln()

        pdf.set_font("Arial", "B", 9.5)
        pdf.set_fill_color(0, 0, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(
            sum_widths[0] + sum_widths[1], 7, "TOTAL", 1, 0, "C", fill=True
        )
        pdf.cell(
            sum_widths[2], 7, f"{net_tot_sal:,.0f}", 1, 0, "R", fill=True
        )
        pdf.cell(
            sum_widths[3], 7, f"{net_tot_ded:,.0f}", 1, 0, "R", fill=True
        )
        pdf.cell(
            sum_widths[4], 7, f"{net_tot_cred:,.0f}", 1, 0, "R", fill=True
        )
        pdf.cell(
            sum_widths[5], 7, f"{net_tot_plus1:,.0f}", 1, 0, "C", fill=True
        )
        pdf.cell(
            sum_widths[6], 7, f"{net_tot_payable:,.0f}", 1, 0, "R", fill=True
        )
        pdf.ln()

        pdf_output = bytes(pdf.output())
        st.download_button(
            label="📄 Download Professional PDF Report",
            data=pdf_output,
            file_name=f"{selected_campus}_Salary_{month_filter}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

  elif clean_nav_mode == "Employee Yearly Ledger":
    st.markdown(
        "<div class='main-header'>EXCELLENCE MODEL SCHOOL</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-header'>{selected_campus.upper()} BRANCH — Employee"
        " Yearly Salary Ledger</div>",
        unsafe_allow_html=True,
    )

    emp_names_raw = run_query(
        "SELECT DISTINCT name FROM salaries WHERE campus = %s ORDER BY name;",
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
                FROM salaries WHERE campus = %s AND name = %s;
            """,
          (selected_campus, selected_employee),
      )

      if yearly_rows:
        y_data = []
        for yr in yearly_rows:
          m_yr, b_sal, abs_d, late_d, dim, cred_d, reason = yr
          per_day = b_sal / dim if dim > 0 else 0
          auto_ded_late = int(late_d // 3)
          net_units = max(0, (abs_d + auto_ded_late) - cred_d)
          tot_ded = net_units * per_day
          p_one = 1 if abs_d == 0 and late_d == 0 else 0
          final_pay = b_sal - tot_ded + (p_one * per_day)
          y_data.append({
              "Month": m_yr,
              "Month Index": get_month_index(m_yr),
              "Basic Salary": b_sal,
              "Absent Days": int(abs_d),
              "Late Days": int(late_d),
              "Total Deduction": tot_ded,
              "Final Payout": final_pay,
          })
        y_df = pd.DataFrame(y_data)
        y_df = y_df.sort_values("Month Index").drop(columns=["Month Index"])
        st.markdown(
            f"#### Yearly Financial Record for: **{selected_employee}**"
        )
        st.dataframe(y_df, use_container_width=True)
      else:
        st.info("No salary records found for this employee.")
    else:
      st.info("No employee records available for this campus yet.")

  elif clean_nav_mode == "Salary Slip Generator":
    logo_data_uri = ""
    if os.path.exists("LOGO.png"):
      logo_data_uri = base64.b64encode(open("LOGO.png", "rb").read()).decode()

    logo_slip = (
        f'<img src="data:image/png;base64,{logo_data_uri}" width="65" style="vertical-align: middle; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); margin-bottom: 8px;">'
        if logo_data_uri
        else ""
    )
    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; margin-bottom: 25px;">
            {logo_slip}
            <div style="font-size: 26px; font-weight: 800; color: #111827; margin-bottom: 2px;">EXCELLENCE MODEL SCHOOL</div>
            <div style="font-size: 15px; color: #4B5563; font-weight: 500;">{selected_campus.upper()} BRANCH — Individual Salary Slip ({month_filter})</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    slip_emps = run_query(
        """
            SELECT reg_no, name, designation, staff_category, basic_salary, absent_days, late_days, 
                   days_in_month, considered_red_days, reason 
            FROM salaries WHERE campus = %s AND month_year = %s ORDER BY name;
        """,
        (selected_campus, month_filter),
    )

    if slip_emps:
      emp_dict = {row[1]: row for row in slip_emps}
      selected_slip_name = st.selectbox(
          "Select Employee for Salary Slip", list(emp_dict.keys())
      )

      if selected_slip_name:
        r_no, name, desig, s_cat, b_sal, abs_d, late_d, dim, cred_d, reason = (
            emp_dict[selected_slip_name]
        )
        per_day = b_sal / dim if dim > 0 else 0
        cred_amount = cred_d * per_day
        absent_gross_amount = abs_d * per_day
        auto_ded_late = int(late_d // 3)
        tot_units = abs_d + auto_ded_late
        net_units = max(0, tot_units - cred_d)
        tot_ded = net_units * per_day
        p_one = 1 if abs_d == 0 and late_d == 0 else 0
        plus_amount = p_one * per_day
        final_pay = b_sal - tot_ded + plus_amount

        logo_img_tag = (
            f'<img src="data:image/png;base64,{logo_data_uri}" width="50" style="vertical-align: middle;">'
            if logo_data_uri
            else ""
        )

        st.markdown(
            f"""
            <div style="border: 2px solid #111827; padding: 25px; border-radius: 10px; background-color: #ffffff; color: #000000; max-width: 700px; margin: auto;">
                <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 5px;">
                    {logo_img_tag}
                    <h3 style="color: #111827; margin: 0;">EXCELLENCE MODEL SCHOOL</h3>
                </div>
                <p style="text-align: center; font-size: 13px; color: gray; margin-top: 2px;">Campus: {selected_campus} | Salary Slip for {month_filter}</p>
                <hr style="border: 1px solid #111827;">
                <table style="width: 100%; font-size: 14px; margin-bottom: 15px;">
                    <tr>
                        <td><b>Employee Name:</b> {name}</td>
                        <td><b>Reg No:</b> {r_no}</td>
                    </tr>
                    <tr>
                        <td><b>Designation:</b> {desig} ({s_cat})</td>
                        <td><b>Month:</b> {month_filter}</td>
                    </tr>
                </table>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;" border="1">
                    <tr style="background-color: #111827; color: white;">
                        <th style="padding: 6px; text-align: left;">Earnings / Particulars</th>
                        <th style="padding: 6px; text-align: right;">Amount (Rs.)</th>
                        <th style="padding: 6px; text-align: left;">Deductions / Details</th>
                        <th style="padding: 6px; text-align: right;">Amount (Rs.)</th>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">Basic Salary</td>
                        <td style="padding: 6px; text-align: right;">{b_sal:,.0f}</td>
                        <td style="padding: 6px;">Absent Days ({int(abs_d)})</td>
                        <td style="padding: 6px; text-align: right; color: #b91c1c;">- {absent_gross_amount:,.1f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px; color: #1f2937; font-size: 13px;"><b>Considered Days:</b> {int(cred_d)}</td>
                        <td style="padding: 6px; text-align: right; color: #047857;">+ {cred_amount:,.1f}</td>
                        <td style="padding: 6px;">Late Days ({int(late_d)} -> {auto_ded_late} Ded. Day)</td>
                        <td style="padding: 6px; text-align: right;">-</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">Punctuality Bonus (+1)</td>
                        <td style="padding: 6px; text-align: right;">{plus_amount:,.1f}</td>
                        <td style="padding: 6px;">Total Deductions</td>
                        <td style="padding: 6px; text-align: right; color: red; font-weight: bold;">{tot_ded:,.1f}</td>
                    </tr>
                    <tr style="background-color: #f3f4f6; font-weight: bold;">
                        <td style="padding: 8px;">Gross Total</td>
                        <td style="padding: 8px; text-align: right;">{(b_sal + plus_amount):,.0f}</td>
                        <td style="padding: 8px;">Net Final Payout</td>
                        <td style="padding: 8px; text-align: right; color: green;">Rs. {final_pay:,.0f}</td>
                    </tr>
                </table>
                <p style="font-size: 12px; margin-top: 15px; color: gray;"><b>Remarks:</b> {reason if reason else 'None'}</p>
                <div style="display: flex; justify-content: space-between; margin-top: 40px; font-size: 13px;">
                    <span>_________________________<br>Employee Signature</span>
                    <span>_________________________<br>Authorized Stamp & Sign</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
      st.info("No salary records available for this month.")

  elif clean_nav_mode == "Summary":
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
            FROM salaries WHERE month_year = %s GROUP BY campus;
        """
    summary_data = run_query(sum_query, (month_filter,))
    all_rows = run_query(
        """
            SELECT basic_salary, absent_days, late_days, days_in_month, considered_red_days 
            FROM salaries WHERE month_year = %s;
        """,
        (month_filter,),
    )

    if summary_data and all_rows:
      total_staff_all = sum([r[1] for r in summary_data])
      total_basic_all = sum([r[2] for r in summary_data])
      tot_deductions = 0
      tot_final = 0
      for r in all_rows:
        b_sal, abs_d, late_d, dim, cred_d = r
        per_day = b_sal / dim if dim > 0 else 0
        auto_ded_late = int(late_d // 3)
        net_units = max(0, (abs_d + auto_ded_late) - cred_d)
        total_ded = net_units * per_day
        f_sal = (
            b_sal
            - total_ded
            + ((1 if abs_d == 0 and late_d == 0 else 0) * per_day)
        )
        tot_deductions += total_ded
        tot_final += f_sal

      st.markdown("### 🌟 Overall Network Analytics")
      k1, k2, k3, k4 = st.columns(4)
      with k1:
        st.metric("Total Network Staff", f"{total_staff_all}")
      with k2:
        st.metric("Total Basic Budget", f"Rs. {total_basic_all:,.0f}")
      with k3:
        st.metric("Total Deductions", f"Rs. {tot_deductions:,.1f}")
      with k4:
        st.metric("Grand Total Final Payout", f"Rs. {tot_final:,.0f}")
    else:
      st.info("No data entered yet across campuses for summary.")
