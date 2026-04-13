import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px

# -------------------------------
# CONFIG + BRANDING
# -------------------------------
st.set_page_config(page_title="KhataKhat", layout="wide")

st.markdown("""
<style>
.main {background-color: #0E1117; color: white;}
h1, h2, h3 {color: #00C9A7;}
.stMetric {background-color: #1c1f26; padding: 10px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

st.markdown("# 💸 KhataKhat")
st.markdown("### AI-Powered Credit Recovery Platform")

# -------------------------------
# DATABASE
# -------------------------------
conn = sqlite3.connect("khatakhat.db", check_same_thread=False)
cursor = conn.cursor()

# Users
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

# Transactions
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
# AUTH FUNCTIONS
# -------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    try:
        cursor.execute("INSERT INTO users VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except:
        return False

def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                   (username, hash_password(password)))
    return cursor.fetchone()

# -------------------------------
# SESSION
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# -------------------------------
# DEMO MARKET DATA
# -------------------------------
market_df = pd.DataFrame({
    "Industry": ["FMCG","Textile","Electronics","FMCG","Pharma","Retail"],
    "City": ["Delhi","Surat","Mumbai","Delhi","Ahmedabad","Jaipur"],
    "Amount": [5000,12000,8000,6000,15000,4000],
    "Credit_Days": [15,30,10,12,20,8],
    "Days_Delayed": [3,20,2,8,5,9],
    "Status": ["Paid","Delayed","Paid","Delayed","Paid","Delayed"]
})

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------
def get_industry_avg_credit(industry):
    data = market_df[market_df["Industry"] == industry]
    return data["Credit_Days"].mean() if not data.empty else 15

def get_city_risk(city):
    data = market_df[market_df["City"] == city]
    return data["Days_Delayed"].mean() if not data.empty else 5

def calculate_days_overdue(due_date):
    try:
        today = datetime.today()
        due = datetime.strptime(str(due_date), "%Y-%m-%d")
        return max((today - due).days, 0)
    except:
        return 0

def categorize(days):
    if days < 5:
        return "Low"
    elif days < 15:
        return "Medium"
    else:
        return "High"

def calculate_risk(days, amount, industry, city):
    return (days * 0.5) + (amount * 0.2) + (get_city_risk(city) * 0.3)

def calculate_credit_score(days, amount):
    score = 100 - (days * 2)
    if amount > 10000:
        score -= 10
    return max(score, 0)

def generate_ai_message(name, amount, days, category, industry):
    link = f"upi://pay?pa=merchant@upi&am={amount}"
    if category == "Low":
        return f"Hi {name}, reminder for ₹{amount}. Pay: {link}"
    elif category == "Medium":
        return f"{name}, ₹{amount} pending. Most {industry} payments clear soon. Pay: {link}"
    else:
        return f"⚠️ ₹{amount} overdue by {days} days. Immediate payment required: {link}"

def predict_recovery_probability(days, amount, category):
    base = 0.8 - (days * 0.02)
    if amount > 10000:
        base -= 0.1
    if category == "High":
        base -= 0.2
    elif category == "Medium":
        base -= 0.1
    return max(min(base, 1), 0)

# -------------------------------
# LOGIN / REGISTER
# -------------------------------
if not st.session_state.logged_in:

    st.sidebar.title("Menu")
    choice = st.sidebar.radio("Select", ["Login", "Register"])

    if choice == "Login":
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")

        if st.button("Login"):
            result = login_user(user, pwd)
            if result:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

    else:
        new_user = st.text_input("New Username")
        new_pwd = st.text_input("New Password", type="password")

        if st.button("Register"):
            if create_user(new_user, new_pwd):
                st.success("Account created!")
            else:
                st.error("User already exists")

# -------------------------------
# MAIN APP
# -------------------------------
else:

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Market Insights", "Recovery Engine"])

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # ---------------- MARKET INSIGHTS ----------------
    if page == "Market Insights":

        st.header("📊 Market Intelligence")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Credit", f"₹{market_df['Amount'].sum():,.0f}")
        col2.metric("Overdue", f"₹{market_df[market_df['Status']=='Delayed']['Amount'].sum():,.0f}")
        col3.metric("Avg Delay", f"{market_df['Days_Delayed'].mean():.1f} days")

        tab1, tab2, tab3 = st.tabs(["Industry", "City", "Risk"])

        with tab1:
            data = market_df.groupby("Industry")["Credit_Days"].mean().reset_index()
            st.plotly_chart(px.bar(data, x="Industry", y="Credit_Days"))

        with tab2:
            data = market_df.groupby("City")["Days_Delayed"].mean().reset_index()
            st.plotly_chart(px.bar(data, x="City", y="Days_Delayed"))

        with tab3:
            market_df["Risk"] = market_df["Days_Delayed"].apply(categorize)
            st.plotly_chart(px.pie(market_df, names="Risk"))

    # ---------------- RECOVERY ENGINE ----------------
    else:

        st.header("💸 Recovery Engine")

        file = st.file_uploader("Upload CSV", type=["csv"])

        if file:
            df = pd.read_csv(file)

            required_cols = ["Name","Amount","Due Date","Industry","City"]
            if not all(col in df.columns for col in required_cols):
                st.error("CSV format incorrect")
                st.stop()

            results = []

            for _, row in df.iterrows():
                days = calculate_days_overdue(row['Due Date'])
                category = categorize(days)
                risk = calculate_risk(days, row['Amount'], row['Industry'], row['City'])
                credit = calculate_credit_score(days, row['Amount'])

                prob = predict_recovery_probability(days, row['Amount'], category)
                expected = row['Amount'] * prob

                msg = generate_ai_message(row['Name'], row['Amount'], days, category, row['Industry'])

                # SAVE USER DATA
                cursor.execute("""
                INSERT INTO transactions (username, customer, amount, due_date, industry, city, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    st.session_state.user,
                    row['Name'],
                    row['Amount'],
                    row['Due Date'],
                    row['Industry'],
                    row['City'],
                    "Pending"
                ))
                conn.commit()

                results.append({
                    "Name": row['Name'],
                    "Amount": row['Amount'],
                    "Days": days,
                    "Risk": round(risk,2),
                    "Category": category,
                    "Credit Score": credit,
                    "Recovery %": round(prob*100,1),
                    "Expected": round(expected,0),
                    "Message": msg
                })

            result_df = pd.DataFrame(results)

            # KPIs
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total Due", f"₹{result_df['Amount'].sum():,.0f}")
            c2.metric("Expected", f"₹{result_df['Expected'].sum():,.0f}")
            c3.metric("High Risk", len(result_df[result_df["Category"]=="High"]))
            c4.metric("Avg Recovery", f"{result_df['Recovery %'].mean():.1f}%")

            # Charts
            st.plotly_chart(px.bar(result_df, x="Name", y="Risk"))
            st.plotly_chart(px.pie(result_df, names="Category"))

            # Forecast
            result_df["Index"] = range(1,len(result_df)+1)
            result_df["Cum"] = result_df["Expected"].cumsum()
            st.plotly_chart(px.line(result_df, x="Index", y="Cum", title="Recovery Forecast"))

            # WhatsApp Simulation
            st.subheader("📲 WhatsApp Simulation")
            for i,row in result_df.iterrows():
                with st.expander(row["Name"]):
                    st.write(row["Message"])

                    if st.button("Send", key=f"send_{i}"):
                        st.success("Sent ✅")

                    if st.button("Mark Paid", key=f"paid_{i}"):
                        cursor.execute("""
                        UPDATE transactions
                        SET status='Recovered'
                        WHERE customer=? AND username=?
                        """, (row["Name"], st.session_state.user))
                        conn.commit()
                        st.success("Marked as Recovered ✅")

            # Performance Tracking
            st.markdown("---")
            st.subheader("📊 Recovery Performance")

            history = pd.read_sql(f"""
            SELECT * FROM transactions WHERE username='{st.session_state.user}'
            """, conn)

            if not history.empty:
                total = len(history)
                recovered = len(history[history["status"]=="Recovered"])
                rate = (recovered/total)*100 if total else 0

                p1,p2,p3 = st.columns(3)
                p1.metric("Total Cases", total)
                p2.metric("Recovered", recovered)
                p3.metric("Recovery Rate", f"{rate:.1f}%")

                history["id"] = history["id"].astype(int)
                st.plotly_chart(px.line(history, x="id", y="amount"))

            st.dataframe(result_df)
