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
        return f"Hi {name}, a gentle reminder for your pending amount of ₹{amount}. Pay here: {link}"
    elif category == "Medium":
        return f"Hello {name}, ₹{amount} is currently pending. Most {industry} payments clear soon. Please complete yours: {link}"
    else:
        return f"⚠️ URGENT: {name}, ₹{amount} is overdue by {days} days. Immediate payment is required to maintain your credit score: {link}"

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

    st.sidebar.title("User Portal")
    choice = st.sidebar.radio("Select Action", ["Login", "Register"])

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
                st.success("Account created successfully!")
            else:
                st.error("User already exists")

# -------------------------------
# MAIN APP
# -------------------------------
else:

    st.sidebar.title("Settings")
    st.sidebar.markdown(f"Logged in as: **{st.session_state.user}**")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # Replaced Navigation Sidebar with Main Tabs
    tab_market, tab_recovery = st.tabs(["📊 Market Insights", "💸 Recovery Engine"])

    # ---------------- MARKET INSIGHTS ----------------
    with tab_market:
        st.header("📊 Market Intelligence")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Market Credit", f"₹{market_df['Amount'].sum():,.0f}")
        col2.metric("Total Overdue", f"₹{market_df[market_df['Status']=='Delayed']['Amount'].sum():,.0f}")
        col3.metric("Average Delay", f"{market_df['Days_Delayed'].mean():.1f} days")

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Industry Analysis", "City Analysis", "Risk Distribution"])

        with sub_tab1:
            data = market_df.groupby("Industry")["Credit_Days"].mean().reset_index()
            fig = px.bar(data, x="Industry", y="Credit_Days", title="Average Allowed Credit Days by Industry")
            st.plotly_chart(fig, use_container_width=True)

        with sub_tab2:
            data = market_df.groupby("City")["Days_Delayed"].mean().reset_index()
            fig = px.bar(data, x="City", y="Days_Delayed", title="Average Payment Delay Days by City")
            st.plotly_chart(fig, use_container_width=True)

        with sub_tab3:
            market_df["Risk"] = market_df["Days_Delayed"].apply(categorize)
            fig = px.pie(market_df, names="Risk", title="Market Risk Profiles Distribution")
            st.plotly_chart(fig, use_container_width=True)

    # ---------------- RECOVERY ENGINE ----------------
    with tab_recovery:
        st.header("💸 Recovery Engine")

        file = st.file_uploader("Upload Recovery Data CSV", type=["csv"])

        if file:
            df = pd.read_csv(file)

            required_cols = ["Name", "Amount", "Paid Amount", "Due Date", "Industry", "City"]
            if not all(col in df.columns for col in required_cols):
                st.error(f"CSV format incorrect. Required columns: {', '.join(required_cols)}")
                st.stop()

            results = []

            for _, row in df.iterrows():
                pending_amount = row['Amount'] - row['Paid Amount']
                
                # Skip fully paid users
                if pending_amount <= 0:
                    continue

                days = calculate_days_overdue(row['Due Date'])
                category = categorize(days)
                risk = calculate_risk(days, pending_amount, row['Industry'], row['City'])
                credit = calculate_credit_score(days, pending_amount)
                prob = predict_recovery_probability(days, pending_amount, category)
                expected = pending_amount * prob
                msg = generate_ai_message(row['Name'], pending_amount, days, category, row['Industry'])

                # Store all context for the dataframe and DB
                results.append({
                    "Name": row['Name'],
                    "Amount": pending_amount,
                    "Due Date": row['Due Date'],
                    "Industry": row['Industry'],
                    "City": row['City'],
                    "Days": days,
                    "Risk Score": round(risk, 2),
                    "Category": category,
                    "Credit Score": credit,
                    "Recovery %": round(prob * 100, 1),
                    "Expected": round(expected, 0),
                    "Message": msg
                })

            result_df = pd.DataFrame(results)

            if result_df.empty:
                st.success("All outstanding balances have been fully paid. No pending recoveries!")
            else:
                st.markdown("---")
                st.subheader("📋 Processed Recovery Data")
                
                # Display tabular format of the authentic data without the long message column
                st.dataframe(result_df.drop(columns=["Message"]), use_container_width=True)
                
                # Button to optionally save data to DB
                if st.button("💾 Save Data to System"):
                    for _, row in result_df.iterrows():
                        cursor.execute("""
                        INSERT INTO transactions (username, customer, amount, due_date, industry, city, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            st.session_state.user, row['Name'], row['Amount'], 
                            row['Due Date'], row['Industry'], row['City'], "Pending"
                        ))
                    conn.commit()
                    st.success("Data securely saved to your transaction records!")

                # KPIs
                st.markdown("---")
                st.subheader("🎯 Recovery Targets")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Pending Due", f"₹{result_df['Amount'].sum():,.0f}")
                c2.metric("Expected Recovery", f"₹{result_df['Expected'].sum():,.0f}")
                c3.metric("High Risk Accounts", len(result_df[result_df["Category"] == "High"]))
                c4.metric("Avg Recovery Prob.", f"{result_df['Recovery %'].mean():.1f}%")

                # Charts
                st.markdown("<br>", unsafe_allow_html=True)
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig1 = px.bar(result_df, x="Name", y="Risk Score", title="Risk Score by Customer")
                    st.plotly_chart(fig1, use_container_width=True)
                with col_chart2:
                    fig2 = px.pie(result_df, names="Category", title="Account Risk Category Distribution")
                    st.plotly_chart(fig2, use_container_width=True)

                # Forecast
                result_df["Index"] = range(1, len(result_df) + 1)
                result_df["Cum"] = result_df["Expected"].cumsum()
                fig_line = px.line(result_df, x="Index", y="Cum", title="Expected Recovery Forecast (Cumulative Path)")
                st.plotly_chart(fig_line, use_container_width=True)

                # Improved WhatsApp Simulation UI
                st.markdown("---")
                st.subheader("📲 WhatsApp Communication Hub")
                st.write("Select a customer from the dropdown below to preview and send targeted payment reminders.")
                
                customer_list = result_df["Name"].tolist()
                selected_customer = st.selectbox("Select Target Customer:", customer_list)
                
                if selected_customer:
                    customer_info = result_df[result_df["Name"] == selected_customer].iloc[0]
                    
                    st.info(f"**Draft Message:**\n\n{customer_info['Message']}")
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("Send WhatsApp 💬", key="send_wa", use_container_width=True):
                            st.success(f"Reminder sent successfully to {selected_customer}! ✅")
                    with btn_col2:
                        if st.button("Mark as Recovered 💰", key="mark_paid", use_container_width=True):
                            cursor.execute("""
                            UPDATE transactions
                            SET status='Recovered'
                            WHERE customer=? AND username=?
                            """, (selected_customer, st.session_state.user))
                            conn.commit()
                            st.success(f"Outstanding amount for {selected_customer} has been marked as recovered! ✅")

            # Performance Tracking
            st.markdown("---")
            st.subheader("📈 Personal Recovery Performance")

            history = pd.read_sql(f"""
            SELECT * FROM transactions WHERE username='{st.session_state.user}'
            """, conn)

            if not history.empty:
                total_cases = len(history)
                recovered_cases = len(history[history["status"] == "Recovered"])
                recovery_rate = (recovered_cases / total_cases) * 100 if total_cases else 0

                p1, p2, p3 = st.columns(3)
                p1.metric("Total Cases Assigned", total_cases)
                p2.metric("Cases Recovered", recovered_cases)
                p3.metric("Recovery Success Rate", f"{recovery_rate:.1f}%")

                history["id"] = history["id"].astype(int)
                fig_perf = px.line(history, x="id", y="amount", title="Historical Recovery Task Trend")
                st.plotly_chart(fig_perf, use_container_width=True)
            else:
                st.write("Save some data to the system to track your historical recovery performance.")
