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
st.set_page_config(page_title="KhataKhat AI", layout="wide", initial_sidebar_state="expanded")

# Ultra-Premium Dark Theme CSS
st.markdown("""
<style>
/* Deep Charcoal Background */
.stApp {
    background-color: #0a0e17;
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
/* Hide default Streamlit branding for app feel */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Neon Accents for Headers */
h1, h2, h3 { 
    color: #00e6b8 !important; 
    font-weight: 700; 
    letter-spacing: -0.5px;
}

/* Glassmorphism Metric Cards */
div[data-testid="metric-container"] {
    background: #111827;
    border: 1px solid #1f2937;
    border-left: 4px solid #00e6b8;
    padding: 1.2rem;
    border-radius: 10px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    transition: transform 0.2s ease;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
}

/* Clean Tabs */
button[data-baseweb="tab"] {
    color: #9ca3af !important;
    font-size: 16px !important;
    font-weight: 500;
}
button[aria-selected="true"] {
    color: #00e6b8 !important;
    border-bottom: 2px solid #00e6b8 !important;
}

/* Dataframe styling */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>💸 KhataKhat <span style='color: #ffffff; font-size: 24px; font-weight: 400;'>| Enterprise Receivables Engine</span></h1>", unsafe_allow_html=True)

# Custom Insight Box to replace "Smart Advice"
def strategic_insight(observation, action):
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #111827 0%, #1f2937 100%); border-left: 4px solid #00e6b8; padding: 16px; border-radius: 6px; margin-top: 15px; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
        <h4 style="color: #00e6b8; margin-top: 0px; margin-bottom: 12px; font-size: 15px; text-transform: uppercase; letter-spacing: 1px;">⚡ Strategic AI Insight</h4>
        <p style="margin-bottom: 8px; font-size: 14px; color: #d1d5db;"><strong style="color: #ffffff;">Observation:</strong> {observation}</p>
        <p style="margin-bottom: 0px; font-size: 14px; color: #d1d5db;"><strong style="color: #ffffff;">Action Plan:</strong> {action}</p>
    </div>
    """, unsafe_allow_html=True)

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
    
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(200, 10, txt="KhataKhat - Active Recovery Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Executive Overview:", ln=True)
    pdf.set_font("Arial", size=11)
    
    total_due = df['Amount'].sum()
    expected_cash = df['Expected'].sum()
    
    analysis_text = f"Total Pending Due: Rs. {total_due:,.0f} | AI Expected Recovery: Rs. {expected_cash:,.0f}"
    pdf.multi_cell(0, 6, txt=clean_txt(analysis_text))
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10)
    for index, row in df.iterrows():
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, txt=clean_txt(f"Customer: {row['Name']} ({row['Industry']} - {row['City']})"), ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, txt=clean_txt(f"Due: Rs. {row['Amount']} | Days Overdue: {row['Days']} | Risk: {row['Category']}"), ln=True)
        pdf.ln(4)
        
    return pdf.output(dest="S").encode("latin-1")

# -------------------------------
# LOGIN / REGISTER
# -------------------------------
if not st.session_state.logged_in:
    st.sidebar.title("Secure Portal")
    choice = st.sidebar.radio("Authentication", ["Login", "Register"])

    if choice == "Login":
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Access Platform", use_container_width=True):
            if login_user(user, pwd):
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        new_user = st.text_input("New Username")
        new_pwd = st.text_input("New Password", type="password")
        if st.button("Create Account", use_container_width=True):
            if create_user(new_user, new_pwd):
                st.success("Account created successfully!")
            else:
                st.error("User already exists")

