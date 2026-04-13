import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(page_title="KhataKhat", layout="wide")

st.title("💸 KhataKhat")
st.caption("AI-Powered Credit Recovery Platform")

# -------------------------------
# DATABASE
# -------------------------------
conn = sqlite3.connect("khatakhat.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    customer TEXT,
    amount REAL,
    due_date TEXT,
    industry TEXT,
    city TEXT,
    status TEXT
)
""")

conn.commit()

# -------------------------------
# AUTH
# -------------------------------
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def create_user(u, p):
    try:
        cursor.execute("INSERT INTO users VALUES (?, ?)", (u, hash_password(p)))
        conn.commit()
        return True
    except:
        return False

def login_user(u, p):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                   (u, hash_password(p)))
    return cursor.fetchone()

# -------------------------------
# SESSION
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# -------------------------------
# FUNCTIONS
# -------------------------------
def calculate_days_overdue(due_date):
    try:
        return max((datetime.today() - datetime.strptime(str(due_date), "%Y-%m-%d")).days, 0)
    except:
        return 0

def categorize(days):
    return "Low" if days < 5 else "Medium" if days < 15 else "High"

def calculate_risk(days, amount):
    return (days * 0.5) + (amount * 0.2)

def calculate_credit_score(days, amount):
    score = 100 - (days * 2)
    if amount > 10000:
        score -= 10
    return max(score, 0)

def predict_recovery_probability(days, amount, category, status):
    base = 0.8 - (days * 0.02)

    if amount > 10000:
        base -= 0.1

    if category == "High":
        base -= 0.2

    if status == "Defaulted":
        base -= 0.3

    return max(min(base, 1), 0)

def generate_ai_message(name, amount, days, category):
    link = f"upi://pay?pa=merchant@upi&am={amount}"

    if category == "Low":
        return f"Hi {name}, reminder for ₹{amount}. Pay: {link}"
    elif category == "Medium":
        return f"{name}, ₹{amount} pending. Kindly clear soon: {link}"
    else:
        return f"⚠️ ₹{amount} overdue by {days} days. Immediate payment required: {link}"

# -------------------------------
# LOGIN
# -------------------------------
if not st.session_state.logged_in:

    choice = st.sidebar.radio("Menu", ["Login", "Register"])

    if choice == "Login":
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            if login_user(u, p):
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid credentials")

    else:
        u = st.text_input("New Username")
        p = st.text_input("New Password", type="password")

        if st.button("Register"):
            if create_user(u, p):
                st.success("Account created")
            else:
                st.error("User exists")

# -------------------------------
# MAIN APP
# -------------------------------
else:

    page = st.sidebar.radio("Go to", ["Recovery Engine"])

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # ---------------- RECOVERY ENGINE ----------------
    st.header("💸 Recovery Engine")

    file = st.file_uploader("Upload CSV", type=["csv"])

    if file:
        df = pd.read_csv(file)

        required = ["Name","Amount","Due Date","Industry","City"]
        if not all(col in df.columns for col in required):
            st.error("Missing required columns")
            st.stop()

        results = []

        for _, row in df.iterrows():

            days = calculate_days_overdue(row["Due Date"])
            category = categorize(days)
            risk = calculate_risk(days, row["Amount"])
            credit = calculate_credit_score(days, row["Amount"])

            status = row["Status"] if "Status" in df.columns else "Unknown"

            paid_amount = row["Paid Amount"] if "Paid Amount" in df.columns else 0
            remaining = row["Amount"] - paid_amount

            prob = predict_recovery_probability(days, row["Amount"], category, status)
            expected = remaining * prob

            msg = generate_ai_message(row["Name"], remaining, days, category)

            # Save
            cursor.execute("""
            INSERT INTO transactions (username, customer, amount, due_date, industry, city, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                st.session_state.user,
                row["Name"],
                row["Amount"],
                row["Due Date"],
                row["Industry"],
                row["City"],
                status
            ))
            conn.commit()

            results.append({
                "Name": row["Name"],
                "Amount": row["Amount"],
                "Remaining": remaining,
                "Days": days,
                "Category": category,
                "Credit Score": credit,
                "Recovery %": round(prob*100,1),
                "Expected": round(expected,0),
                "Status": status,
                "Message": msg
            })

        result_df = pd.DataFrame(results)

        # KPIs
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Remaining", f"₹{result_df['Remaining'].sum():,.0f}")
        c2.metric("Expected Recovery", f"₹{result_df['Expected'].sum():,.0f}")
        c3.metric("High Risk", len(result_df[result_df["Category"]=="High"]))

        # Charts
        st.plotly_chart(px.bar(result_df, x="Name", y="Expected"))
        st.plotly_chart(px.pie(result_df, names="Category"))

        # Forecast
        result_df["Index"] = range(1,len(result_df)+1)
        result_df["Cum"] = result_df["Expected"].cumsum()
        st.plotly_chart(px.line(result_df, x="Index", y="Cum", title="Recovery Forecast"))

        # Messages
        st.subheader("📲 Messages")
        for i,row in result_df.iterrows():
            with st.expander(row["Name"]):
                st.write(row["Message"])

        st.dataframe(result_df)
