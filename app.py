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
st.set_page_config(page_title="KhataKhat Premium", layout="wide", initial_sidebar_state="expanded")

# Ultra-Premium Custom CSS
st.markdown("""
<style>
/* Deep Dark Premium Background */
.stApp {
    background-color: #0b0f19;
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
}
/* Neon Accents for Headers */
h1, h2, h3 { 
    color: #00e6a8 !important; 
    font-weight: 800; 
    letter-spacing: -0.5px;
}
/* Sleek Metric Cards */
div[data-testid="metric-container"] {
    background: #151e2d;
    border: 1px solid #1f2937;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    transition: transform 0.2s ease-in-out;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    border-color: #00e6a8;
}
/* Upgraded AI Action Plan Boxes */
.ai-action-plan {
    background: linear-gradient(90deg, #132a2c 0%, #0b0f19 100%);
    border-left: 4px solid #00e6a8;
    padding: 16px 20px;
    border-radius: 6px;
    margin-top: 10px;
    margin-bottom: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
}
.ai-action-title {
    color: #00e6a8;
    font-weight: 700;
    font-size: 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.ai-action-text {
    color: #94a3b8;
    font-size: 14px;
    line-height: 1.6;
}
.ai-action-highlight {
    color: #e2e8f0;
    font-weight: 600;
}
/* Clean Tabs */
button[data-baseweb="tab"] {
    color: #64748b !important;
    font-weight: 600;
    font-size: 16px;
}
button[aria-selected="true"] {
    color: #00e6a8 !important;
    border-bottom: 2px solid #00e6a8 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>💸 KhataKhat <span style='color: #ffffff; font-weight: 300;'>| Enterprise Engine</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8; font-size: 18px; margin-bottom: 30px;'>Intelligent Credit Recovery for the Modern Vyapari</p>", unsafe_allow_html=True)

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

if not cursor.execute("SELECT * FROM users WHERE username='admin'").fetchone():
    create_user("admin", "admin123")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------
def ai_action_card(title, result, action):
    html = f"""
    <div class="ai-action-plan">
        <div class="ai-action-title">⚡ {title}</div>
        <div class="ai-action-text">
            <span class="ai-action-highlight">Analysis:</span> {result}<br>
            <span class="ai-action-highlight" style="color: #ff4757; margin-top: 5px; display: inline-block;">Action Required:</span> {action}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def calculate_days_overdue(due_date):
    try:
        today = datetime.today()
        due = pd.to_datetime(due_date)
        return max((today - due).days, 0)
    except Exception:
        return 0

def categorize(days):
    if days < 15: return "Low"
    elif days < 30: return "Medium"
    else: return "High"

def calculate_risk(days, amount):
    return (days * 0.4) + (amount * 0.001)

def predict_recovery_probability(days, amount, category):
    base = 0.9 - (days * 0.01)
    if category == "High": base -= 0.2
    return max(min(base, 0.95), 0.1)

def generate_ai_message(name, amount, days, category, industry):
    amount_str = f"Rs. {amount:,.0f}"
    if category == "Low":
        return f"Hi {name}, this is a polite reminder regarding your pending balance of {amount_str}. Kindly clear this at your earliest convenience."
    elif category == "Medium":
        return f"Hello {name}, your payment of {amount_str} is currently overdue. Please prioritize clearing this invoice today to maintain your credit standing."
    else:
        return f"URGENT: {name}, your balance of {amount_str} is severely overdue ({days} days). Immediate payment is required to prevent an account hold."

def generate_pdf_report(df):
    pdf = FPDF()
    pdf.add_page()
    def clean_txt(text):
        return str(text).replace("₹", "Rs.").replace("⚠️", "[URGENT]").encode('latin-1', 'ignore').decode('latin-1')
    
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(200, 10, txt="KhataKhat Enterprise Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    total_due = df['Amount'].sum()
    expected_cash = df['Expected'].sum()
    pdf.cell(200, 10, txt=f"Total Pending: Rs. {total_due:,.0f} | AI Expected Recovery: Rs. {expected_cash:,.0f}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=10)
    for _, row in df.iterrows():
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, txt=clean_txt(f"{row['Name']} ({row['City']}) - Risk: {row['Category']}"), ln=True)
        pdf.set_font("Arial", size=9)
        pdf.cell(0, 5, txt=clean_txt(f"Due: Rs. {row['Amount']} | Days Overdue: {row['Days']}"), ln=True)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5, txt=clean_txt(f"Strategy: {row['Message']}"))
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)
        
    return pdf.output(dest="S").encode("latin-1")

# -------------------------------
# LOGIN / REGISTER
# -------------------------------
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.subheader("Secure Access")
        choice = st.radio("Portal", ["Login", "Register"], horizontal=True)
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        
        if choice == "Login" and st.button("Authenticate", use_container_width=True):
            if login_user(user, pwd):
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else: st.error("Access Denied.")
            
        elif choice == "Register" and st.button("Create Account", use_container_width=True):
            if create_user(user, pwd): st.success("Account created!")
            else: st.error("Username taken.")