# -------------------------------
# MAIN APP
# -------------------------------
else:
    st.sidebar.title("Control Panel")
    st.sidebar.markdown(f"User: **{st.session_state.user}**")
    
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

    tab_names = ["📊 Macro Insights", "💸 Recovery Engine"]
    is_admin = st.session_state.user == "admin"
    if is_admin: tab_names.append("🛡️ Admin Database")

    tabs = st.tabs(tab_names)

    # ---------------- MARKET INSIGHTS ----------------
    with tabs[0]:
        st.header("📊 Macro Intelligence")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Market Credit", f"₹{market_df['Amount'].sum():,.0f}")
        col2.metric("Total Capital Stuck", f"₹{market_df[market_df['Status']=='Delayed']['Amount'].sum():,.0f}")
        col3.metric("System Average Delay", f"{market_df['Days_Delayed'].mean():.1f} days")

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Industry Analytics", "Geographic Analytics", "Risk Stratification"])

        with sub_tab1:
            data = market_df.groupby("Industry")["Credit_Days"].mean().reset_index()
            fig = px.bar(data, x="Industry", y="Credit_Days", title="Credit Cycle by Industry", color="Credit_Days", color_continuous_scale="Teal", template="plotly_dark")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            strategic_insight(
                "FMCG counterparties exhibit high liquidity, clearing within 15 days, whereas Textile buyers are extending credit cycles beyond a month.",
                "Mandate a 50% upfront payment structure for all future Textile wholesale orders to mitigate cash flow disruption."
            )

        with sub_tab2:
            data = market_df.groupby("City")["Days_Delayed"].mean().reset_index()
            fig = px.bar(data, x="City", y="Days_Delayed", title="Capital Delay by Region", color="Days_Delayed", color_continuous_scale="Reds", template="plotly_dark")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            strategic_insight(
                "Counterparties in Surat are severely stretching working capital cycles (+20 days delay). Delhi accounts remain highly liquid.",
                "Reroute current inventory allocation to Delhi-based distributors. Initiate manual recovery protocols for Surat."
            )

        with sub_tab3:
            market_df["Risk"] = market_df["Days_Delayed"].apply(categorize)
            fig = px.pie(market_df, names="Risk", title="Portfolio Risk Distribution", hole=0.4, color="Risk", color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}, template="plotly_dark")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            strategic_insight(
                "A significant tranche of receivables is currently flagged as 'High Risk', indicating high probability of default.",
                "Suspend all credit extensions to High Risk profiles immediately until past-due balances are reduced by 50%."
            )

    # ---------------- RECOVERY ENGINE ----------------
    with tabs[1]:
        st.header("💸 Recovery Engine")
        
        # Explicit instruction for the exact file name
        st.markdown("<p style='color: #9ca3af;'>Please upload your current receivables ledger. File must be named <b>udhaar_data.csv</b>.</p>", unsafe_allow_html=True)
        file = st.file_uploader("", type=["csv"])

        if file:
            df = pd.read_csv(file)
            required_cols = ["Name", "Amount", "Paid Amount", "Due Date", "Industry", "City"]
            if not all(col in df.columns for col in required_cols):
                st.error(f"Schema mismatch. Required headers: {', '.join(required_cols)}")
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
                st.success("Ledger clear. Zero outstanding balances detected.")
            else:
                st.markdown("---")
                st.subheader("📋 Live Ledger Analysis")
                st.dataframe(result_df.drop(columns=["Message"]), use_container_width=True)
                
                if st.button("💾 Synchronize to Database"):
                    for _, row in result_df.iterrows():
                        cursor.execute("""
                        INSERT INTO transactions (username, customer, amount, due_date, industry, city, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (st.session_state.user, row['Name'], row['Amount'], row['Due Date'], row['Industry'], row['City'], "Pending"))
                    conn.commit()
                    st.success("Ledger synchronized successfully.")

                # KPIs
                st.markdown("---")
                st.subheader("🎯 Optimization Targets")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Gross Receivables", f"₹{result_df['Amount'].sum():,.0f}")
                c2.metric("Projected Inflow", f"₹{result_df['Expected'].sum():,.0f}")
                c3.metric("Critical Accounts", len(result_df[result_df["Category"] == "High"]))
                c4.metric("Mean Recovery Probability", f"{result_df['Recovery %'].mean():.1f}%")

                # Charts
                st.markdown("<br>", unsafe_allow_html=True)
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig1 = px.bar(result_df, x="Name", y="Risk Score", title="Default Probability Index", color="Risk Score", color_continuous_scale="Turbo", template="plotly_dark")
                    fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig1, use_container_width=True)
                    strategic_insight(
                        "Spikes in the DPI (Default Probability Index) isolate accounts most likely to write off.",
                        "Bypass automated channels for peak-risk accounts. Initiate direct phone contact or field visits."
                    )
                
                with col_chart2:
                    fig2 = px.pie(result_df, names="Category", title="Exposure Segmentation", hole=0.4, color="Category", color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}, template="plotly_dark")
                    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig2, use_container_width=True)
                    strategic_insight(
                        "Visualizes total capital tied up across safety tiers.",
                        "Deploy automated UPI links to 'Low' tier accounts. Reserve manual collections bandwidth for the 'High' tier."
                    )

                # Forecast
                result_df = result_df.sort_values(by="Expected", ascending=False)
                result_df["Index"] = range(1, len(result_df) + 1)
                result_df["Cum"] = result_df["Expected"].cumsum()
                fig_line = px.area(result_df, x="Index", y="Cum", title="Liquidity Projection Curve", template="plotly_dark", color_discrete_sequence=["#00e6b8"])
                fig_line.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_line, use_container_width=True)
                strategic_insight(
                    "This curve projects your cumulative capital inflow assuming execution of the AI communication strategy today.",
                    "Cap your own payable obligations to suppliers based on the terminal value of this projection curve."
                )

                # WhatsApp Hub
                st.markdown("---")
                st.subheader("📲 Multi-Channel Execution")
                
                customer_list = result_df["Name"].tolist()
                selected_customer = st.selectbox("Select Counterparty Profile:", customer_list)
                
                if selected_customer:
                    customer_info = result_df[result_df["Name"] == selected_customer].iloc[0]
                    st.markdown(f"""
                    <div style="background: #1f2937; padding: 15px; border-radius: 5px; border-left: 3px solid #6366f1;">
                        <span style="color: #6366f1; font-weight: bold; font-size: 12px;">GENERATED COMMUNICATION DRAFT</span><br><br>
                        <span style="color: #e2e8f0;">{customer_info['Message']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        target_phone = st.text_input("Target MSISDN (include country code, no +)", value="919876543210")
                        encoded_msg = urllib.parse.quote(customer_info['Message'])
                        wa_link = f"https://wa.me/{target_phone}?text={encoded_msg}"
                        st.link_button("Dispatch via WhatsApp", wa_link, use_container_width=True)
                        
                        if st.button("Log Transmission", use_container_width=True):
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cursor.execute("INSERT INTO transactions (username, customer, amount, due_date, industry, city, status) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                           (st.session_state.user, selected_customer, customer_info['Amount'], customer_info['Due Date'], customer_info['Industry'], customer_info['City'], "Pending"))
                            cursor.execute("INSERT INTO communications (username, customer, message, timestamp, status) VALUES (?, ?, ?, ?, ?)", 
                                           (st.session_state.user, selected_customer, customer_info['Message'], timestamp, "Dispatched"))
                            conn.commit()
                            st.success("Transmission logged securely.")
                            
                    with btn_col2:
                        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                        if st.button("Reconcile Account (Mark Paid)", type="primary", use_container_width=True):
                            cursor.execute("UPDATE transactions SET status='Recovered' WHERE customer=? AND username=?", (selected_customer, st.session_state.user))
                            conn.commit()
                            st.success(f"Ledger updated: Capital from {selected_customer} recovered.")

                # PDF DOWNLOAD
                st.markdown("---")
                st.subheader("📄 Daily Batch Reporting")
                pdf_bytes = generate_pdf_report(result_df)
                st.download_button(
                    label="Export Executive PDF Summary",
                    data=pdf_bytes,
                    file_name=f"KhataKhat_Batch_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    # ---------------- ADMIN PANEL ----------------
    if is_admin:
        with tabs[2]:
            st.header("🛡️ Database Operations")
            st.subheader("Transmission Logs")
            comm_data = pd.read_sql("SELECT * FROM communications ORDER BY id DESC", conn)
            if not comm_data.empty: st.dataframe(comm_data, use_container_width=True)
            else: st.info("Ledger empty.")
                
            st.markdown("---")
            st.subheader("Master Transaction Ledger")
            tx_data = pd.read_sql("SELECT * FROM transactions", conn)
            if not tx_data.empty: st.dataframe(tx_data, use_container_width=True)
            else: st.info("Ledger empty.")
