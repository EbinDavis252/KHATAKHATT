import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import urllib.parse
 
# -------------------------------
# CONFIG + ENTERPRISE UI
# -------------------------------
st.set_page_config(page_title="KhataKhat", layout="wide", initial_sidebar_state="collapsed")
 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Syne:wght@700;800&display=swap');
 
/* Deep textured background */
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #162032 100%);
    background-attachment: fixed;
    color: #f8fafc;
    font-family: 'DM Sans', sans-serif;
}
 
/* Noise texture overlay */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
    opacity: 0.4;
}
 
/* Hide default Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
 
/* Professional Headers using Syne */
h1, h2, h3 {
    color: #38bdf8 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 800;
    letter-spacing: -0.5px;
}
 
/* Metric Cards with hover lift */
div[data-testid="metric-container"] {
    background: linear-gradient(145deg, #1e3a5f 0%, #334155 100%);
    border: 1px solid #475569;
    border-left: 4px solid #38bdf8;
    padding: 1.5rem;
    border-radius: 10px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    transition: all 0.25s ease;
    cursor: default;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 30px rgba(56, 189, 248, 0.18);
    border-left-color: #7dd3fc;
}
div[data-testid="metric-container"] label {
    color: #cbd5e1 !important;
    font-weight: 500 !important;
    font-size: 1.0rem !important;
    font-family: 'DM Sans', sans-serif !important;
}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    color: #f8fafc !important;
    font-weight: 700 !important;
    font-family: 'Syne', sans-serif !important;
}
 
/* Clean Tabs */
button[data-baseweb="tab"] {
    color: #94a3b8 !important;
    font-size: 15px !important;
    font-weight: 600;
    font-family: 'DM Sans', sans-serif !important;
    transition: color 0.2s;
}
button[aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom: 3px solid #38bdf8 !important;
}
 
/* Dataframe styling */
.stDataFrame {
    border-radius: 10px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
    border: 1px solid #334155;
}
 
/* Buttons */
.stButton > button {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600;
    border-radius: 8px;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(56, 189, 248, 0.25);
}
 
/* Input fields */
.stTextInput > div > div > input,
.stSelectbox > div > div {
    background: #1e293b !important;
    border: 1px solid #475569 !important;
    color: #f8fafc !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
}
 
/* File uploader */
.stFileUploader {
    border: 2px dashed #475569;
    border-radius: 12px;
    padding: 10px;
    transition: border-color 0.2s;
}
.stFileUploader:hover {
    border-color: #38bdf8;
}
 
/* Alert / info boxes */
.stAlert {
    border-radius: 8px;
    font-family: 'DM Sans', sans-serif;
}
 
/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f172a !important;
}
 
/* Demo badge */
.demo-badge {
    display: inline-block;
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.4);
    color: #fbbf24;
    font-size: 12px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.5px;
    vertical-align: middle;
}
 
