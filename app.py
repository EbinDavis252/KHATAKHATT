import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import urllib.parse

# -------------------------------
# CONFIG + PREMIUM UI BRANDING
# -------------------------------
st.set_page_config(page_title="KhataKhat", layout="wide", initial_sidebar_state="expanded")

# Premium Custom CSS (Glassmorphism + Gradients)
st.markdown("""
<style>
/* Premium Gradient Background */
.stApp {
    background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
    color: #ffffff;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
/* Neon Teal Headers */
h1, h2, h3 { 
    color: #00FFC2 !important; 
    font-weight: 700; 
    text-shadow: 1px 1px 4px rgba(0,0,0,0.5); 
}
/* Glassmorphism Metric Cards */
div[data-testid="metric-container"] {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    backdrop-filter: blur(10px);
}
/* Upgraded Smart Advice Info Boxes */
div.stInfo {
    background: rgba(0, 201, 167, 0.1) !important;
    border-left: 5px solid #00FFC2 !important;
    color: #E0F7FA !important;
    font-size: 16px !important;
    border-radius: 4px;
}
/* Clean Tabs */
button[data-baseweb="tab"] {
    color: #A0C4C7 !important;
    font-weight: 600;
}
button[aria-selected="true"] {
    color: #00FFC2 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("# 💸 KhataKhat")
st.markdown("### AI-Powered Credit Recovery Platform for Smart Vyaparis")

# -------------------------------
# DATABASE
# -------------------------------
conn = sqlite3.connect("khatakhat.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, customer TEXT, amount REAL, due_date TEXT, industry TEXT, city TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS communications (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, customer TEXT, message TEXT, timestamp TEXT, status TEXT)")
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
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_password(password)))
    return cursor.fetchone()

admin_check = cursor.execute("SELECT * FROM users WHERE username='admin'").fetchone()
if not admin_check:
    create_user("admin", "admin123")

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
def get_city_risk(city):
    data = market_df[market_df["City"] == city]
    return data["Days_Delayed"].mean() if not data.empty else 5

def calculate_days_overdue(due_date):
    try:
        today = datetime.today()
        due = datetime.strptime(str(due_date), "%Y-%m-%d")
        return max((today - due).days, 0)
    except ValueError:
        return 0

def categorize(days):
    if days < 5: return "Low"
    elif days < 15: return "Medium"
    else: return "High"

def calculate_risk(days, amount, industry, city):
    return (days * 0.5) + (amount * 0.2) + (get_city_risk(city) * 0.3)

def calculate_credit_score(days, amount):
    score = 100 - (days * 2)
    if amount > 10000: score -= 10
    return max(score, 0)

def generate_ai_message(name, amount, days, category, industry):
    link = f"upi://pay?pa=merchant@upi&am={amount}"
    if category == "Low":
        return f"Hi {name}, a gentle reminder for your pending amount of Rs. {amount}. Pay here: {link}"
    elif category == "Medium":
        return f"Hello {name}, Rs. {amount} is currently pending. Most {industry} payments clear soon. Please complete yours: {link}"
    else:
        return f"URGENT: {name}, Rs. {amount} is overdue by {days} days. Immediate payment is required: {link}"

def predict_recovery_probability(days, amount, category):
    base = 0.8 - (days * 0.02)
    if amount > 10000: base -= 0.1
    if category == "High": base -= 0.2
    elif category == "Medium": base -= 0.1
    return max(min(base, 1), 0)

def generate_pdf_report(df):
    pdf = FPDF()
    pdf.add_page()
    
    def clean_txt(text):
        return str(text).replace("₹", "Rs.").replace("⚠️", "[URGENT]").encode('latin-1', 'ignore').decode('latin-1')
    
    # Header
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(200, 10, txt="KhataKhat - Active Recovery & AI Analysis Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    
    # AI Summary Section
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="AI Business Analysis & Advice:", ln=True)
    pdf.set_font("Arial", size=11)
    high_risk_count = len(df[df['Category'] == 'High'])
    total_due = df['Amount'].sum()
    expected_cash = df['Expected'].sum()
    
    analysis_text = f"""Result: You have {high_risk_count} 'High Risk' customers who are severely delaying payments. 
Action: Stop all new supply to these buyers immediately. Focus strictly on cash recovery.
Result: Out of Rs. {total_due:,.0f} stuck in the market, AI predicts you can safely recover Rs. {expected_cash:,.0f} this week by following the automated message strategy.
Action: Send automated reminders to Low/Medium risk today, and personally call the High Risk accounts."""
    
    pdf.multi_cell(0, 6, txt=clean_txt(analysis_text))
    pdf.ln(10)
    
    # Summary Metrics
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=f"Total Pending Due: Rs. {total_due:,.0f} | Expected Recovery: Rs. {expected_cash:,.0f}", ln=True)
    pdf.ln(5)
    
    # Data Rows
    pdf.set_font("Arial", size=10)
    for index, row in df.iterrows():
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, txt=clean_txt(f"Customer: {row['Name']} ({row['Industry']} - {row['City']})"), ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, txt=clean_txt(f"Due: Rs. {row['Amount']} | Days Overdue: {row['Days']} | Risk: {row['Category']}"), ln=True)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 6, txt=clean_txt(f"Auto-Message: {row['Message']}"))
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)
        
    return pdf.output(dest="S").encode("latin-1")

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
            if login_user(user, pwd):
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

    tab_names = ["📊 Market Insights", "💸 Recovery Engine"]
    is_admin = st.session_state.user == "admin"
    if is_admin: tab_names.append("🛡️ Admin Panel")

    tabs = st.tabs(tab_names)

    # ---------------- MARKET INSIGHTS ----------------
    with tabs[0]:
        st.header("📊 Market Intelligence")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Market Credit", f"₹{market_df['Amount'].sum():,.0f}")
        col2.metric("Total Overdue", f"₹{market_df[market_df['Status']=='Delayed']['Amount'].sum():,.0f}")
        col3.metric("Average Delay", f"{market_df['Days_Delayed'].mean():.1f} days")

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Industry Analysis", "City Analysis", "Risk Distribution"])

        with sub_tab1:
            data = market_df.groupby("Industry")["Credit_Days"].mean().reset_index()
            fig = px.bar(data, x="Industry", y="Credit_Days", title="Credit Days by Industry")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)
            st.info("💡 **Smart Advice:**\n* **Result:** Your FMCG buyers clear payments fast (15 days), while Textile buyers hold your money for over a month.\n* **Action:** To maintain cash flow in your shop, demand a 50% advance for all new Textile orders.")

        with sub_tab2:
            data = market_df.groupby("City")["Days_Delayed"].mean().reset_index()
            fig = px.bar(data, x="City", y="Days_Delayed", title="Payment Delay by City")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)
            st.info("💡 **Smart Advice:**\n* **Result:** Buyers from Surat are delaying payments by 20 extra days, blocking your capital. Delhi buyers are paying much faster.\n* **Action:** Prioritize selling to Delhi right now. Call your Surat buyers personally before sending them any new stock.")

        with sub_tab3:
            market_df["Risk"] = market_df["Days_Delayed"].apply(categorize)
            fig = px.pie(market_df, names="Risk", title="Risk Distribution")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)
            st.info("💡 **Smart Advice:**\n* **Result:** A dangerous amount of your money is stuck in the 'High Risk' slice. These are people who might never pay.\n* **Action:** Stop completely. Do not give even 1 Rupee of new credit to these buyers until they clear at least half their old bills.")

    # ---------------- RECOVERY ENGINE ----------------
    with tabs[1]:
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
                if pending_amount <= 0: continue

                days = calculate_days_overdue(row['Due Date'])
                category = categorize(days)
                risk = calculate_risk(days, pending_amount, row['Industry'], row['City'])
                credit = calculate_credit_score(days, pending_amount)
                prob = predict_recovery_probability(days, pending_amount, category)
                expected = pending_amount * prob
                msg = generate_ai_message(row['Name'], pending_amount, days, category, row['Industry'])

                results.append({
                    "Name": row['Name'], "Amount": pending_amount, "Due Date": row['Due Date'],
                    "Industry": row['Industry'], "City": row['City'], "Days": days,
                    "Risk Score": round(risk, 2), "Category": category, "Credit Score": credit,
                    "Recovery %": round(prob * 100, 1), "Expected": round(expected, 0), "Message": msg
                })

            result_df = pd.DataFrame(results)

            if result_df.empty:
                st.success("All outstanding balances have been fully paid. No pending recoveries!")
            else:
                st.markdown("---")
                st.subheader("📋 Processed Recovery Data")
                st.dataframe(result_df.drop(columns=["Message"]), use_container_width=True)
                
                if st.button("💾 Save Data to System"):
                    for _, row in result_df.iterrows():
                        cursor.execute("""
                        INSERT INTO transactions (username, customer, amount, due_date, industry, city, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (st.session_state.user, row['Name'], row['Amount'], row['Due Date'], row['Industry'], row['City'], "Pending"))
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
                    fig1 = px.bar(result_df, x="Name", y="Risk Score", title="Danger Score by Customer")
                    fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
                    st.plotly_chart(fig1, use_container_width=True)
                    st.info("💡 **Smart Advice:**\n* **Result:** The highest bars show the customers most likely to run away with your money.\n* **Action:** Pick up your phone and call the tallest bar customer right now. Don't wait for WhatsApp.")
                
                with col_chart2:
                    fig2 = px.pie(result_df, names="Category", title="Account Risk Category")
                    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
                    st.plotly_chart(fig2, use_container_width=True)
                    st.info("💡 **Smart Advice:**\n* **Result:** This splits your customers into 'Safe' (Low) and 'Danger' (High).\n* **Action:** Use the KhataKhat automatic WhatsApp button for 'Low' risk. Save your own personal energy to deal with the 'High' risk buyers.")

                # Forecast
                result_df["Index"] = range(1, len(result_df) + 1)
                result_df["Cum"] = result_df["Expected"].cumsum()
                fig_line = px.line(result_df, x="Index", y="Cum", title="Expected Cash Flow This Week")
                fig_line.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
                st.plotly_chart(fig_line, use_container_width=True)
                st.info("💡 **Smart Advice:**\n* **Result:** If you send all the automated reminders today, this rising line shows how much cash will enter your bank account over the next few days.\n* **Action:** Look at the final top number on this line. Only commit to paying your own suppliers based on that number.")

                # WhatsApp Hub
                st.markdown("---")
                st.subheader("📲 WhatsApp Communication Hub")
                st.write("Select a customer below to instantly send a targeted payment reminder.")
                
                customer_list = result_df["Name"].tolist()
                selected_customer = st.selectbox("Select Target Customer:", customer_list)
                
                if selected_customer:
                    customer_info = result_df[result_df["Name"] == selected_customer].iloc[0]
                    st.info(f"**AI Draft Message:**\n\n{customer_info['Message']}")
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        target_phone = st.text_input("Customer Phone (Include 91, no +)", value="919876543210")
                        encoded_msg = urllib.parse.quote(customer_info['Message'])
                        wa_link = f"https://wa.me/{target_phone}?text={encoded_msg}"
                        st.link_button("Send via WhatsApp 💬", wa_link, use_container_width=True)
                        
                        if st.button("Log as Sent (For Demo)"):
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cursor.execute("INSERT INTO transactions (username, customer, amount, due_date, industry, city, status) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                           (st.session_state.user, selected_customer, customer_info['Amount'], customer_info['Due Date'], customer_info['Industry'], customer_info['City'], "Pending"))
                            cursor.execute("INSERT INTO communications (username, customer, message, timestamp, status) VALUES (?, ?, ?, ?, ?)", 
                                           (st.session_state.user, selected_customer, customer_info['Message'], timestamp, "Sent (Demo Link)"))
                            conn.commit()
                            st.success("Logged to Admin Panel! ✅")
                            
                    with btn_col2:
                        if st.button("Mark as Recovered 💰", key="mark_paid", use_container_width=True):
                            cursor.execute("UPDATE transactions SET status='Recovered' WHERE customer=? AND username=?", (selected_customer, st.session_state.user))
                            conn.commit()
                            st.success(f"Money from {selected_customer} recovered! ✅")

                # Performance Tracking
                st.markdown("---")
                st.subheader("📈 Personal Recovery Performance")
                history = pd.read_sql("SELECT * FROM transactions WHERE username=?", conn, params=(st.session_state.user,))

                if not history.empty:
                    total_cases = len(history)
                    recovered_cases = len(history[history["status"] == "Recovered"])
                    recovery_rate = (recovered_cases / total_cases) * 100 if total_cases else 0

                    p1, p2, p3 = st.columns(3)
                    p1.metric("Total Cases Handled", total_cases)
                    p2.metric("Successful Recoveries", recovered_cases)
                    p3.metric("Your Success Rate", f"{recovery_rate:.1f}%")

                    history["id"] = pd.to_numeric(history["id"], errors='coerce')
                    history["amount"] = pd.to_numeric(history["amount"], errors='coerce')
                    safe_plot_data = history[["id", "amount"]]
                    
                    fig_perf = px.line(safe_plot_data, x="id", y="amount", title="Your Recovery Journey")
                    fig_perf.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
                    st.plotly_chart(fig_perf, use_container_width=True)
                    st.info("💡 **Smart Advice:** Keep pushing this line! The more you use the app to follow up, the more cases you will mark as 'Recovered'.")
                else:
                    st.write("Save data to track your business growth.")

                # PDF DOWNLOAD MOVED TO THE BOTTOM
                st.markdown("---")
                st.subheader("📄 Daily Summary Report")
                st.write("Download your complete AI-analyzed recovery report to share with your partners or keep for your records.")
                pdf_bytes = generate_pdf_report(result_df)
                st.download_button(
                    label="Download Detailed PDF Analysis",
                    data=pdf_bytes,
                    file_name=f"KhataKhat_Vyapari_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    # ---------------- ADMIN PANEL ----------------
    if is_admin:
        with tabs[2]:
            st.header("🛡️ Administrator Security Panel")
            st.subheader("📡 WhatsApp Communication Logs")
            comm_data = pd.read_sql("SELECT * FROM communications ORDER BY id DESC", conn)
            if not comm_data.empty: st.dataframe(comm_data, use_container_width=True)
            else: st.info("No communications yet.")
                
            st.markdown("---")
            st.subheader("🗄️ Master Transaction Database")
            tx_data = pd.read_sql("SELECT * FROM transactions", conn)
            if not tx_data.empty: st.dataframe(tx_data, use_container_width=True)
            else: st.info("Database is empty.")