# -------------------------------
# MAIN APP
# -------------------------------
else:
    with st.sidebar:
        st.markdown("### 👤 User Profile")
        st.markdown(f"**ID:** `{st.session_state.user.upper()}`")
        if st.button("End Session"):
            st.session_state.logged_in = False
            st.rerun()

    tabs = st.tabs(["⚡ AI Recovery Engine", "📈 Operations Dashboard"])

    # ---------------- RECOVERY ENGINE (Made Default for Quick Demo) ----------------
    with tabs[0]:
        st.markdown("### Upload Target Data (`udhaar_data.csv`)")
        file = st.file_uploader("", type=["csv"])

        if file:
            df = pd.read_csv(file)
            required_cols = ["Name", "Amount", "Paid Amount", "Due Date", "Industry", "City"]
            if not all(col in df.columns for col in required_cols):
                st.error(f"Missing columns. Need: {', '.join(required_cols)}")
                st.stop()

            results = []
            for _, row in df.iterrows():
                pending_amount = row['Amount'] - row['Paid Amount']
                if pending_amount <= 0: continue

                days = calculate_days_overdue(row['Due Date'])
                category = categorize(days)
                risk = calculate_risk(days, pending_amount)
                prob = predict_recovery_probability(days, pending_amount, category)
                expected = pending_amount * prob
                msg = generate_ai_message(row['Name'], pending_amount, days, category, row['Industry'])

                results.append({
                    "Name": row['Name'], "Amount": pending_amount, "Due Date": row['Due Date'],
                    "Industry": row['Industry'], "City": row['City'], "Days": days,
                    "Risk Score": round(risk, 2), "Category": category,
                    "Recovery Prob": round(prob * 100, 1), "Expected": round(expected, 0), "Message": msg
                })

            result_df = pd.DataFrame(results)

            if result_df.empty:
                st.success("All balances cleared. No active recoveries.")
            else:
                # KPIs
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Capital Stuck", f"₹{result_df['Amount'].sum():,.0f}")
                c2.metric("AI Projected Cashflow", f"₹{result_df['Expected'].sum():,.0f}")
                c3.metric("Critical Accounts", len(result_df[result_df["Category"] == "High"]))
                c4.metric("Avg Success Probability", f"{result_df['Recovery Prob'].mean():.1f}%")

                st.markdown("---")
                
                # Interactive Charts
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig1 = px.bar(result_df, x="Name", y="Risk Score", color="Category", 
                                  color_discrete_map={"High":"#ff4757", "Medium":"#ffa502", "Low":"#2ed573"},
                                  template="plotly_dark", title="Client Risk Matrix")
                    fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig1, use_container_width=True)
                    ai_action_card(
                        "Risk Containment",
                        "Visualizes default probability based on delay and principal amount.",
                        "Halt all secondary inventory dispatches to clients in the RED zone immediately."
                    )
                
                with col_chart2:
                    fig2 = px.scatter(result_df, x="Days", y="Amount", size="Risk Score", color="Category",
                                      hover_name="Name", template="plotly_dark", title="Capital Exposure Map")
                    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig2, use_container_width=True)
                    ai_action_card(
                        "Exposure Routing",
                        "Identifies high-value targets deep in the delay timeline.",
                        "Trigger automated WhatsApp sequences for GREEN/YELLOW dots. Escalate RED dots to personal phone calls."
                    )

                st.markdown("---")
                st.subheader("📲 1-Click Execution Hub")
                
                selected_customer = st.selectbox("Select Target Account:", result_df["Name"].tolist())
                
                if selected_customer:
                    customer_info = result_df[result_df["Name"] == selected_customer].iloc[0]
                    st.markdown(f"**Generated Payload:**\n> *{customer_info['Message']}*")
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        target_phone = st.text_input("WhatsApp Number (Include 91)", value="919876543210")
                        encoded_msg = urllib.parse.quote(customer_info['Message'])
                        wa_link = f"https://wa.me/{target_phone}?text={encoded_msg}"
                        st.link_button("Deploy via WhatsApp 💬", wa_link, use_container_width=True)
                            
                    with btn_col2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Mark Invoice Cleared 💰", use_container_width=True):
                            cursor.execute("INSERT INTO transactions (username, customer, amount, status) VALUES (?, ?, ?, ?)", 
                                           (st.session_state.user, selected_customer, customer_info['Amount'], "Recovered"))
                            conn.commit()
                            st.success(f"Ledger updated for {selected_customer}.")

                # PDF Export
                st.markdown("---")
                pdf_bytes = generate_pdf_report(result_df)
                st.download_button(
                    label="📄 Export Enterprise Recovery Report (PDF)",
                    data=pdf_bytes,
                    file_name=f"KhataKhat_Ops_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    # ---------------- OPERATIONS DASHBOARD ----------------
    with tabs[1]:
        st.header("📈 Ledger Operations")
        history = pd.read_sql("SELECT * FROM transactions WHERE username=?", conn, params=(st.session_state.user,))

        if not history.empty:
            recovered = history[history["status"] == "Recovered"]
            st.metric("Total Capital Recovered To Date", f"₹{recovered['amount'].sum():,.0f}")
            st.dataframe(history, use_container_width=True)
        else:
            st.info("System ledger is clean. Process recoveries in the main engine to populate logs.")
