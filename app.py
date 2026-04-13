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
st.set_page_config(page_title="KhataKhat AI", layout="wide", initial_sidebar_state="collapsed")

# Premium Light/Corporate Theme CSS
st.markdown("""
<style>
/* Soft Premium Background */
.stApp {
    background-color: #f8fafc;
    color: #334155;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
/* Hide default Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Professional Headers */
h1, h2, h3 { 
    color: #0f766e !important; 
    font-weight: 700; 
    letter-spacing: -0.5px;
}

/* Light Glassmorphism Metric Cards */
div[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #0d9488;
    padding: 1.2rem;
    border-radius: 10px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    transition: transform 0.2s ease;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
}
div[data-testid="metric-container"] label {
    color: #64748b !important;
}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    color: #0f172a !important;
}

/* Clean Tabs */
button[data-baseweb="tab"] {
    color: #64748b !important;
    font-size: 16px !important;
    font-weight: 600;
}
button[aria-selected="true"] {
    color: #0d9488 !important;
    border-bottom: 2px solid #0d9488 !important;
}

/* Dataframe styling */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# STATE & LANGUAGE MANAGER
# -------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "English"

def t(en_text, hi_text):
    return en_text if st.session_state.lang == "English" else hi_text

# Custom Jaankari Box (Clean Light Theme)
def jaankari_box(obs_en, act_en, obs_hi, act_hi):
    obs = obs_en if st.session_state.lang == "English" else obs_hi
    act = act_en if st.session_state.lang == "English" else act_hi
    
    st.markdown(f"""
    <div style="background: #ffffff; border-left: 4px solid #0ea5e9; padding: 16px; border-radius: 6px; margin-top: 15px; margin-bottom: 25px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid #e0f2fe;">
        <h4 style="color: #0369a1; margin-top: 0px; margin-bottom: 10px; font-size: 15px; text-transform: uppercase; letter-spacing: 1px;">⚡ Jaankari (जानकारी)</h4>
        <p style="margin-bottom: 8px; font-size: 14px; color: #334155;"><strong style="color: #0f172a;">{t('Observation:', 'स्थिति:')}</strong> {obs}</p>
        <p style="margin-bottom: 0px; font-size: 14px; color: #334155;"><strong style="color: #0f172a;">{t('Action Plan:', 'सुझाव:')}</strong> {act}</p>
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
# DEMO MARKET DATA & LOGIC
# -------------------------------
market_df = pd.DataFrame({
    "Industry": ["FMCG","Textile","Electronics","FMCG","Pharma","Retail"],
    "City": ["Delhi","Surat","Mumbai","Delhi","Ahmedabad","Jaipur"],
    "Amount": [5000,12000,8000,6000,15000,4000],
    "Credit_Days": [15,30,10,12,20,8],
    "Days_Delayed": [3,20,2,8,5,9],
    "Status": ["Paid","Delayed","Paid","Delayed","Paid","Delayed"]
})

def get_city_risk(city):
    data = market_df[market_df["City"] == city]
    return data["Days_Delayed"].mean() if not data.empty else 5

def calculate_days_overdue(due_date):
    if pd.isnull(due_date):
        return 0
    today = datetime.today()
    return max((today - due_date).days, 0)

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
    if st.session_state.lang == "English":
        if category == "Low": return f"Hi {name}, a gentle reminder for your pending amount of Rs. {amount}. Pay here: {link}"
        elif category == "Medium": return f"Hello {name}, Rs. {amount} is currently pending. Most {industry} payments clear soon. Please complete yours: {link}"
        else: return f"URGENT: {name}, Rs. {amount} is overdue by {days} days. Immediate payment is required: {link}"
    else:
        if category == "Low": return f"नमस्ते {name}, आपके {amount} रुपये बकाया हैं। कृपया यहाँ भुगतान करें: {link}"
        elif category == "Medium": return f"नमस्कार {name}, आपके {amount} रुपये पेंडिंग हैं। कृपया अपना भुगतान जल्द पूरा करें: {link}"
        else: return f"जरूरी सूचना: {name}, आपके {amount} रुपये {days} दिन से ज्यादा पेंडिंग हैं। कृपया तुरंत भुगतान करें: {link}"

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
        return str(text).replace("₹", "Rs.").encode('latin-1', 'ignore').decode('latin-1')
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
# APP ROUTING & TOP NAVIGATION
# -------------------------------

if not st.session_state.logged_in:
    # --- LOGIN SCREEN ---
    col_logo, col_lang = st.columns([3, 1])
    with col_logo:
        st.markdown(f"<h1>💸 KhataKhat</h1>", unsafe_allow_html=True)
    with col_lang:
        st.session_state.lang = st.radio("Language / भाषा", ["English", "हिंदी"], horizontal=True, label_visibility="collapsed")
    
    st.markdown("---")
    
    col_login, col_empty = st.columns([1, 1])
    with col_login:
        st.markdown(f"### {t('Secure Portal', 'सुरक्षित पोर्टल')}")
        choice = st.radio(t("Authentication", "लॉगिन विकल्प"), [t("Login", "लॉगिन"), t("Register", "नया खाता")], horizontal=True)

        if choice in ["Login", "लॉगिन"]:
            user = st.text_input(t("Username", "यूज़रनेम"))
            pwd = st.text_input(t("Password", "पासवर्ड"), type="password")
            if st.button(t("Access Platform", "लॉगिन करें"), type="primary"):
                if login_user(user, pwd):
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error(t("Invalid credentials", "गलत जानकारी"))
        else:
            new_user = st.text_input(t("New Username", "नया यूज़रनेम"))
            new_pwd = st.text_input(t("New Password", "नया पासवर्ड"), type="password")
            if st.button(t("Create Account", "खाता बनाएं"), type="primary"):
                if create_user(new_user, new_pwd):
                    st.success(t("Account created successfully!", "खाता सफलतापूर्वक बन गया!"))
                else:
                    st.error(t("User already exists", "यूज़र पहले से मौजूद है"))

else:
    # --- MAIN DASHBOARD SCREEN ---
    
    # Top Navigation / Toolbar
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([4, 2, 2, 1])
    with nav_col1:
        st.markdown(f"<h2 style='margin-top: -10px;'>💸 KhataKhat <span style='color: #64748b; font-size: 20px; font-weight: 400;'>| {t('Enterprise Receivables', 'स्मार्ट व्यापार वसूली')}</span></h2>", unsafe_allow_html=True)
    with nav_col2:
        st.session_state.lang = st.radio("Language", ["English", "हिंदी"], horizontal=True, label_visibility="collapsed", key="lang_main")
    with nav_col3:
        st.markdown(f"<div style='text-align: right; padding-top: 5px; font-weight: bold;'>{t('User:', 'यूज़र:')} {st.session_state.user}</div>", unsafe_allow_html=True)
    with nav_col4:
        if st.button(t("Log Out", "लॉग आउट"), use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown("<hr style='margin-top: 0px; margin-bottom: 20px;'>", unsafe_allow_html=True)

    tab_names = [t("📊 Macro Insights", "📊 बाज़ार की जानकारी"), t("💸 Recovery Engine", "💸 वसूली इंजन")]
    is_admin = st.session_state.user == "admin"
    if is_admin: tab_names.append(t("🛡️ Admin Database", "🛡️ एडमिन पैनल"))

    tabs = st.tabs(tab_names)

    # ---------------- MARKET INSIGHTS ----------------
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        col1.metric(t("Total Market Credit", "बाज़ार में कुल उधार"), f"₹{market_df['Amount'].sum():,.0f}")
        col2.metric(t("Total Capital Stuck", "कुल फंसा हुआ पैसा"), f"₹{market_df[market_df['Status']=='Delayed']['Amount'].sum():,.0f}")
        col3.metric(t("System Average Delay", "औसत देरी (दिन)"), f"{market_df['Days_Delayed'].mean():.1f}")

        sub_tab1, sub_tab2, sub_tab3 = st.tabs([t("Industry Analytics", "व्यापार विश्लेषण"), t("Geographic Analytics", "शहर विश्लेषण"), t("Risk Stratification", "रिस्क विश्लेषण")])

        with sub_tab1:
            data = market_df.groupby("Industry")["Credit_Days"].mean().reset_index()
            fig = px.bar(data, x="Industry", y="Credit_Days", title=t("Credit Cycle by Industry", "उद्योग के अनुसार उधार के दिन"), color="Credit_Days", color_continuous_scale="Teal", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            jaankari_box(
                "FMCG counterparties exhibit high liquidity, clearing within 15 days, whereas Textile buyers are extending credit cycles beyond a month.",
                "Mandate a 50% upfront payment structure for all future Textile wholesale orders.",
                "FMCG वाले ग्राहक 15 दिनों में पैसे चुका रहे हैं, जबकि टेक्सटाइल (कपड़ा) वाले एक महीने से ज्यादा का समय ले रहे हैं।",
                "कैश फ्लो बनाए रखने के लिए, टेक्सटाइल के नए ऑर्डर पर 50% एडवांस लेना शुरू करें।"
            )

        with sub_tab2:
            data = market_df.groupby("City")["Days_Delayed"].mean().reset_index()
            fig = px.bar(data, x="City", y="Days_Delayed", title=t("Capital Delay by Region", "शहर के अनुसार देरी"), color="Days_Delayed", color_continuous_scale="Reds", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            jaankari_box(
                "Counterparties in Surat are severely stretching working capital cycles (+20 days delay). Delhi accounts remain highly liquid.",
                "Reroute current inventory allocation to Delhi-based distributors.",
                "सूरत के ग्राहक पैसा बहुत ज्यादा रोक रहे हैं (20+ दिन की देरी)। दिल्ली के ग्राहक तेज़ी से पैसे दे रहे हैं।",
                "सूरत में नया माल भेजना रोकें और दिल्ली के ग्राहकों पर ज़्यादा फोकस करें।"
            )

        with sub_tab3:
            market_df["Risk"] = market_df["Days_Delayed"].apply(categorize)
            fig = px.pie(market_df, names="Risk", title=t("Portfolio Risk Distribution", "रिस्क का बंटवारा"), hole=0.4, color="Risk", color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            jaankari_box(
                "A significant tranche of receivables is currently flagged as 'High Risk', indicating high probability of default.",
                "Suspend all credit extensions to High Risk profiles immediately.",
                "आपका बहुत सारा पैसा 'हाई रिस्क' (डूबने के खतरे) वाली जगह फंसा हुआ है।",
                "जब तक ये ग्राहक अपना पुराना बिल आधा साफ नहीं कर देते, इन्हें 1 रुपये का भी उधार न दें।"
            )

    # ---------------- RECOVERY ENGINE ----------------
    with tabs[1]:
        st.markdown(f"<p style='color: #64748b;'>{t('Please upload your current receivables ledger. File must be named', 'कृपया अपना डेटा अपलोड करें। फ़ाइल का नाम होना चाहिए')} <b>udhaar_data.csv</b>.</p>", unsafe_allow_html=True)
        file = st.file_uploader("", type=["csv"])

        if file:
            df = pd.read_csv(file)
            required_cols = ["Name", "Amount", "Paid Amount", "Due Date", "Industry", "City"]
            if not all(col in df.columns for col in required_cols):
                st.error(t(f"Schema mismatch. Required headers: {', '.join(required_cols)}", f"फ़ाइल गलत है। ज़रूरी कॉलम: {', '.join(required_cols)}"))
                st.stop()
            
            # Robust Date Parsing Fix
            df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce')

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
                
                # Convert date back to string for display/DB storage
                display_date = row['Due Date'].strftime('%Y-%m-%d') if pd.notnull(row['Due Date']) else "N/A"
                msg = generate_ai_message(row['Name'], pending_amount, days, category, row['Industry'])

                results.append({
                    "Name": row['Name'], "Amount": pending_amount, "Due Date": display_date,
                    "Industry": row['Industry'], "City": row['City'], "Days": days,
                    "Risk Score": round(risk, 2), "Category": category, "Credit Score": credit,
                    "Recovery %": round(prob * 100, 1), "Expected": round(expected, 0), "Message": msg
                })

            result_df = pd.DataFrame(results)

            if result_df.empty:
                st.success(t("Ledger clear. Zero outstanding balances detected.", "खाता साफ़ है। कोई पैसा बकाया नहीं है!"))
            else:
                st.markdown("---")
                st.subheader(t("📋 Live Ledger Analysis", "📋 लाइव डेटा रिपोर्ट"))
                st.dataframe(result_df.drop(columns=["Message"]), use_container_width=True)
                
                if st.button(t("💾 Synchronize to Database", "💾 डेटाबेस में सेव करें")):
                    for _, row in result_df.iterrows():
                        cursor.execute("""
                        INSERT INTO transactions (username, customer, amount, due_date, industry, city, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (st.session_state.user, row['Name'], row['Amount'], row['Due Date'], row['Industry'], row['City'], "Pending"))
                    conn.commit()
                    st.success(t("Ledger synchronized successfully.", "डेटा सुरक्षित कर लिया गया है।"))

                # KPIs
                st.markdown("---")
                st.subheader(t("🎯 Optimization Targets", "🎯 रिकवरी टारगेट"))
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("Gross Receivables", "कुल बकाया"), f"₹{result_df['Amount'].sum():,.0f}")
                c2.metric(t("Projected Inflow", "आने की उम्मीद"), f"₹{result_df['Expected'].sum():,.0f}")
                c3.metric(t("Critical Accounts", "खतरे वाले खाते"), len(result_df[result_df["Category"] == "High"]))
                c4.metric(t("Recovery Probability", "रिकवरी संभावना"), f"{result_df['Recovery %'].mean():.1f}%")

                # Charts
                st.markdown("<br>", unsafe_allow_html=True)
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig1 = px.bar(result_df, x="Name", y="Risk Score", title=t("Default Probability Index", "खतरे का स्कोर (ग्राहक अनुसार)"), color="Risk Score", color_continuous_scale="Turbo", template="plotly_white")
                    st.plotly_chart(fig1, use_container_width=True)
                    jaankari_box(
                        "Spikes in the DPI isolate accounts most likely to default.",
                        "Bypass automated channels for peak-risk accounts. Initiate direct phone contact.",
                        "सबसे ऊंचे बार वाले ग्राहकों के पैसे लेकर भागने की संभावना सबसे ज़्यादा है।",
                        "व्हाट्सएप का इंतज़ार न करें, अभी अपना फोन उठाएं और इन ऊंचे बार वाले ग्राहकों को सीधे कॉल करें।"
                    )
                
                with col_chart2:
                    fig2 = px.pie(result_df, names="Category", title=t("Exposure Segmentation", "अकाउंट रिस्क केटेगरी"), hole=0.4, color="Category", color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}, template="plotly_white")
                    st.plotly_chart(fig2, use_container_width=True)
                    jaankari_box(
                        "Visualizes total capital tied up across safety tiers.",
                        "Deploy automated UPI links to 'Low' tier accounts. Reserve manual collections bandwidth.",
                        "यह चार्ट आपके ग्राहकों को सुरक्षित (Low) और खतरे (High) में बांटता है।",
                        "सुरक्षित वालों के लिए ऑटोमैटिक व्हाट्सएप का इस्तेमाल करें। अपना समय हाई रिस्क वालों के लिए बचाएं।"
                    )

                # Forecast
                result_df = result_df.sort_values(by="Expected", ascending=False)
                result_df["Index"] = range(1, len(result_df) + 1)
                result_df["Cum"] = result_df["Expected"].cumsum()
                fig_line = px.area(result_df, x="Index", y="Cum", title=t("Liquidity Projection Curve", "इस हफ़्ते कैश फ्लो का अनुमान"), template="plotly_white", color_discrete_sequence=["#0ea5e9"])
                st.plotly_chart(fig_line, use_container_width=True)

                # WhatsApp Hub
                st.markdown("---")
                st.subheader(t("📲 Multi-Channel Execution", "📲 व्हाट्सएप कम्युनिकेशन हब"))
                
                customer_list = result_df["Name"].tolist()
                selected_customer = st.selectbox(t("Select Counterparty Profile:", "ग्राहक चुनें:"), customer_list)
                
                if selected_customer:
                    customer_info = result_df[result_df["Name"] == selected_customer].iloc[0]
                    st.markdown(f"""
                    <div style="background: #f1f5f9; padding: 15px; border-radius: 5px; border-left: 3px solid #6366f1;">
                        <span style="color: #4f46e5; font-weight: bold; font-size: 12px;">{t('GENERATED COMMUNICATION DRAFT', 'तैयार किया गया मैसेज')}</span><br><br>
                        <span style="color: #334155;">{customer_info['Message']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        target_phone = st.text_input(t("Target MSISDN (include country code, no +)", "ग्राहक का फोन नंबर (91 के साथ)"), value="919876543210")
                        clean_phone = target_phone.replace("+", "").replace(" ", "").strip()
                        encoded_msg = urllib.parse.quote(customer_info['Message'])
                        wa_link = f"https://wa.me/{clean_phone}?text={encoded_msg}"
                        st.link_button(t("Dispatch via WhatsApp", "व्हाट्सएप पर भेजें 💬"), wa_link, use_container_width=True)
                        
                        if st.button(t("Log Transmission", "रिकॉर्ड में दर्ज करें"), use_container_width=True):
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cursor.execute("INSERT INTO transactions (username, customer, amount, due_date, industry, city, status) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                           (st.session_state.user, selected_customer, customer_info['Amount'], customer_info['Due Date'], customer_info['Industry'], customer_info['City'], "Pending"))
                            cursor.execute("INSERT INTO communications (username, customer, message, timestamp, status) VALUES (?, ?, ?, ?, ?)", 
                                           (st.session_state.user, selected_customer, customer_info['Message'], timestamp, "Dispatched"))
                            conn.commit()
                            st.success(t("Transmission logged securely.", "रिकॉर्ड सफलतापूर्वक सेव हो गया! ✅"))
                            
                    with btn_col2:
                        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                        if st.button(t("Reconcile Account (Mark Paid)", "पैसा मिल गया (मार्क करें) 💰"), type="primary", use_container_width=True):
                            cursor.execute("UPDATE transactions SET status='Recovered' WHERE customer=? AND username=? AND amount=? AND status='Pending'", (selected_customer, st.session_state.user, customer_info['Amount']))
                            conn.commit()
                            st.success(f"{t('Ledger updated: Capital from', 'अकाउंट अपडेट:')} {selected_customer} {t('recovered.', 'से पैसा मिल गया! ✅')}")

                # Tracking Table
                st.markdown("---")
                st.subheader(t("📈 Active Recovery History", "📈 आपका रिकवरी इतिहास"))
                history_df = pd.read_sql("SELECT customer, amount, due_date, status FROM transactions WHERE username=?", conn, params=(st.session_state.user,))
                if not history_df.empty:
                    st.dataframe(history_df, use_container_width=True)
                else:
                    st.info(t("No recovery records found. Sync data or log a transmission above.", "अभी तक कोई रिकवरी रिकॉर्ड नहीं है।"))

                # PDF DOWNLOAD
                st.markdown("---")
                st.subheader(t("📄 Daily Batch Reporting", "📄 डेली रिपोर्ट"))
                pdf_bytes = generate_pdf_report(result_df)
                st.download_button(
                    label=t("Export Executive PDF Summary", "PDF रिपोर्ट डाउनलोड करें"),
                    data=pdf_bytes,
                    file_name=f"KhataKhat_Batch_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    # ---------------- ADMIN PANEL ----------------
    if is_admin:
        with tabs[2]:
            st.header(t("🛡️ Database Operations", "🛡️ एडमिन पैनल"))
            st.subheader(t("Transmission Logs", "व्हाट्सएप लॉग्स"))
            comm_data = pd.read_sql("SELECT * FROM communications ORDER BY id DESC", conn)
            if not comm_data.empty: st.dataframe(comm_data, use_container_width=True)
            else: st.info(t("Ledger empty.", "कोई रिकॉर्ड नहीं है।"))
                
            st.markdown("---")
            st.subheader(t("Master Transaction Ledger", "मास्टर डेटाबेस"))
            tx_data = pd.read_sql("SELECT * FROM transactions", conn)
            if not tx_data.empty: st.dataframe(tx_data, use_container_width=True)
            else: st.info(t("Ledger empty.", "डेटाबेस खाली है।"))

# -------------------------------
# COPYRIGHT FOOTER
# -------------------------------
st.markdown("""
    <div style='text-align: center; margin-top: 50px; padding: 20px; color: #94a3b8; font-size: 14px;'>
        Copyright by Ebin Davis
    </div>
""", unsafe_allow_html=True)