/* Status badge */
.status-pending { color: #f59e0b; font-weight: 600; }
.status-recovered { color: #10b981; font-weight: 600; }
</style>
""", unsafe_allow_html=True)
 
# -------------------------------
# CORE FIX: NATIVE SQL SANITIZER
# -------------------------------
def safe_read_sql(query, conn, params=()):
    cursor = conn.cursor()
    cursor.execute(query, params)
    if cursor.description is None:
        return pd.DataFrame()
    cols = [description[0] for description in cursor.description]
    clean_rows = []
    for row in cursor.fetchall():
        clean_row = []
        for val in row:
            if isinstance(val, bytes):
                clean_row.append(val.decode('utf-8', 'ignore'))
            elif isinstance(val, str):
                clean_row.append(val.encode('utf-8', 'ignore').decode('utf-8'))
            else:
                clean_row.append(val)
        clean_rows.append(clean_row)
    return pd.DataFrame(clean_rows, columns=cols)
 
# -------------------------------
# PLOTLY LAYOUT HELPER
# -------------------------------
def apply_chart_layout(fig, title=""):
    fig.update_layout(
        font=dict(family="'DM Sans', sans-serif", color="#cbd5e1", size=13),
        title_font=dict(family="'Syne', sans-serif", size=16, color="#f8fafc"),
        title_text=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        xaxis=dict(gridcolor="#1e293b", zerolinecolor="#334155"),
        yaxis=dict(gridcolor="#1e293b", zerolinecolor="#334155"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1")),
        margin=dict(t=50, b=30, l=20, r=20),
    )
    return fig
 
# -------------------------------
# STATE & LANGUAGE MANAGER
# -------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "English"
 
def t(en_text, hi_text):
    return en_text if st.session_state.lang == "English" else hi_text
 
def jaankari_box(obs_en, act_en, obs_hi, act_hi):
    obs = obs_en if st.session_state.lang == "English" else obs_hi
    act = act_en if st.session_state.lang == "English" else act_hi
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0f172a, #1a2744); border-left: 4px solid #0284c7; padding: 18px; border-radius: 10px; margin-top: 15px; margin-bottom: 25px; border: 1px solid #1e3a5f; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.1);">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
            <span style="font-size: 16px;">💡</span>
            <h4 style="color: #38bdf8; margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; font-family: 'Syne', sans-serif;">Jaankari</h4>
        </div>
        <p style="margin-bottom: 8px; font-size: 14px; color: #cbd5e1;"><strong style="color: #f8fafc;">{t('Observation:', 'स्थिति:')}</strong> {obs}</p>
        <p style="margin-bottom: 0px; font-size: 14px; color: #cbd5e1;"><strong style="color: #f8fafc;">{t('Action Plan:', 'सुझाव:')}</strong> {act}</p>
    </div>
    """, unsafe_allow_html=True)
 
# -------------------------------
# DATABASE
# -------------------------------
conn = sqlite3.connect("khatakhat.db", check_same_thread=False)
cursor = conn.cursor()
 
cursor.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, upi_id TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, customer TEXT, amount REAL, due_date TEXT, industry TEXT, city TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS communications (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, customer TEXT, message TEXT, timestamp TEXT, status TEXT)")
conn.commit()
 
# Add upi_id column if it doesn't exist (migration safety)
try:
    cursor.execute("ALTER TABLE users ADD COLUMN upi_id TEXT")
    conn.commit()
except:
    pass
 
# -------------------------------
# AUTH FUNCTIONS
# -------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
 
def create_user(username, password):
    try:
        cursor.execute("INSERT INTO users VALUES (?, ?, ?)", (username, hash_password(password), ""))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
 
def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_password(password)))
    return cursor.fetchone()
 
def get_upi_id(username):
    result = cursor.execute("SELECT upi_id FROM users WHERE username=?", (username,)).fetchone()
    return result[0] if result and result[0] else ""
 
def save_upi_id(username, upi_id):
    cursor.execute("UPDATE users SET upi_id=? WHERE username=?", (upi_id, username))
    conn.commit()
 
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
 
def generate_ai_message(name, amount, days, category, industry, upi_id):
    # Use actual UPI ID if set, else show placeholder label
    upi_target = upi_id if upi_id else "yourname@upi"
    link = f"upi://pay?pa={urllib.parse.quote(upi_target)}&am={amount}&cu=INR&tn=Invoice+Payment"
    if st.session_state.lang == "English":
        if category == "Low":
            return f"Hi {name}, a gentle reminder for your pending amount of ₹{amount:,.0f}. Please complete payment here: {link}"
        elif category == "Medium":
            return f"Hello {name}, ₹{amount:,.0f} is currently pending. Most {industry} payments clear within the week. Please complete yours: {link}"
        else:
            return f"URGENT: {name}, ₹{amount:,.0f} is overdue by {days} days. Immediate payment is required to avoid further action: {link}"
    else:
        if category == "Low":
            return f"नमस्ते {name}, आपके ₹{amount:,.0f} बकाया हैं। कृपया यहाँ भुगतान करें: {link}"
        elif category == "Medium":
            return f"नमस्कार {name}, आपके ₹{amount:,.0f} पेंडिंग हैं। कृपया अपना भुगतान जल्द पूरा करें: {link}"
        else:
            return f"जरूरी सूचना: {name}, आपके ₹{amount:,.0f}, {days} दिन से ज्यादा पेंडिंग हैं। कृपया तुरंत भुगतान करें: {link}"
 
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
    pdf.cell(200, 10, txt="KhataKhat - Recovery Report", ln=True, align='C')
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
    return bytes(pdf.output())
 
# -------------------------------
# APP ROUTING
# -------------------------------
 
