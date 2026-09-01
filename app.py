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
    [data-testid="stSidebar"] button {
        color: #ffffff !important;
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
        font-weight: 700;
        border-radius: 35px !important;
        border: 2px solid rgba(255, 255, 255, 0.2) !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        letter-spacing: 0.8px;
        transition: all 0.3s ease;
    }
    [data-testid="stSidebar"] button:hover {
        background: linear-gradient(135deg, #4338ca 0%, #2563eb 100%) !important;
        box-shadow: 0 6px 15px rgba(59, 130, 246, 0.6);
        border-color: rgba(255, 255, 255, 0.5) !important;
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
    .section-title {
        font-size: 18px;
        font-weight: 700;
        color: #2C1654;
        margin-top: 25px;
        margin-bottom: 10px;
        border-bottom: 2px solid #2C1654;
        padding-bottom: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Neon Database (PostgreSQL) Connection with Bulletproof URL Parsing
def init_connection():
  db_url = st.secrets.get("DATABASE_URL")
  if not db_url:
    st.error(
        "⚠️ DATABASE_URL not found in Streamlit Secrets! Please configure"
        " secrets in Streamlit Cloud."
    )
    st.stop()

  # Clean up quotes, spaces, and handle channel_binding safely
  db_url = db_url.strip().strip('"').strip("'")

  if "channel_binding" in db_url:
    if "&channel_binding" in db_url:
      db_url = db_url.split("&channel_binding")[0]
    elif "?channel_binding" in db_url:
      base_part = db_url.split("?channel_binding")[0]
      remainder = db_url.split("?channel_binding")[1]
      if "&" in remainder:
        extra_params = "&".join(remainder.split("&")[1:])
        db_url = f"{base_part}?{extra_params}"
      else:
        db_url = base_part

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
      last_id = result[0][0]
      numbers = re.findall(r"\d+", last_id)
      if numbers:
        next_num = int(numbers[-1]) + 1
        new_id = f"{prefix}{next_num}"
      else:
        new_id = f"{prefix}1"
    else:
      new_id = f"{prefix}1"
  except Exception:
    new_id = f"{prefix}1"

  return new_id


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
  logo_html = ""
  if os.path.exists("LOGO.png"):
    with open("LOGO.png", "rb") as f:
      logo_b64 = base64.b64encode(f.read()).decode()
      logo_html = f'<img src="data:image/png;base64,{logo_b64}" width="90" style="margin-bottom: 10px; border-radius: 10px; box-shadow: 0 3px 8px rgba(0,0,0,0.15);">'
  else:
    logo_html = '<h1 style="margin:0;">🎓</h1>'

  st.markdown(
      f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; margin-top: 40px; margin-bottom: 20px;">
            {logo_html}
            <h1 style="color: #2C1654; margin: 5px 0 0 0; font-weight: 800; font-size: 32px;">EXCELLENCE MODEL SCHOOL</h1>
            <p style="color: #4B5563; font-weight: 600; font-size: 16px; margin-top: 5px;">Salary Management ERP Portal</p>
        </div>
        """,
      unsafe_allow_html=True,
  )

  col1, col2, col3 = st.columns([1, 1.2, 1])
  with col2:
    st.markdown(
        """
        <div style="background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 6px 20px rgba(44,22,84,0.12); border: 1px solid #e5e7eb;">
            <h3 style="color: #2C1654; text-align: center; margin-bottom: 20px; font-size: 20px; font-weight: 700;">🔒 Secure System Login</h3>
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
    logo_html = ""
    if os.path.exists("LOGO.png"):
      with open("LOGO.png", "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" width="80" style="margin-bottom: 8px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.2);">'
    else:
      logo_html = '<h3 style="margin:0;">🎓</h3>'

    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 10px 0; width: 100%;">
            {logo_html}
            <h3 style="margin: 6px 0 0 0; font-size: 15px; color: #ffffff; font-weight: 700; letter-spacing: 0.5px; text-align: center;">EXCELLENCE MODEL SCHOOL</h3>
            <p style="font-size: 11px; color: #d1d5db; margin: 3px 0 0 0; text-align: center;">Enterprise Management ERP</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
            "Add New Employee",
            "Staff Directory (Master & Increment)",
            "Employee Yearly Ledger",
            "Salary Slip Generator",
            "Summary",
        ],
    )

    month_filter = st.selectbox(
        "Select Month", list(MONTH_ORDER.keys()), index=7
    )

    st.markdown("---")
    if st.button("🚪 LOGOUT", use_container_width=True):
      st.session_state.authenticated = False
      st.rerun()

  if nav_mode == "Add New Employee":
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
              " campus! Please use a unique ID."
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

          j_idx = get_month_index(new_joining_month)
          curr_idx = get_month_index(month_filter)
          if j_idx <= curr_idx and new_status == "Active":
            execute_non_query(
                """
                        INSERT INTO salaries (campus, reg_no, name, designation, staff_category, basic_salary, absent_days, late_days, days_in_month, considered_red_days, reason, month_year)
                        VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 30, 0, '', %s);
                    """,
                (
                    new_campus,
                    new_reg_no,
                    new_name,
                    new_designation,
                    new_staff_category,
                    new_basic_salary,
                    month_filter,
                ),
            )

          st.success(
              f"✅ Successfully registered {new_name} ({new_designation} -"
              f" {new_staff_category}) with ID {new_reg_no} for"
              f" {new_campus}!"
          )
          st.balloons()

  elif nav_mode == "Staff Directory (Master & Increment)":
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

    if emp_rows:
      emp_df = pd.DataFrame(
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
    else:
      emp_df = pd.DataFrame(
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

      is_eligible = False
      if j_idx <= current_m_idx:
        if status == "Active":
          is_eligible = True
        elif status == "Left" and l_month:
          l_idx = get_month_index(l_month)
          if current_m_idx <= l_idx:
            is_eligible = True

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
      elif is_eligible and existing_entry:
        execute_non_query(
            """
                    UPDATE salaries SET staff_category = %s, designation = %s, name = %s, basic_salary = %s 
                    WHERE campus = %s AND month_year = %s AND reg_no = %s;
                """,
            (
                s_cat if s_cat else "Teaching Staff",
                desig,
                name,
                effective_basic,
                selected_campus,
                month_filter,
                r_no,
            ),
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

      full_display_df = df[
          [
              "Staff Category",
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
      full_display_df = pd.DataFrame(
          columns=[
              "Staff Category",
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

    categories = ["Admin Staff", "Teaching Staff", "Non-Teaching Staff"]
    cat_dfs = {}

    for cat in categories:
      st.markdown(
          f"<div class='section-title'>📌 {cat.upper()} PORTION</div>",
          unsafe_allow_html=True,
      )

      cat_subset = full_display_df[full_display_df["Staff Category"] == cat]
      work_df = cat_subset.drop(columns=["Staff Category"])

      edited_cat_df = st.data_editor(
          work_df,
          num_rows="fixed",
          key=f"salary_sheet_{selected_campus}_{month_filter}_{cat}",
          column_config={
              "Staff Category": None,
          },
      )

      if not edited_cat_df.empty:
        sub_basic = edited_cat_df["Basic Salary"].sum()
        sub_ded = edited_cat_df["Total Deduction Amount"].sum()
        sub_final = edited_cat_df["Total Final Salary"].sum()

        st.markdown(
            f"""
            <div style="background-color: #f3f4f6; padding: 10px 15px; border-radius: 6px; font-weight: bold; margin-bottom: 20px; display: flex; justify-content: space-between; border-left: 5px solid #2C1654;">
                <span>Total {cat}:</span>
                <span>Basic: Rs. {sub_basic:,.2f} | Deductions: Rs. {sub_ded:,.2f} | <span style="color: green;">Final Payout: Rs. {sub_final:,.2f}</span></span>
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
          <div style="background: linear-gradient(135deg, #2C1654 0%, #4338ca 100%); color: white; padding: 15px 20px; border-radius: 8px; font-weight: bold; font-size: 16px; margin-top: 15px; margin-bottom: 25px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
              🏆 GRAND TOTAL ({selected_campus.upper()} BRANCH) — Basic: Rs. {grand_basic:,.2f} | Deductions: Rs. {grand_ded:,.2f} | Final Payout: Rs. {grand_final:,.2f}
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
          execute_non_query(
              """
                        INSERT INTO salaries (campus, reg_no, name, designation, staff_category, basic_salary, absent_days, 
                                              late_days, days_in_month, considered_red_days, reason, month_year)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
              (
                  selected_campus,
                  str(row["Reg No"]) if pd.notna(row["Reg No"]) else "",
                  str(row["Name"]),
                  str(row["Designation"])
                  if pd.notna(row["Designation"])
                  else "",
                  str(row["Staff Category"])
                  if pd.notna(row["Staff Category"])
                  else "Teaching Staff",
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
        st.success("✅ Monthly salary sheet saved successfully to Neon!")
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

        for cat in categories:
          cat_data = all_edited_combined[
              all_edited_combined["Staff Category"] == cat
          ]
          if cat_data.empty:
            continue

          pdf.set_font("Arial", "B", 11)
          pdf.cell(0, 7, f"{cat.upper()} PORTION", 0, 1, "L")

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
          for idx, row in cat_data.iterrows():
            pdf.cell(widths[0], 6, str(row["Reg No"]), 1, 0, "C")  # type: ignore
            pdf.cell(widths[1], 6, str(row["Name"])[:25], 1, 0, "L")  # type: ignore
            pdf.cell(widths[2], 6, str(row["Designation"])[:22], 1, 0, "L")  # type: ignore
            pdf.cell(widths[3], 6, f"{row['Basic Salary']:,.0f}", 1, 0, "R")  # type: ignore
            pdf.cell(widths[4], 6, str(row["Absent Days"]), 1, 0, "C")  # type: ignore
            pdf.cell(widths[5], 6, str(row["Late Days"]), 1, 0, "C")  # type: ignore
            pdf.cell(widths[6], 6, str(row["Days in Month"]), 1, 0, "C")  # type: ignore
            pdf.cell(widths[7], 6, f"{row['Per Day']:,.1f}", 1, 0, "R")  # type: ignore
            pdf.cell(
                widths[8],
                6,
                f"{row['Total Deduction Amount']:,.1f}",
                1,
                0,
                "R",
            )  # type: ignore
            pdf.cell(widths[9], 6, f"{row['Total Final Salary']:,.1f}", 1, 0, "R")  # type: ignore
            pdf.ln()

          pdf.ln(3)

        pdf_output = bytes(pdf.output())

        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_output,
            file_name=f"{selected_campus}_Salary_{month_filter}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

  elif nav_mode == "Employee Yearly Ledger":
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
      else:
        st.info("No salary records found for this employee.")
    else:
      st.info("No employee records available for this campus yet.")

  elif nav_mode == "Salary Slip Generator":
    logo_html = ""
    if os.path.exists("LOGO.png"):
      with open("LOGO.png", "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" width="65" style="vertical-align: middle; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); margin-bottom: 8px;">'

    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; margin-bottom: 25px;">
            {logo_html}
            <div style="font-size: 26px; font-weight: 800; color: #2C1654; margin-bottom: 2px;">EXCELLENCE MODEL SCHOOL</div>
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
        auto_ded_late = late_d / 3.0
        tot_units = abs_d + auto_ded_late
        net_units = max(0, tot_units - cred_d)
        tot_ded = net_units * per_day
        p_one = 1 if abs_d == 0 and late_d == 0 else 0
        plus_amount = p_one * per_day
        final_pay = b_sal - tot_ded + plus_amount

        st.markdown(
            f"""
            <div style="border: 2px solid #2C1654; padding: 25px; border-radius: 10px; background-color: #ffffff; color: #000000; max-width: 700px; margin: auto;">
                <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 5px;">
                    <img src="data:image/png;base64,{base64.b64encode(open('LOGO.png', 'rb').read()).decode() if os.path.exists('LOGO.png') else ''}" width="50" style="vertical-align: middle;">
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
                        <td><b>Designation:</b> {desig} ({s_cat})</td>
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
                        <td style="padding: 6px; text-align: right; color: #b91c1c;">- {absent_gross_amount:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px; color: #1f2937; font-size: 13px;"><b>Considered Days:</b> {cred_d}</td>
                        <td style="padding: 6px; text-align: right; color: #047857;">+ {cred_amount:,.2f}</td>
                        <td style="padding: 6px;">Late Days ({late_d} / 3)</td>
                        <td style="padding: 6px; text-align: right;">-</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px;">Punctuality Bonus (+1)</td>
                        <td style="padding: 6px; text-align: right;">{plus_amount:,.2f}</td>
                        <td style="padding: 6px;">Total Deductions</td>
                        <td style="padding: 6px; text-align: right; color: red; font-weight: bold;">{tot_ded:,.2f}</td>
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
            0,
            6,
            f"Employee Name: {name} (Reg No: {r_no}) [{s_cat}]",
            0,
            1,
            "L",
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
            f"Absent Days ({abs_d}) - Gross Deduction",
            1,
            0,
            "L",
        )
        slip_pdf.cell(100, 6, f"-{absent_gross_amount:,.2f}", 1, 1, "R")

        slip_pdf.cell(
            90,
            6,
            f"Considered Days (Saved/Waived): {cred_d}",
            1,
            0,
            "L",
        )
        slip_pdf.cell(100, 6, f"+{cred_amount:,.2f}", 1, 1, "R")

        slip_pdf.cell(
            90,
            6,
            f"Late Days ({late_d} / 3)",
            1,
            0,
            "L",
        )
        slip_pdf.cell(100, 6, "-0.00", 1, 1, "R")

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
        slip_pdf.cell(90, 8, f"Total Deductions (Net)", 1, 0, "L")
        slip_pdf.cell(100, 8, f"-{tot_ded:,.2f}", 1, 1, "R")

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
      st.info("No salary records available for this month.")

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
            FROM salaries WHERE month_year = %s GROUP BY campus;
        """
    summary_data = run_query(sum_query, (month_filter,))

    all_q = """
            SELECT basic_salary, absent_days, late_days, days_in_month, considered_red_days 
            FROM salaries WHERE month_year = %s;
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
    else:
      st.info("No data entered yet across campuses for summary.")