if not st.session_state.logged_in:
    # --- LOGIN SCREEN ---
    col_logo, col_lang = st.columns([3, 1])
    with col_logo:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 4px;">
            <div style="background: linear-gradient(135deg, #0284c7, #38bdf8); border-radius: 10px; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 4px 14px rgba(56,189,248,0.3);">₹</div>
            <h1 style="margin: 0; font-family: 'Syne', sans-serif; font-size: 32px; color: #f8fafc !important;">KhataKhat</h1>
        </div>
        """, unsafe_allow_html=True)
    with col_lang:
        st.session_state.lang = st.radio("Language / भाषा", ["English", "हिंदी"], horizontal=True, label_visibility="collapsed")
 
    # Hero tagline
    st.markdown(f"""
    <p style="color: #94a3b8; font-size: 16px; margin-top: 2px; margin-bottom: 0px; font-family: 'DM Sans', sans-serif;">
        {t("India's smart receivables recovery platform for MSMEs.", "भारत के MSME व्यापारियों के लिए स्मार्ट वसूली प्लेटफॉर्म।")}<br>
        <span style="color: #64748b; font-size: 14px;">{t("Track dues. Predict defaults. Recover faster.", "बकाया ट्रैक करें। डिफॉल्ट पहचानें। जल्दी पैसा वसूलें।")}</span>
    </p>
    """, unsafe_allow_html=True)
 
    st.markdown("<hr style='border-color: #1e293b; margin: 20px 0;'>", unsafe_allow_html=True)
 
    col_login, col_empty = st.columns([1, 1])
    with col_login:
        st.markdown(f"<h3 style='font-family: Syne, sans-serif;'>{t('Secure Portal', 'सुरक्षित पोर्टल')}</h3>", unsafe_allow_html=True)
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
                    st.error(t("Invalid credentials. Please check your username and password.", "गलत जानकारी। कृपया यूज़रनेम और पासवर्ड दोबारा जांचें।"))
        else:
            new_user = st.text_input(t("New Username", "नया यूज़रनेम"))
            new_pwd = st.text_input(t("New Password", "नया पासवर्ड"), type="password")
            if st.button(t("Create Account", "खाता बनाएं"), type="primary"):
                if len(new_user.strip()) < 3:
                    st.error(t("Username must be at least 3 characters.", "यूज़रनेम कम से कम 3 अक्षर का होना चाहिए।"))
                elif len(new_pwd) < 6:
                    st.error(t("Password must be at least 6 characters.", "पासवर्ड कम से कम 6 अक्षर का होना चाहिए।"))
                elif create_user(new_user.strip(), new_pwd):
                    st.success(t("Account created successfully. You can now log in.", "खाता सफलतापूर्वक बन गया। अब लॉगिन करें।"))
                else:
                    st.error(t("This username already exists. Please choose another.", "यह यूज़रनेम पहले से मौजूद है। कोई दूसरा नाम चुनें।"))
 
    with col_empty:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1e3a5f22, #0f172a); border: 1px solid #1e3a5f; border-radius: 14px; padding: 28px; margin-top: 50px;">
            <div style="font-size: 13px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; font-weight: 600;">Platform Features</div>
            <div style="display: flex; flex-direction: column; gap: 12px;">
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                    <span style="font-size: 18px;">📊</span>
                    <div><div style="color: #f8fafc; font-weight: 600; font-size: 14px;">Market Pulse Analytics</div><div style="color: #64748b; font-size: 13px;">Industry & city-level credit benchmarks</div></div>
                </div>
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                    <span style="font-size: 18px;">🤖</span>
                    <div><div style="color: #f8fafc; font-weight: 600; font-size: 14px;">AI Risk Scoring</div><div style="color: #64748b; font-size: 13px;">Predict defaults before they happen</div></div>
                </div>
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                    <span style="font-size: 18px;">💬</span>
                    <div><div style="color: #f8fafc; font-weight: 600; font-size: 14px;">WhatsApp Recovery Hub</div><div style="color: #64748b; font-size: 13px;">Auto-generated UPI payment messages</div></div>
                </div>
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                    <span style="font-size: 18px;">📄</span>
                    <div><div style="color: #f8fafc; font-weight: 600; font-size: 14px;">PDF Reports</div><div style="color: #64748b; font-size: 13px;">Daily batch recovery summaries</div></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
 
else:
    # --- MAIN DASHBOARD SCREEN ---
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([4, 2, 2, 1])
    with nav_col1:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-top: -8px;">
            <div style="background: linear-gradient(135deg, #0284c7, #38bdf8); border-radius: 8px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;">₹</div>
            <h2 style="margin: 0; font-family: 'Syne', sans-serif;">KhataKhat <span style="color: #475569; font-size: 16px; font-weight: 400;">| {t('Smart Recovery Desk', 'स्मार्ट वसूली डेस्क')}</span></h2>
        </div>
        """, unsafe_allow_html=True)
    with nav_col2:
        st.session_state.lang = st.radio("Language", ["English", "हिंदी"], horizontal=True, label_visibility="collapsed", key="lang_main")
    with nav_col3:
        st.markdown(f"<div style='text-align: right; padding-top: 5px; font-size: 15px; font-weight: 500; color: #94a3b8;'>{t('User:', 'यूज़र:')} <span style='color: #f8fafc;'>{st.session_state.user}</span></div>", unsafe_allow_html=True)
    with nav_col4:
        if st.button(t("Log Out", "लॉग आउट"), use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
 
    st.markdown("<hr style='margin-top: 8px; margin-bottom: 20px; border-color: #1e293b;'>", unsafe_allow_html=True)
 
    # --- UPI SETTINGS BANNER (dismissible) ---
    upi_id = get_upi_id(st.session_state.user)
    if not upi_id:
        with st.expander(f"⚙️ {t('Set your UPI ID to enable payment links in recovery messages', 'भुगतान लिंक चालू करने के लिए अपना UPI ID सेट करें')}", expanded=True):
            col_upi, col_save = st.columns([3, 1])
            with col_upi:
                new_upi = st.text_input(t("Your UPI ID (e.g. yourname@okaxis)", "आपका UPI ID (जैसे yourname@okaxis)"), placeholder="yourname@okaxis", label_visibility="collapsed")
            with col_save:
                if st.button(t("Save UPI ID", "UPI सेव करें"), type="primary"):
                    if "@" in new_upi and len(new_upi) > 5:
                        save_upi_id(st.session_state.user, new_upi)
                        st.success(t("UPI ID saved!", "UPI ID सेव हो गई!"))
                        st.rerun()
                    else:
                        st.error(t("Please enter a valid UPI ID.", "सही UPI ID डालें।"))
    else:
        st.markdown(f"""
        <div style="background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.25); border-radius: 8px; padding: 10px 16px; margin-bottom: 16px; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 15px;">✅</span>
            <span style="color: #6ee7b7; font-size: 13px; font-weight: 500;">UPI ID: <strong>{upi_id}</strong> — {t('Payment links are active', 'पेमेंट लिंक चालू हैं')}</span>
            <span style="margin-left: auto; color: #475569; font-size: 12px;">{t('Edit in Settings below', 'नीचे बदलें')}</span>
        </div>
        """, unsafe_allow_html=True)
 
    tab_names = [t("Market Pulse", "बाज़ार की जानकारी"), t("Recovery Desk", "वसूली डेस्क"), t("Settings", "सेटिंग्स")]
    is_admin = st.session_state.user == "admin"
    if is_admin: tab_names.append(t("Admin Panel", "एडमिन पैनल"))
 
    tabs = st.tabs(tab_names)
 
    # ---------------- MARKET PULSE ----------------
    with tabs[0]:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
            <span style="font-size: 20px;">📊</span>
            <span style="color: #94a3b8; font-size: 14px;">{t('Industry & regional credit benchmarks', 'उद्योग और शहर के अनुसार क्रेडिट बेंचमार्क')}</span>
            <span class="demo-badge">⚠️ DEMO DATA</span>
        </div>
        """, unsafe_allow_html=True)
 
        col1, col2, col3 = st.columns(3)
        col1.metric(t("Total Market Credit", "बाज़ार में कुल उधार"), f"₹{market_df['Amount'].sum():,.0f}")
        col2.metric(t("Capital at Risk", "खतरे में पैसा"), f"₹{market_df[market_df['Status']=='Delayed']['Amount'].sum():,.0f}")
        col3.metric(t("Avg. Payment Delay", "औसत देरी (दिन)"), f"{market_df['Days_Delayed'].mean():.1f} days")
 
        st.markdown("<br>", unsafe_allow_html=True)
        sub_tab1, sub_tab2, sub_tab3 = st.tabs([t("Industry Analytics", "व्यापार विश्लेषण"), t("Geographic Analytics", "शहर विश्लेषण"), t("Risk Stratification", "रिस्क विश्लेषण")])
 
        with sub_tab1:
            data = market_df.groupby("Industry")["Credit_Days"].mean().reset_index()
            fig = px.bar(data, x="Industry", y="Credit_Days", color="Credit_Days", color_continuous_scale="Teal", template="plotly_dark")
            fig = apply_chart_layout(fig, t("Credit Cycle by Industry (days)", "उद्योग के अनुसार उधार के दिन"))
            st.plotly_chart(fig, use_container_width=True)
            jaankari_box(
                "FMCG counterparties exhibit high liquidity, clearing within 15 days, whereas Textile buyers are extending credit cycles beyond a month.",
                "Mandate a 50% upfront payment structure for all future Textile wholesale orders.",
                "FMCG वाले ग्राहक 15 दिनों में पैसे चुका रहे हैं, जबकि टेक्सटाइल वाले एक महीने से ज्यादा का समय ले रहे हैं।",
                "कैश फ्लो बनाए रखने के लिए, टेक्सटाइल के नए ऑर्डर पर 50% एडवांस लेना शुरू करें।"
            )
 
        with sub_tab2:
            data = market_df.groupby("City")["Days_Delayed"].mean().reset_index()
            fig = px.bar(data, x="City", y="Days_Delayed", color="Days_Delayed", color_continuous_scale="Reds", template="plotly_dark")
            fig = apply_chart_layout(fig, t("Capital Delay by Region (days)", "शहर के अनुसार देरी"))
            st.plotly_chart(fig, use_container_width=True)
            jaankari_box(
                "Counterparties in Surat are severely stretching working capital cycles (+20 days delay). Delhi accounts remain highly liquid.",
                "Reroute current inventory allocation to Delhi-based distributors.",
                "सूरत के ग्राहक पैसा बहुत ज्यादा रोक रहे हैं (20+ दिन की देरी)। दिल्ली के ग्राहक तेज़ी से पैसे दे रहे हैं।",
                "सूरत में नया माल भेजना रोकें और दिल्ली के ग्राहकों पर ज़्यादा फोकस करें।"
            )
 
        with sub_tab3:
            market_df["Risk"] = market_df["Days_Delayed"].apply(categorize)
            fig = px.pie(market_df, names="Risk", hole=0.45, color="Risk",
                         color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"},
                         template="plotly_dark")
            fig = apply_chart_layout(fig, t("Portfolio Risk Distribution", "रिस्क का बंटवारा"))
            st.plotly_chart(fig, use_container_width=True)
            jaankari_box(
                "A significant tranche of receivables is currently flagged as 'High Risk', indicating high probability of default.",
                "Suspend all credit extensions to High Risk profiles immediately.",
                "आपका बहुत सारा पैसा 'हाई रिस्क' (डूबने के खतरे) वाली जगह फंसा हुआ है।",
                "जब तक ये ग्राहक अपना पुराना बिल आधा साफ नहीं कर देते, इन्हें उधार न दें।"
            )
 
    # ---------------- RECOVERY DESK ----------------
    with tabs[1]:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3a5f22, #0f172a); border: 1px dashed #334155; border-radius: 12px; padding: 20px 24px; margin-bottom: 24px;">
            <div style="font-size: 14px; color: #94a3b8; margin-bottom: 6px;">{t('Upload your receivables ledger as a CSV file named', 'अपना बकाया डेटा CSV फ़ाइल के रूप में अपलोड करें, नाम होना चाहिए')} <code style="background: #1e293b; padding: 2px 8px; border-radius: 4px; color: #38bdf8;">udhaar_data.csv</code></div>
            <div style="font-size: 13px; color: #475569;">{t('Required columns:', 'ज़रूरी कॉलम:')} <span style="color: #64748b;">Name, Amount, Paid Amount, Due Date, Industry, City</span></div>
        </div>
        """, unsafe_allow_html=True)
 
        file = st.file_uploader("", type=["csv"])
 
        if file:
            df = pd.read_csv(file, encoding='utf-8', encoding_errors='ignore')
            required_cols = ["Name", "Amount", "Paid Amount", "Due Date", "Industry", "City"]
            if not all(col in df.columns for col in required_cols):
                st.error(t(f"Schema mismatch. Required headers: {', '.join(required_cols)}", f"फ़ाइल गलत है। ज़रूरी कॉलम: {', '.join(required_cols)}"))
                st.stop()
 
            df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce')
            current_upi = get_upi_id(st.session_state.user)
 
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
                display_date = row['Due Date'].strftime('%Y-%m-%d') if pd.notnull(row['Due Date']) else "N/A"
                msg = generate_ai_message(row['Name'], pending_amount, days, category, row['Industry'], current_upi)
 
                results.append({
                    "Name": row['Name'], "Amount": pending_amount, "Due Date": display_date,
                    "Industry": row['Industry'], "City": row['City'], "Days": days,
                    "Risk Score": round(risk, 2), "Category": category, "Credit Score": credit,
                    "Recovery %": round(prob * 100, 1), "Expected": round(expected, 0), "Message": msg
                })
 
            result_df = pd.DataFrame(results)
 
            if result_df.empty:
                st.markdown("""
                <div style="text-align: center; padding: 40px; color: #64748b;">
                    <div style="font-size: 48px; margin-bottom: 12px;">📭</div>
                    <div style="font-size: 18px; font-weight: 600; color: #94a3b8;">Ledger is clear</div>
                    <div style="font-size: 14px; margin-top: 6px;">Zero outstanding balances detected. Great work!</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<hr style='border-color: #1e293b; margin: 8px 0 20px;'>", unsafe_allow_html=True)
                st.subheader(t("Live Ledger Analysis", "लाइव डेटा रिपोर्ट"))
                st.dataframe(result_df.drop(columns=["Message"]), use_container_width=True)
 
                if st.button(t("Save to Ledger", "डेटाबेस में सेव करें")):
                    for _, row in result_df.iterrows():
                        cursor.execute("""
                        INSERT INTO transactions (username, customer, amount, due_date, industry, city, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (st.session_state.user, row['Name'], row['Amount'], row['Due Date'], row['Industry'], row['City'], "Pending"))
                    conn.commit()
                    st.success(t("Ledger saved successfully.", "डेटा सुरक्षित कर लिया गया है।"))
 
                # KPIs
                st.markdown("<hr style='border-color: #1e293b; margin: 20px 0;'>", unsafe_allow_html=True)
                st.subheader(t("Recovery Targets", "रिकवरी टारगेट"))
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("Gross Receivables", "कुल बकाया"), f"₹{result_df['Amount'].sum():,.0f}")
                c2.metric(t("Projected Inflow", "आने की उम्मीद"), f"₹{result_df['Expected'].sum():,.0f}")
                c3.metric(t("Critical Accounts", "खतरे वाले खाते"), len(result_df[result_df["Category"] == "High"]))
                c4.metric(t("Avg. Recovery Chance", "रिकवरी संभावना"), f"{result_df['Recovery %'].mean():.1f}%")
 
                # Charts
                st.markdown("<br>", unsafe_allow_html=True)
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig1 = px.bar(result_df, x="Name", y="Risk Score", color="Risk Score",
                                  color_continuous_scale="Turbo", template="plotly_dark")
                    fig1 = apply_chart_layout(fig1, t("Default Probability Index", "डिफॉल्ट रिस्क स्कोर (ग्राहक अनुसार)"))
                    st.plotly_chart(fig1, use_container_width=True)
                    jaankari_box(
                        "Spikes in the DPI isolate accounts most likely to default.",
                        "Bypass automated channels for peak-risk accounts. Initiate direct phone contact.",
                        "सबसे ऊंचे बार वाले ग्राहकों के पैसे लेकर भागने की संभावना सबसे ज़्यादा है।",
                        "अभी फोन उठाएं और इन ऊंचे स्कोर वाले ग्राहकों को सीधे कॉल करें।"
                    )
 
                with col_chart2:
                    fig2 = px.pie(result_df, names="Category", hole=0.45, color="Category",
                                  color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"},
                                  template="plotly_dark")
                    fig2 = apply_chart_layout(fig2, t("Account Risk Segmentation", "अकाउंट रिस्क केटेगरी"))
                    st.plotly_chart(fig2, use_container_width=True)
                    jaankari_box(
                        "Visualizes total capital tied up across safety tiers.",
                        "Deploy automated UPI links to 'Low' tier accounts. Reserve manual bandwidth for High risk.",
                        "यह चार्ट आपके ग्राहकों को सुरक्षित (Low) और खतरे (High) में बांटता है।",
                        "सुरक्षित वालों के लिए ऑटोमैटिक व्हाट्सएप करें। अपना समय हाई रिस्क वालों के लिए बचाएं।"
                    )
 
                # Forecast
                result_df_sorted = result_df.sort_values(by="Expected", ascending=False).copy()
                result_df_sorted["Index"] = range(1, len(result_df_sorted) + 1)
                result_df_sorted["Cum"] = result_df_sorted["Expected"].cumsum()
                fig_line = px.area(result_df_sorted, x="Index", y="Cum",
                                   template="plotly_dark", color_discrete_sequence=["#38bdf8"])
                fig_line = apply_chart_layout(fig_line, t("Liquidity Projection Curve", "इस हफ़्ते कैश फ्लो का अनुमान"))
                fig_line.update_traces(fillcolor="rgba(56,189,248,0.12)")
                st.plotly_chart(fig_line, use_container_width=True)
 
                # Communication Hub
                st.markdown("<hr style='border-color: #1e293b; margin: 20px 0;'>", unsafe_allow_html=True)
                st.subheader(t("WhatsApp Recovery Hub", "व्हाट्सएप रिकवरी हब"))
 
                if not current_upi:
                    st.warning(t("⚠️ UPI ID not set. Payment links in messages will use a placeholder. Set your UPI ID in the Settings tab.", "⚠️ UPI ID सेट नहीं है। Settings टैब में जाकर अपना UPI ID डालें।"))
 
                customer_list = result_df["Name"].tolist()
                selected_customer = st.selectbox(t("Select Customer Profile:", "ग्राहक चुनें:"), customer_list)
 
                if selected_customer:
                    customer_info = result_df[result_df["Name"] == selected_customer].iloc[0]
 
                    # Category badge color
                    badge_color = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}.get(customer_info['Category'], "#94a3b8")
 
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #1e3a5f33, #1e293b); padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <span style="color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">{t('Generated Recovery Message', 'तैयार किया गया रिकवरी मैसेज')}</span>
                            <span style="background: {badge_color}22; border: 1px solid {badge_color}44; color: {badge_color}; font-size: 11px; font-weight: 700; padding: 2px 10px; border-radius: 20px;">{customer_info['Category'].upper()} RISK</span>
                        </div>
                        <p style="color: #f8fafc; font-size: 15px; line-height: 1.6; margin: 0;">{customer_info['Message']}</p>
                    </div>
                    """, unsafe_allow_html=True)
 
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        target_phone = st.text_input(
                            t("Customer WhatsApp Number (with country code, no +)", "ग्राहक का WhatsApp नंबर (91 के साथ)"),
                            value="919876543210"
                        )
                        clean_phone = target_phone.replace("+", "").replace(" ", "").strip()
                        encoded_msg = urllib.parse.quote(customer_info['Message'])
                        wa_link = f"https://wa.me/{clean_phone}?text={encoded_msg}"
                        st.link_button(t("📲 Send via WhatsApp", "📲 WhatsApp पर भेजें"), wa_link, use_container_width=True)
 
                        if st.button(t("📝 Log Transmission", "📝 रिकॉर्ड में दर्ज करें"), use_container_width=True):
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            # Only log to communications (not duplicate transaction insert)
                            cursor.execute("INSERT INTO communications (username, customer, message, timestamp, status) VALUES (?, ?, ?, ?, ?)",
                                           (st.session_state.user, selected_customer, customer_info['Message'], timestamp, "Dispatched"))
                            conn.commit()
                            st.success(t("✅ Transmission logged.", "✅ रिकॉर्ड सफलतापूर्वक सेव हो गया।"))
 
                    with btn_col2:
                        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                        if st.button(t("✅ Mark as Paid", "✅ पैसा मिल गया (मार्क करें)"), type="primary", use_container_width=True):
                            cursor.execute("UPDATE transactions SET status='Recovered' WHERE customer=? AND username=? AND amount=? AND status='Pending'",
                                           (selected_customer, st.session_state.user, customer_info['Amount']))
                            conn.commit()
                            st.success(f"✅ {selected_customer} — {t('payment marked as recovered.', 'का पैसा मिल गया।')}")
 
                # Recovery History
                st.markdown("<hr style='border-color: #1e293b; margin: 20px 0;'>", unsafe_allow_html=True)
                st.subheader(t("Recovery History", "रिकवरी इतिहास"))
                history_df = safe_read_sql("SELECT customer, amount, due_date, status FROM transactions WHERE username=?", conn, params=(st.session_state.user,))
 
                if not history_df.empty:
                    st.dataframe(history_df, use_container_width=True)
                else:
                    st.markdown("""
                    <div style="text-align: center; padding: 30px; color: #64748b;">
                        <div style="font-size: 36px; margin-bottom: 10px;">📭</div>
                        <div style="font-size: 15px; font-weight: 500; color: #94a3b8;">No recovery records yet</div>
                        <div style="font-size: 13px; margin-top: 4px;">Save your ledger or log a transmission above to get started.</div>
                    </div>
                    """, unsafe_allow_html=True)
 
                # PDF Download
                st.markdown("<hr style='border-color: #1e293b; margin: 20px 0;'>", unsafe_allow_html=True)
                st.subheader(t("Download Recovery Report", "रिकवरी रिपोर्ट डाउनलोड करें"))
                pdf_bytes = generate_pdf_report(result_df)
                st.download_button(
                    label=t("📄 Download Recovery Report (PDF)", "📄 PDF रिपोर्ट डाउनलोड करें"),
                    data=pdf_bytes,
                    file_name=f"KhataKhat_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
 
    # ---------------- SETTINGS ----------------
    with tabs[2]:
        st.subheader(t("Account Settings", "खाता सेटिंग्स"))
        st.markdown("<br>", unsafe_allow_html=True)
 
        col_s1, col_s2 = st.columns([1, 1])
        with col_s1:
            st.markdown(f"<div style='color: #94a3b8; font-size: 13px; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;'>{t('UPI Payment ID', 'UPI पेमेंट ID')}</div>", unsafe_allow_html=True)
            current_upi_display = get_upi_id(st.session_state.user)
            upi_input = st.text_input(t("Your UPI ID", "आपका UPI ID"), value=current_upi_display, placeholder="yourname@okaxis", label_visibility="collapsed")
            if st.button(t("Update UPI ID", "UPI ID अपडेट करें"), type="primary"):
                if "@" in upi_input and len(upi_input) > 5:
                    save_upi_id(st.session_state.user, upi_input)
                    st.success(t("UPI ID updated successfully.", "UPI ID अपडेट हो गई।"))
                    st.rerun()
                else:
                    st.error(t("Please enter a valid UPI ID (e.g. name@okaxis).", "सही UPI ID डालें।"))
 
        with col_s2:
            st.markdown(f"""
            <div style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 20px;">
                <div style="color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">Account Info</div>
                <div style="color: #94a3b8; font-size: 14px; margin-bottom: 8px;">Username: <span style="color: #f8fafc; font-weight: 600;">{st.session_state.user}</span></div>
                <div style="color: #94a3b8; font-size: 14px;">Session started: <span style="color: #f8fafc;">{datetime.now().strftime('%d %b %Y, %H:%M')}</span></div>
            </div>
            """, unsafe_allow_html=True)
 
    # ---------------- ADMIN PANEL ----------------
    if is_admin:
        with tabs[3]:
            st.header(t("Admin Panel", "एडमिन पैनल"))
            st.subheader(t("WhatsApp Transmission Logs", "व्हाट्सएप लॉग्स"))
            comm_data = safe_read_sql("SELECT * FROM communications ORDER BY id DESC", conn)
            if not comm_data.empty:
                st.dataframe(comm_data, use_container_width=True)
            else:
                st.markdown("""
                <div style="text-align: center; padding: 24px; color: #64748b;">
                    <div style="font-size: 32px;">📭</div>
                    <div style="margin-top: 8px;">No transmission logs yet.</div>
                </div>
                """, unsafe_allow_html=True)
 
            st.markdown("<hr style='border-color: #1e293b; margin: 20px 0;'>", unsafe_allow_html=True)
            st.subheader(t("Master Transaction Ledger", "मास्टर ट्रांज़ैक्शन लेजर"))
            tx_data = safe_read_sql("SELECT * FROM transactions", conn)
            if not tx_data.empty:
                st.dataframe(tx_data, use_container_width=True)
            else:
                st.markdown("""
                <div style="text-align: center; padding: 24px; color: #64748b;">
                    <div style="font-size: 32px;">📭</div>
                    <div style="margin-top: 8px;">Database is empty.</div>
                </div>
                """, unsafe_allow_html=True)
 
# -------------------------------
# COPYRIGHT FOOTER
# -------------------------------
st.markdown("""
    <div style='text-align: center; margin-top: 60px; padding: 20px; color: #334155; font-size: 13px; font-weight: 500; border-top: 1px solid #1e293b;'>
        © 2025 KhataKhat · Built by Ebin Davis · All rights reserved
    </div>
""", unsafe_allow_html=True)
