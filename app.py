"""
KhataKhat - Startup-Grade Receivables Recovery Platform
All 25 security + feature enhancements applied.
Author: Ebin Davis
"""

import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import bcrypt
import qrcode
import logging
import re
import os
import secrets
import smtplib
import io
import time
from io import BytesIO
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import urllib.parse
from PIL import Image, ImageDraw

# -----------------------------------------------------------------------
# #25 — LOGGING SETUP (rotating file + console)
# -----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("khatakhat")

# -----------------------------------------------------------------------
# #10 — SECRETS / ENV CONFIG  (st.secrets with .env fallback)
# -----------------------------------------------------------------------
def get_secret(key: str, fallback: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, fallback)

# Encryption key — generate once and persist in secrets/env
RAW_KEY = get_secret("ENCRYPTION_KEY", "")
if not RAW_KEY:
    # Dev-mode: generate an ephemeral key (warn operator)
    RAW_KEY = Fernet.generate_key().decode()
    logger.warning("ENCRYPTION_KEY not set — using ephemeral key. Set it in st.secrets for production.")

try:
    FERNET = Fernet(RAW_KEY.encode() if isinstance(RAW_KEY, str) else RAW_KEY)
except Exception:
    FERNET = Fernet(Fernet.generate_key())
    logger.error("Invalid ENCRYPTION_KEY format — falling back to ephemeral key.")

DB_PATH = get_secret("DB_PATH", "khatakhat.db")
SESSION_TIMEOUT_MINUTES = int(get_secret("SESSION_TIMEOUT_MINUTES", "30"))
MAX_LOGIN_ATTEMPTS = int(get_secret("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(get_secret("LOCKOUT_MINUTES", "15"))

SMTP_HOST     = get_secret("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(get_secret("SMTP_PORT", "587"))
SMTP_USER     = get_secret("SMTP_USER", "")
SMTP_PASSWORD = get_secret("SMTP_PASSWORD", "")

# -----------------------------------------------------------------------
# STREAMLIT PAGE CONFIG
# -----------------------------------------------------------------------
st.set_page_config(page_title="KhataKhat", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Syne:wght@600;700;800&display=swap');

:root {
    --bg-deep:    #080f1e;
    --bg-mid:     #0f1f35;
    --bg-card:    #132033;
    --bg-raised:  #1a2d44;
    --border:     #1e3a5a;
    --border-lit: #2d5278;
    --accent:     #29b6f6;
    --accent-dim: #0d7ab5;
    --accent-glow:rgba(41,182,246,0.18);
    --success:    #26d97f;
    --warning:    #f5a623;
    --danger:     #ef4444;
    --text-hi:    #f0f6ff;
    --text-mid:   #8eacc8;
    --text-lo:    #3d5a72;
}

/* ── Base ── */
.stApp {
    background: radial-gradient(ellipse 120% 80% at 60% -10%, #0d2745 0%, var(--bg-deep) 55%);
    color: var(--text-hi);
    font-family: 'DM Sans', sans-serif;
}
.stApp::after {
    content:'';
    position:fixed;
    inset:0;
    background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='400' height='400' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");
    pointer-events:none;
    z-index:9999;
}
#MainMenu,footer,header{visibility:hidden}

/* ── Typography ── */
h1,h2,h3{font-family:'Syne',sans-serif !important;font-weight:800;color:var(--text-hi) !important;letter-spacing:-0.4px;}

/* ── Metric Cards ── */
div[data-testid="metric-container"]{
    background:linear-gradient(145deg,var(--bg-card),var(--bg-raised));
    border:1px solid var(--border);
    border-left:3px solid var(--accent);
    padding:1.4rem 1.6rem;
    border-radius:12px;
    box-shadow:0 4px 20px rgba(0,0,0,0.35);
    transition:all .22s ease;
}
div[data-testid="metric-container"]:hover{
    transform:translateY(-3px);
    box-shadow:0 10px 32px var(--accent-glow);
    border-left-color:#7dd3fc;
}
div[data-testid="metric-container"] label{color:var(--text-mid) !important;font-weight:500 !important;font-size:.95rem !important;}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:var(--text-hi) !important;font-weight:700 !important;font-family:'Syne',sans-serif !important;}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] svg{display:inline;}

/* ── Tabs ── */
button[data-baseweb="tab"]{color:var(--text-mid) !important;font-size:14px !important;font-weight:600;font-family:'DM Sans',sans-serif !important;transition:color .18s;}
button[aria-selected="true"]{color:var(--accent) !important;border-bottom:2px solid var(--accent) !important;}

/* ── Buttons ── */
.stButton>button{font-family:'DM Sans',sans-serif !important;font-weight:600;border-radius:8px;transition:all .2s ease;}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 4px 14px var(--accent-glow);}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,var(--accent-dim),var(--accent)) !important;border:none !important;}

/* ── Inputs ── */
.stTextInput>div>div>input,.stSelectbox>div>div{
    background:var(--bg-mid) !important;border:1px solid var(--border) !important;
    color:var(--text-hi) !important;border-radius:8px !important;
    font-family:'DM Sans',sans-serif !important;
}
.stTextInput>div>div>input:focus{border-color:var(--accent) !important;box-shadow:0 0 0 2px var(--accent-glow) !important;}

/* ── Dataframe ── */
.stDataFrame{border-radius:10px;box-shadow:0 2px 16px rgba(0,0,0,0.3);border:1px solid var(--border);}

/* ── File uploader ── */
.stFileUploader{border:2px dashed var(--border);border-radius:12px;padding:10px;transition:border-color .2s;}
.stFileUploader:hover{border-color:var(--accent);}

/* ── Alert ── */
.stAlert{border-radius:8px;font-family:'DM Sans',sans-serif;}

/* ── Custom badges ── */
.badge-demo{display:inline-block;background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.35);color:#fbbf24;font-size:11px;font-weight:700;padding:2px 10px;border-radius:20px;letter-spacing:.6px;vertical-align:middle;}
.badge-ok  {display:inline-block;background:rgba(38,217,127,.10);border:1px solid rgba(38,217,127,.30);color:var(--success);font-size:11px;font-weight:700;padding:2px 10px;border-radius:20px;}
.badge-warn{display:inline-block;background:rgba(245,166,35,.10);border:1px solid rgba(245,166,35,.30);color:var(--warning);font-size:11px;font-weight:700;padding:2px 10px;border-radius:20px;}
.badge-bad {display:inline-block;background:rgba(239, 68,68,.10);border:1px solid rgba(239, 68,68,.30);color:var(--danger) ;font-size:11px;font-weight:700;padding:2px 10px;border-radius:20px;}

/* ── Divider ── */
hr.kk{border:none;border-top:1px solid var(--border);margin:22px 0;}

/* ── Sidebar ── */
section[data-testid="stSidebar"]{background:var(--bg-deep) !important;}

/* ── Scrollbar ── */
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:var(--bg-deep);}
::-webkit-scrollbar-thumb{background:var(--border-lit);border-radius:4px;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------
# #11 — DATABASE SETUP  (with schema versioning)
# -----------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

SCHEMA_VERSION = 4

def get_schema_version():
    cursor.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)")
    row = cursor.execute("SELECT version FROM schema_version").fetchone()
    return row[0] if row else 0

def set_schema_version(v):
    cursor.execute("DELETE FROM schema_version")
    cursor.execute("INSERT INTO schema_version VALUES (?)", (v,))
    conn.commit()

def run_migrations():
    v = get_schema_version()
    if v < 1:
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            username    TEXT PRIMARY KEY,
            password    BLOB NOT NULL,
            upi_id_enc  TEXT DEFAULT '',
            email_enc   TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now')),
            failed_attempts INTEGER DEFAULT 0,
            locked_until    TEXT DEFAULT NULL
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT,
            customer    TEXT,
            amount      REAL,
            due_date    TEXT,
            industry    TEXT,
            city        TEXT,
            status      TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS communications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT,
            customer    TEXT,
            message_enc TEXT,
            timestamp   TEXT,
            status      TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token       TEXT PRIMARY KEY,
            username    TEXT,
            created_at  TEXT,
            expires_at  TEXT
        )""")
        set_schema_version(1)
    if v < 2:
        # Add customer email column to transactions
        for col in ["customer_email TEXT DEFAULT ''", "notes TEXT DEFAULT ''"]:
            try:
                cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col}")
            except Exception:
                pass
        set_schema_version(2)
    if v < 3:
        # Add dark_mode preference
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN dark_mode INTEGER DEFAULT 1")
        except Exception:
            pass
        set_schema_version(3)
    if v < 4:
        # Add aging_bucket to transactions
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN aging_bucket TEXT DEFAULT ''")
        except Exception:
            pass
        set_schema_version(4)
    conn.commit()

run_migrations()

# -----------------------------------------------------------------------
# #5 — ENCRYPTION HELPERS
# -----------------------------------------------------------------------
def encrypt(text: str) -> str:
    if not text:
        return ""
    try:
        return FERNET.encrypt(text.encode()).decode()
    except Exception:
        return text

def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        return FERNET.decrypt(token.encode()).decode()
    except Exception:
        return token  # fallback for unencrypted legacy values

# -----------------------------------------------------------------------
# #1 — BCRYPT PASSWORD HASHING
# -----------------------------------------------------------------------
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))

def verify_password(password: str, hashed) -> bool:
    try:
        if isinstance(hashed, str):
            hashed = hashed.encode()
        return bcrypt.checkpw(password.encode(), hashed)
    except Exception:
        return False

# -----------------------------------------------------------------------
# #6 — UPI ID VALIDATION
# -----------------------------------------------------------------------
UPI_REGEX = re.compile(r'^[a-zA-Z0-9._\-]{2,}@[a-zA-Z]{3,}$')

def is_valid_upi(upi: str) -> bool:
    return bool(UPI_REGEX.match(upi.strip()))

# -----------------------------------------------------------------------
# #4 — INPUT SANITIZER
# -----------------------------------------------------------------------
def sanitize(text: str, max_len: int = 200) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r"[;'\"\\]", "", text).strip()
    return cleaned[:max_len]

# -----------------------------------------------------------------------
# #2 + #3 — SESSION TOKENS + RATE LIMITING
# -----------------------------------------------------------------------
def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires = now + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    cursor.execute(
        "INSERT INTO sessions (token, username, created_at, expires_at) VALUES (?,?,?,?)",
        (token, username, now.isoformat(), expires.isoformat())
    )
    conn.commit()
    logger.info(f"Session created for user '{username}'")
    return token

def validate_session(token: str):
    if not token:
        return None
    row = cursor.execute(
        "SELECT username, expires_at FROM sessions WHERE token=?", (token,)
    ).fetchone()
    if not row:
        return None
    username, expires_at = row
    if datetime.utcnow() > datetime.fromisoformat(expires_at):
        cursor.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
        logger.info(f"Session expired for '{username}'")
        return None
    # Slide expiry window
    new_expiry = (datetime.utcnow() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)).isoformat()
    cursor.execute("UPDATE sessions SET expires_at=? WHERE token=?", (new_expiry, token))
    conn.commit()
    return username

def destroy_session(token: str):
    cursor.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()

def is_account_locked(username: str) -> tuple:
    row = cursor.execute(
        "SELECT failed_attempts, locked_until FROM users WHERE username=?", (username,)
    ).fetchone()
    if not row:
        return False, None
    attempts, locked_until = row
    if locked_until:
        lock_dt = datetime.fromisoformat(locked_until)
        if datetime.utcnow() < lock_dt:
            return True, lock_dt
        else:
            # Unlock
            cursor.execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE username=?", (username,))
            conn.commit()
    return False, None

def record_failed_attempt(username: str):
    cursor.execute("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE username=?", (username,))
    row = cursor.execute("SELECT failed_attempts FROM users WHERE username=?", (username,)).fetchone()
    if row and row[0] >= MAX_LOGIN_ATTEMPTS:
        lock_until = (datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
        cursor.execute("UPDATE users SET locked_until=? WHERE username=?", (lock_until, username))
        logger.warning(f"Account '{username}' locked after {MAX_LOGIN_ATTEMPTS} failed attempts.")
    conn.commit()

def reset_failed_attempts(username: str):
    cursor.execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE username=?", (username,))
    conn.commit()

# -----------------------------------------------------------------------
# AUTH
# -----------------------------------------------------------------------
def create_user(username: str, password: str) -> bool:
    username = sanitize(username)
    try:
        hashed = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password, upi_id_enc, email_enc) VALUES (?,?,?,?)",
            (username, hashed, "", "")
        )
        conn.commit()
        logger.info(f"New user created: '{username}'")
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username: str, password: str):
    username = sanitize(username)
    locked, lock_until = is_account_locked(username)
    if locked:
        remaining = int((lock_until - datetime.utcnow()).total_seconds() / 60) + 1
        return None, f"Account locked. Try again in {remaining} minute(s)."
    row = cursor.execute("SELECT password FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        logger.warning(f"Login attempt for unknown user: '{username}'")
        return None, "Invalid credentials."
    if verify_password(password, row[0]):
        reset_failed_attempts(username)
        token = create_session(username)
        logger.info(f"Successful login: '{username}'")
        return token, None
    else:
        record_failed_attempt(username)
        row2 = cursor.execute("SELECT failed_attempts FROM users WHERE username=?", (username,)).fetchone()
        remaining = MAX_LOGIN_ATTEMPTS - (row2[0] if row2 else 0)
        logger.warning(f"Failed login for '{username}'. {remaining} attempts remaining.")
        return None, f"Invalid credentials. {max(remaining,0)} attempt(s) remaining."

# Seed admin account
if not cursor.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
    create_user("admin", "Admin@12345")
    logger.info("Default admin account seeded.")

# -----------------------------------------------------------------------
# USER PREFERENCES
# -----------------------------------------------------------------------
def get_upi_id(username: str) -> str:
    row = cursor.execute("SELECT upi_id_enc FROM users WHERE username=?", (username,)).fetchone()
    return decrypt(row[0]) if row and row[0] else ""

def save_upi_id(username: str, upi_id: str):
    cursor.execute("UPDATE users SET upi_id_enc=? WHERE username=?", (encrypt(upi_id), username))
    conn.commit()

def get_email(username: str) -> str:
    row = cursor.execute("SELECT email_enc FROM users WHERE username=?", (username,)).fetchone()
    return decrypt(row[0]) if row and row[0] else ""

def save_email(username: str, email: str):
    cursor.execute("UPDATE users SET email_enc=? WHERE username=?", (encrypt(email), username))
    conn.commit()

# -----------------------------------------------------------------------
# SQL SANITIZER
# -----------------------------------------------------------------------
def safe_read_sql(query, db_conn, params=()):
    cur = db_conn.cursor()
    cur.execute(query, params)
    if not cur.description:
        return pd.DataFrame()
    cols = [d[0] for d in cur.description]
    rows = []
    for row in cur.fetchall():
        rows.append([
            v.decode('utf-8', 'ignore') if isinstance(v, bytes)
            else v.encode('utf-8', 'ignore').decode('utf-8') if isinstance(v, str)
            else v
            for v in row
        ])
    return pd.DataFrame(rows, columns=cols)

# -----------------------------------------------------------------------
# PLOTLY THEME
# -----------------------------------------------------------------------
def apply_chart_layout(fig, title=""):
    fig.update_layout(
        font=dict(family="'DM Sans', sans-serif", color="#8eacc8", size=12),
        title_font=dict(family="'Syne', sans-serif", size=15, color="#f0f6ff"),
        title_text=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,15,30,0.5)",
        xaxis=dict(gridcolor="#132033", zerolinecolor="#1e3a5a", tickfont=dict(color="#8eacc8")),
        yaxis=dict(gridcolor="#132033", zerolinecolor="#1e3a5a", tickfont=dict(color="#8eacc8")),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8eacc8")),
        margin=dict(t=50, b=30, l=15, r=15),
    )
    return fig

# -----------------------------------------------------------------------
# LANGUAGE MANAGER
# -----------------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "English"

def t(en, hi):
    return en if st.session_state.lang == "English" else hi

def jaankari_box(obs_en, act_en, obs_hi, act_hi):
    obs = obs_en if st.session_state.lang == "English" else obs_hi
    act = act_en if st.session_state.lang == "English" else act_hi
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#080f1e,#0d1e35);border-left:3px solid #0284c7;
                padding:16px 20px;border-radius:10px;margin:14px 0 22px;
                border:1px solid #1e3a5a;box-shadow:0 4px 16px rgba(2,132,199,.08);">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <span style="font-size:15px;">💡</span>
            <span style="color:#29b6f6;font-size:11px;text-transform:uppercase;letter-spacing:1.8px;
                         font-weight:700;font-family:'Syne',sans-serif;">Jaankari</span>
        </div>
        <p style="margin:0 0 7px;font-size:13.5px;color:#8eacc8;">
            <strong style="color:#f0f6ff;">{t('Observation: ','स्थिति: ')}</strong>{obs}</p>
        <p style="margin:0;font-size:13.5px;color:#8eacc8;">
            <strong style="color:#f0f6ff;">{t('Action Plan: ','सुझाव: ')}</strong>{act}</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------
# MARKET DATA
# -----------------------------------------------------------------------
market_df = pd.DataFrame({
    "Industry":    ["FMCG","Textile","Electronics","FMCG","Pharma","Retail"],
    "City":        ["Delhi","Surat","Mumbai","Delhi","Ahmedabad","Jaipur"],
    "Amount":      [5000, 12000, 8000, 6000, 15000, 4000],
    "Credit_Days": [15, 30, 10, 12, 20, 8],
    "Days_Delayed":[3, 20, 2, 8, 5, 9],
    "Status":      ["Paid","Delayed","Paid","Delayed","Paid","Delayed"]
})

# -----------------------------------------------------------------------
# BUSINESS LOGIC
# -----------------------------------------------------------------------
def get_city_risk(city):
    data = market_df[market_df["City"] == city]
    return data["Days_Delayed"].mean() if not data.empty else 5

def calculate_days_overdue(due_date):
    if pd.isnull(due_date):
        return 0
    return max((datetime.today() - due_date).days, 0)

def aging_bucket(days: int) -> str:
    if days <= 30:   return "0–30 days"
    elif days <= 60: return "31–60 days"
    elif days <= 90: return "61–90 days"
    else:            return "90+ days"

def categorize(days: int) -> str:
    if days < 5:   return "Low"
    elif days < 15: return "Medium"
    else:          return "High"

def calculate_risk(days, amount, industry, city):
    return (days * 0.5) + (amount * 0.2) + (get_city_risk(city) * 0.3)

def calculate_credit_score(days, amount):
    score = 100 - (days * 2)
    if amount > 10000: score -= 10
    return max(score, 0)

def predict_recovery_probability(days, amount, category):
    base = 0.8 - (days * 0.02)
    if amount > 10000: base -= 0.1
    if category == "High":   base -= 0.2
    elif category == "Medium": base -= 0.1
    return max(min(base, 1.0), 0.0)

def generate_ai_message(name, amount, days, category, industry, upi_id):
    upi_target = upi_id if upi_id else "yourname@upi"
    link = f"upi://pay?pa={urllib.parse.quote(upi_target)}&am={amount}&cu=INR&tn=Invoice+Payment"
    if st.session_state.lang == "English":
        if category == "Low":
            return f"Hi {name}, a gentle reminder for your pending amount of ₹{amount:,.0f}. Please complete payment: {link}"
        elif category == "Medium":
            return f"Hello {name}, ₹{amount:,.0f} is pending. Most {industry} payments clear within the week. Please pay: {link}"
        else:
            return f"URGENT: {name}, ₹{amount:,.0f} is overdue by {days} days. Please pay immediately to avoid escalation: {link}"
    else:
        if category == "Low":
            return f"नमस्ते {name}, आपके ₹{amount:,.0f} बकाया हैं। कृपया यहाँ भुगतान करें: {link}"
        elif category == "Medium":
            return f"नमस्कार {name}, आपके ₹{amount:,.0f} पेंडिंग हैं। जल्द भुगतान करें: {link}"
        else:
            return f"जरूरी: {name}, ₹{amount:,.0f} — {days} दिन से पेंडिंग। तुरंत भुगतान करें: {link}"

# -----------------------------------------------------------------------
# #7 + #8 — QR CODE GENERATOR (with branded ₹ overlay)
# -----------------------------------------------------------------------
def generate_upi_qr(upi_id: str, amount: float, customer_name: str) -> bytes:
    upi_string = (
        f"upi://pay?pa={urllib.parse.quote(upi_id)}"
        f"&am={amount:.2f}&cu=INR"
        f"&tn={urllib.parse.quote('Payment from ' + customer_name)}"
    )
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=3,
    )
    qr.add_data(upi_string)
    qr.make(fit=True)

    # High-contrast dark QR
    img = qr.make_image(fill_color="#f0f6ff", back_color="#0f1f35").convert("RGBA")
    size = img.size[0]

    # Draw branded ₹ overlay circle in centre
    overlay_r = int(size * 0.1)
    cx = cy = size // 2
    draw = ImageDraw.Draw(img)
    draw.ellipse(
        [cx - overlay_r, cy - overlay_r, cx + overlay_r, cy + overlay_r],
        fill="#0f1f35"
    )
    # Draw ₹ symbol
    font_size = int(overlay_r * 1.2)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = None
    symbol = "₹"
    if font:
        bbox = draw.textbbox((0, 0), symbol, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2 - 2), symbol, fill="#29b6f6", font=font)
    else:
        draw.text((cx - font_size // 3, cy - font_size // 2), "R", fill="#29b6f6")

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# -----------------------------------------------------------------------
# #18 — EMAIL REMINDERS
# -----------------------------------------------------------------------
def send_email_reminder(to_email: str, customer_name: str, amount: float, message: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured — email not sent.")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Payment Reminder — ₹{amount:,.0f} Outstanding"
        msg["From"]    = SMTP_USER
        msg["To"]      = to_email
        html = f"""
        <html><body style="font-family:sans-serif;background:#0f1f35;color:#f0f6ff;padding:32px;">
        <div style="max-width:520px;margin:auto;background:#132033;border-radius:12px;padding:28px;border:1px solid #1e3a5a;">
            <h2 style="color:#29b6f6;margin-top:0;">KhataKhat Payment Reminder</h2>
            <p style="color:#8eacc8;">{message}</p>
            <hr style="border-color:#1e3a5a;"/>
            <p style="font-size:12px;color:#3d5a72;">KhataKhat · Smart Receivables Recovery · India</p>
        </div></body></html>"""
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        logger.info(f"Email reminder sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False

# -----------------------------------------------------------------------
# PDF REPORT  (enhanced with aging buckets + QR stub)
# -----------------------------------------------------------------------
def generate_pdf_report(df: pd.DataFrame, upi_id: str = "") -> bytes:
    pdf = FPDF()
    pdf.add_page()
    def clean(text):
        return str(text).replace("₹", "Rs.").encode('latin-1', 'ignore').decode('latin-1')
    pdf.set_fill_color(8, 15, 30)
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_text_color(240, 246, 255)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 12, "KhataKhat - Recovery Report", ln=True, align='C')
    pdf.set_font("Arial", size=9)
    pdf.set_text_color(142, 172, 200)
    pdf.cell(0, 7, f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}  |  Confidential", ln=True, align='C')
    pdf.ln(6)
    pdf.set_text_color(240, 246, 255)
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(0, 9, "Executive Summary", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(142, 172, 200)
    total_due  = df['Amount'].sum()
    expected   = df['Expected'].sum()
    high_count = len(df[df['Category'] == 'High'])
    pdf.multi_cell(0, 6, clean(
        f"Total Pending: Rs. {total_due:,.0f}  |  AI Expected Recovery: Rs. {expected:,.0f}  |  Critical Accounts: {high_count}"
    ))
    pdf.ln(5)
    # Aging summary
    if 'Aging' in df.columns:
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(41, 182, 246)
        pdf.cell(0, 8, "Aging Breakdown", ln=True)
        pdf.set_font("Arial", size=9)
        pdf.set_text_color(142, 172, 200)
        for bucket, grp in df.groupby("Aging"):
            pdf.cell(0, 6, clean(f"  {bucket}: Rs. {grp['Amount'].sum():,.0f} across {len(grp)} accounts"), ln=True)
        pdf.ln(4)
    # Per-account detail
    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(41, 182, 246)
    pdf.cell(0, 8, "Account Detail", ln=True)
    for _, row in df.iterrows():
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(240, 246, 255)
        pdf.cell(0, 7, clean(f"{row['Name']}  ({row['Industry']} · {row['City']})"), ln=True)
        pdf.set_font("Arial", size=9)
        pdf.set_text_color(142, 172, 200)
        pdf.cell(0, 5, clean(
            f"  Due: Rs.{row['Amount']:,.0f}  |  Days Overdue: {row['Days']}  |  Risk: {row['Category']}  |  Recovery: {row['Recovery %']}%"
        ), ln=True)
        pdf.ln(2)
    pdf.set_y(-18)
    pdf.set_font("Arial", size=8)
    pdf.set_text_color(61, 90, 114)
    pdf.cell(0, 6, "© KhataKhat · Built by Ebin Davis · All rights reserved", align='C')
    return pdf.output(dest="S").encode("latin-1")

# -----------------------------------------------------------------------
# SESSION STATE INIT
# -----------------------------------------------------------------------
if "session_token" not in st.session_state:
    st.session_state.session_token = None
if "user" not in st.session_state:
    st.session_state.user = None

# Validate existing session on every rerun
if st.session_state.session_token:
    validated = validate_session(st.session_state.session_token)
    if not validated:
        st.session_state.session_token = None
        st.session_state.user = None
    else:
        st.session_state.user = validated

logged_in = st.session_state.session_token is not None

# ═══════════════════════════════════════════════════════════════════════
#  LOGIN SCREEN
# ═══════════════════════════════════════════════════════════════════════
if not logged_in:
    col_logo, col_lang = st.columns([3, 1])
    with col_logo:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:2px;">
            <div style="background:linear-gradient(135deg,#0d4a7a,#29b6f6);border-radius:12px;
                        width:48px;height:48px;display:flex;align-items:center;justify-content:center;
                        font-size:24px;box-shadow:0 4px 20px rgba(41,182,246,0.35);">₹</div>
            <h1 style="margin:0;font-family:'Syne',sans-serif;font-size:34px;color:#f0f6ff !important;">
                KhataKhat</h1>
        </div>
        """, unsafe_allow_html=True)
    with col_lang:
        st.session_state.lang = st.radio(
            "lang", ["English", "हिंदी"], horizontal=True, label_visibility="collapsed")

    st.markdown(f"""
    <p style="color:#8eacc8;font-size:15px;margin:4px 0 0;">
        {t("India's smart receivables recovery platform for MSMEs.",
           "भारत के MSME व्यापारियों के लिए स्मार्ट वसूली प्लेटफॉर्म।")}<br>
        <span style="color:#3d5a72;font-size:13px;">
        {t("Track dues · Predict defaults · Recover faster.",
           "बकाया ट्रैक करें · डिफॉल्ट पहचानें · जल्दी वसूलें।")}</span>
    </p>
    <hr class="kk" style="margin:18px 0;">
    """, unsafe_allow_html=True)

    col_form, col_feat = st.columns([1, 1])
    with col_form:
        st.markdown(f"<h3>{t('Secure Portal','सुरक्षित पोर्टल')}</h3>", unsafe_allow_html=True)
        choice = st.radio(
            "auth", [t("Login","लॉगिन"), t("Register","नया खाता")],
            horizontal=True, label_visibility="collapsed")

        if choice in ("Login", "लॉगिन"):
            u = st.text_input(t("Username","यूज़रनेम"))
            p = st.text_input(t("Password","पासवर्ड"), type="password")
            if st.button(t("Access Platform","लॉगिन करें"), type="primary"):
                with st.spinner(t("Authenticating…","सत्यापन हो रहा है…")):
                    token, err = login_user(u, p)
                if token:
                    st.session_state.session_token = token
                    st.session_state.user = u
                    st.toast(t("Welcome back!","वापस आने पर स्वागत है!"), icon="✅")
                    st.rerun()
                else:
                    st.error(err)
        else:
            nu = st.text_input(t("New Username","नया यूज़रनेम"))
            np_ = st.text_input(t("New Password (min 6 chars)","नया पासवर्ड (न्यूनतम 6 अक्षर)"), type="password")
            if st.button(t("Create Account","खाता बनाएं"), type="primary"):
                if len(nu.strip()) < 3:
                    st.error(t("Username must be ≥ 3 characters.","यूज़रनेम कम से कम 3 अक्षर का होना चाहिए।"))
                elif len(np_) < 6:
                    st.error(t("Password must be ≥ 6 characters.","पासवर्ड कम से कम 6 अक्षर का होना चाहिए।"))
                elif create_user(nu.strip(), np_):
                    st.success(t("Account created. You can now log in.","खाता बन गया। अब लॉगिन करें।"))
                else:
                    st.error(t("Username already exists.","यह यूज़रनेम पहले से मौजूद है।"))

    with col_feat:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0d1e3522,#080f1e);border:1px solid #1e3a5a;
                    border-radius:14px;padding:26px 28px;margin-top:46px;">
            <div style="font-size:11px;color:#3d5a72;text-transform:uppercase;letter-spacing:1.2px;
                        font-weight:700;margin-bottom:18px;">Platform Features</div>
            <div style="display:flex;flex-direction:column;gap:14px;">
                <div style="display:flex;gap:14px;align-items:flex-start;">
                    <span style="font-size:20px;">📊</span>
                    <div><div style="color:#f0f6ff;font-weight:600;font-size:13.5px;">Market Pulse Analytics</div>
                         <div style="color:#3d5a72;font-size:12px;">Industry & city-level credit benchmarks</div></div>
                </div>
                <div style="display:flex;gap:14px;align-items:flex-start;">
                    <span style="font-size:20px;">🤖</span>
                    <div><div style="color:#f0f6ff;font-weight:600;font-size:13.5px;">AI Risk Scoring</div>
                         <div style="color:#3d5a72;font-size:12px;">Predict defaults before they happen</div></div>
                </div>
                <div style="display:flex;gap:14px;align-items:flex-start;">
                    <span style="font-size:20px;">📱</span>
                    <div><div style="color:#f0f6ff;font-weight:600;font-size:13.5px;">UPI QR Code Generator</div>
                         <div style="color:#3d5a72;font-size:12px;">Branded scannable QR per customer</div></div>
                </div>
                <div style="display:flex;gap:14px;align-items:flex-start;">
                    <span style="font-size:20px;">💬</span>
                    <div><div style="color:#f0f6ff;font-weight:600;font-size:13.5px;">WhatsApp + Email Recovery</div>
                         <div style="color:#3d5a72;font-size:12px;">Dual-channel automated reminders</div></div>
                </div>
                <div style="display:flex;gap:14px;align-items:flex-start;">
                    <span style="font-size:20px;">🔒</span>
                    <div><div style="color:#f0f6ff;font-weight:600;font-size:13.5px;">Bank-Grade Security</div>
                         <div style="color:#3d5a72;font-size:12px;">bcrypt · Fernet encryption · Session tokens</div></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════
else:
    username = st.session_state.user

    # ── Top Nav ──
    n1, n2, n3, n4 = st.columns([4, 2, 2, 1])
    with n1:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin-top:-6px;">
            <div style="background:linear-gradient(135deg,#0d4a7a,#29b6f6);border-radius:8px;
                        width:36px;height:36px;display:flex;align-items:center;justify-content:center;
                        font-size:18px;flex-shrink:0;box-shadow:0 2px 12px rgba(41,182,246,.3);">₹</div>
            <h2 style="margin:0;font-family:'Syne',sans-serif;font-size:22px;">
                KhataKhat
                <span style="color:#3d5a72;font-size:14px;font-weight:400;">
                 | {t('Smart Recovery Desk','स्मार्ट वसूली डेस्क')}</span>
            </h2>
        </div>
        """, unsafe_allow_html=True)
    with n2:
        st.session_state.lang = st.radio(
            "lang2", ["English","हिंदी"], horizontal=True,
            label_visibility="collapsed", key="lang_main")
    with n3:
        st.markdown(f"""
        <div style="text-align:right;padding-top:6px;font-size:14px;color:#8eacc8;">
            {t('User:','यूज़र:')} <strong style="color:#f0f6ff;">{username}</strong>
        </div>""", unsafe_allow_html=True)
    with n4:
        if st.button(t("Log Out","लॉग आउट"), use_container_width=True):
            destroy_session(st.session_state.session_token)
            st.session_state.session_token = None
            st.session_state.user = None
            logger.info(f"User '{username}' logged out.")
            st.rerun()

    st.markdown("<hr class='kk' style='margin:8px 0 18px;'>", unsafe_allow_html=True)

    # ── UPI Banner ──
    upi_id = get_upi_id(username)
    if not upi_id:
        with st.expander(
            f"⚙️ {t('Set your UPI ID to enable payment links & QR codes','UPI ID सेट करें — पेमेंट लिंक और QR चालू करें')}",
            expanded=True
        ):
            cu1, cu2 = st.columns([3, 1])
            with cu1:
                new_upi = st.text_input(
                    "upi_banner", placeholder="yourname@okaxis",
                    label_visibility="collapsed")
            with cu2:
                if st.button(t("Save","सेव करें"), type="primary"):
                    if is_valid_upi(new_upi):
                        save_upi_id(username, new_upi.strip())
                        st.toast(t("UPI ID saved!","UPI ID सेव हो गई!"), icon="✅")
                        st.rerun()
                    else:
                        st.error(t("Invalid UPI ID format.","गलत UPI ID फॉर्मेट।"))
    else:
        st.markdown(f"""
        <div style="background:rgba(38,217,127,.07);border:1px solid rgba(38,217,127,.2);
                    border-radius:8px;padding:9px 16px;margin-bottom:14px;
                    display:flex;align-items:center;gap:10px;">
            <span>✅</span>
            <span style="color:#26d97f;font-size:13px;font-weight:500;">
                UPI: <strong>{upi_id}</strong> — {t('Payment links & QR codes active','पेमेंट लिंक और QR चालू')}</span>
            <span style="margin-left:auto;color:#3d5a72;font-size:11px;">
                {t('Edit in Settings','Settings में बदलें')}</span>
        </div>""", unsafe_allow_html=True)

    # ── Tabs ──
    is_admin = (username == "admin")
    tab_labels = [
        t("📊 Market Pulse","📊 बाज़ार"),
        t("💼 Recovery Desk","💼 वसूली डेस्क"),
        t("📈 Aging Report","📈 एजिंग रिपोर्ट"),
        t("⚙️ Settings","⚙️ सेटिंग्स"),
    ]
    if is_admin:
        tab_labels.append(t("🛡️ Admin Panel","🛡️ एडमिन"))
    tabs = st.tabs(tab_labels)

    # ════════════════════════════════════════════════
    #  TAB 0 — MARKET PULSE
    # ════════════════════════════════════════════════
    with tabs[0]:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px;">
            <span style="color:#8eacc8;font-size:13px;">
                {t('Industry & regional credit benchmarks','उद्योग और शहर के अनुसार क्रेडिट बेंचमार्क')}</span>
            <span class="badge-demo">⚠️ DEMO DATA</span>
        </div>""", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric(t("Total Market Credit","कुल बाज़ार क्रेडिट"),
                  f"₹{market_df['Amount'].sum():,.0f}")
        c2.metric(t("Capital at Risk","खतरे में पैसा"),
                  f"₹{market_df[market_df['Status']=='Delayed']['Amount'].sum():,.0f}")
        c3.metric(t("Avg. Delay","औसत देरी"),
                  f"{market_df['Days_Delayed'].mean():.1f} days")

        st.markdown("<br>", unsafe_allow_html=True)
        st1, st2, st3 = st.tabs([
            t("Industry","व्यापार"), t("Geography","शहर"), t("Risk","रिस्क")])

        with st1:
            d = market_df.groupby("Industry")["Credit_Days"].mean().reset_index()
            fig = apply_chart_layout(
                px.bar(d, x="Industry", y="Credit_Days",
                       color="Credit_Days", color_continuous_scale="Teal",
                       template="plotly_dark"),
                t("Credit Cycle by Industry (days)","उद्योग के अनुसार उधार के दिन"))
            st.plotly_chart(fig, use_container_width=True)
            jaankari_box(
                "FMCG clears within 15 days; Textile buyers stretch past 30.",
                "Mandate 50% upfront for all new Textile orders.",
                "FMCG 15 दिन में देता है, Textile 30+ दिन लेता है।",
                "टेक्सटाइल ऑर्डर पर 50% एडवांस लें।")

        with st2:
            d = market_df.groupby("City")["Days_Delayed"].mean().reset_index()
            fig = apply_chart_layout(
                px.bar(d, x="City", y="Days_Delayed",
                       color="Days_Delayed", color_continuous_scale="Reds",
                       template="plotly_dark"),
                t("Capital Delay by Region (days)","शहर के अनुसार देरी"))
            st.plotly_chart(fig, use_container_width=True)
            jaankari_box(
                "Surat extends cycles 20+ days. Delhi accounts settle fast.",
                "Redirect inventory to Delhi distributors.",
                "सूरत 20+ दिन रोकता है। दिल्ली तेज़ देता है।",
                "दिल्ली के ग्राहकों पर फोकस करें।")

        with st3:
            market_df["Risk"] = market_df["Days_Delayed"].apply(categorize)
            fig = apply_chart_layout(
                px.pie(market_df, names="Risk", hole=0.45, color="Risk",
                       color_discrete_map={"High":"#ef4444","Medium":"#f5a623","Low":"#26d97f"},
                       template="plotly_dark"),
                t("Portfolio Risk Distribution","पोर्टफोलियो रिस्क"))
            st.plotly_chart(fig, use_container_width=True)
            jaankari_box(
                "High-risk tranche signals elevated default probability.",
                "Freeze credit to High Risk profiles until 50% dues are cleared.",
                "हाई रिस्क अकाउंट डिफॉल्ट के खतरे में हैं।",
                "50% बकाया क्लियर होने तक उधार बंद करें।")

    # ════════════════════════════════════════════════
    #  TAB 1 — RECOVERY DESK
    # ════════════════════════════════════════════════
    with tabs[1]:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0d1e3522,#080f1e);border:1px dashed #1e3a5a;
                    border-radius:12px;padding:18px 22px;margin-bottom:20px;">
            <div style="font-size:13.5px;color:#8eacc8;margin-bottom:5px;">
                {t('Upload your receivables ledger (CSV)','अपना बकाया डेटा अपलोड करें (CSV)')}
                — <code style="background:#0f1f35;padding:1px 7px;border-radius:4px;
                               color:#29b6f6;">udhaar_data.csv</code></div>
            <div style="font-size:12px;color:#3d5a72;">
                {t('Required columns:','ज़रूरी कॉलम:')}
                Name · Amount · Paid Amount · Due Date · Industry · City</div>
        </div>""", unsafe_allow_html=True)

        file = st.file_uploader("", type=["csv"])

        if file:
            with st.spinner(t("Analysing your ledger…","लेजर विश्लेषण हो रहा है…")):
                df_raw = pd.read_csv(file, encoding="utf-8", encoding_errors="ignore")

            required_cols = ["Name","Amount","Paid Amount","Due Date","Industry","City"]
            if not all(c in df_raw.columns for c in required_cols):
                st.error(t(f"Schema error. Required: {', '.join(required_cols)}",
                           f"फ़ाइल गलत है। ज़रूरी: {', '.join(required_cols)}"))
                st.stop()

            df_raw["Due Date"] = pd.to_datetime(df_raw["Due Date"], errors="coerce")
            current_upi = get_upi_id(username)
            results = []

            for _, row in df_raw.iterrows():
                pending = row["Amount"] - row["Paid Amount"]
                if pending <= 0:
                    continue
                days     = calculate_days_overdue(row["Due Date"])
                cat      = categorize(days)
                risk     = calculate_risk(days, pending, row["Industry"], row["City"])
                credit   = calculate_credit_score(days, pending)
                prob     = predict_recovery_probability(days, pending, cat)
                expected = pending * prob
                bucket   = aging_bucket(days)
                disp_dt  = row["Due Date"].strftime("%Y-%m-%d") if pd.notnull(row["Due Date"]) else "N/A"
                msg      = generate_ai_message(row["Name"], pending, days, cat, row["Industry"], current_upi)
                results.append({
                    "Name": sanitize(str(row["Name"])),
                    "Amount": pending,
                    "Due Date": disp_dt,
                    "Industry": row["Industry"],
                    "City": row["City"],
                    "Days": days,
                    "Aging": bucket,
                    "Risk Score": round(risk, 2),
                    "Category": cat,
                    "Credit Score": credit,
                    "Recovery %": round(prob * 100, 1),
                    "Expected": round(expected, 0),
                    "Message": msg,
                })

            result_df = pd.DataFrame(results)

            if result_df.empty:
                st.markdown("""
                <div style="text-align:center;padding:44px;color:#3d5a72;">
                    <div style="font-size:52px;margin-bottom:12px;">📭</div>
                    <div style="font-size:17px;font-weight:700;color:#8eacc8;">Ledger is clear</div>
                    <div style="font-size:13px;margin-top:5px;">Zero outstanding balances. Great work!</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("<hr class='kk'>", unsafe_allow_html=True)
                st.subheader(t("Live Ledger Analysis","लाइव डेटा विश्लेषण"))
                st.dataframe(result_df.drop(columns=["Message"]), use_container_width=True)

                # #15 — Filtered CSV export
                col_exp1, col_exp2 = st.columns(2)
                with col_exp1:
                    csv_all = result_df.drop(columns=["Message"]).to_csv(index=False).encode()
                    st.download_button(
                        t("⬇️ Export All (CSV)","⬇️ सभी Export करें (CSV)"),
                        data=csv_all,
                        file_name=f"khatakhat_full_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv", use_container_width=True)
                with col_exp2:
                    high_df = result_df[result_df["Category"] == "High"].drop(columns=["Message"])
                    csv_high = high_df.to_csv(index=False).encode()
                    st.download_button(
                        t("⬇️ Export Critical Only (CSV)","⬇️ Critical ही Export करें"),
                        data=csv_high,
                        file_name=f"khatakhat_critical_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv", use_container_width=True)

                if st.button(t("💾 Save to Ledger","💾 लेजर में सेव करें")):
                    for _, row in result_df.iterrows():
                        cursor.execute("""
                        INSERT INTO transactions
                            (username,customer,amount,due_date,industry,city,status,aging_bucket)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (username, row["Name"], row["Amount"], row["Due Date"],
                         row["Industry"], row["City"], "Pending", row["Aging"]))
                    conn.commit()
                    st.toast(t("Ledger saved!","लेजर सेव हो गया!"), icon="✅")

                # ── KPIs ──
                st.markdown("<hr class='kk'>", unsafe_allow_html=True)
                st.subheader(t("Recovery Targets","रिकवरी टारगेट"))
                k1, k2, k3, k4 = st.columns(4)
                k1.metric(t("Gross Receivables","कुल बकाया"),
                          f"₹{result_df['Amount'].sum():,.0f}")
                k2.metric(t("Projected Inflow","अनुमानित वसूली"),
                          f"₹{result_df['Expected'].sum():,.0f}")
                k3.metric(t("Critical Accounts","खतरे वाले"),
                          len(result_df[result_df["Category"]=="High"]))
                k4.metric(t("Avg. Recovery Chance","औसत रिकवरी"),
                          f"{result_df['Recovery %'].mean():.1f}%")

                # ── Charts ──
                st.markdown("<br>", unsafe_allow_html=True)
                ch1, ch2 = st.columns(2)
                with ch1:
                    fig1 = apply_chart_layout(
                        px.bar(result_df, x="Name", y="Risk Score",
                               color="Risk Score", color_continuous_scale="Turbo",
                               template="plotly_dark"),
                        t("Default Probability Index","डिफॉल्ट रिस्क स्कोर"))
                    st.plotly_chart(fig1, use_container_width=True)
                    jaankari_box(
                        "Highest bars = highest default probability.",
                        "Call those accounts directly — skip automated channels.",
                        "ऊंचे बार = ज़्यादा खतरा।",
                        "इन्हें सीधे कॉल करें।")
                with ch2:
                    fig2 = apply_chart_layout(
                        px.pie(result_df, names="Category", hole=0.45,
                               color="Category",
                               color_discrete_map={"High":"#ef4444","Medium":"#f5a623","Low":"#26d97f"},
                               template="plotly_dark"),
                        t("Account Risk Segmentation","अकाउंट रिस्क वितरण"))
                    st.plotly_chart(fig2, use_container_width=True)
                    jaankari_box(
                        "Proportional exposure across risk tiers.",
                        "Automate Low tier; reserve time for High.",
                        "रिस्क के हिसाब से बंटवारा।",
                        "Low के लिए ऑटो, High के लिए मैन्युअल।")

                # Liquidity curve
                rdf = result_df.sort_values("Expected", ascending=False).copy()
                rdf["Idx"] = range(1, len(rdf)+1)
                rdf["Cum"] = rdf["Expected"].cumsum()
                fig3 = apply_chart_layout(
                    px.area(rdf, x="Idx", y="Cum",
                            template="plotly_dark",
                            color_discrete_sequence=["#29b6f6"]),
                    t("Liquidity Projection Curve","कैश फ्लो प्रोजेक्शन"))
                fig3.update_traces(fillcolor="rgba(41,182,246,0.10)")
                st.plotly_chart(fig3, use_container_width=True)

                # ── #14 BULK WhatsApp ──
                st.markdown("<hr class='kk'>", unsafe_allow_html=True)
                st.subheader(t("WhatsApp Recovery Hub","व्हाट्सएप रिकवरी हब"))

                if not current_upi:
                    st.warning(t("⚠️ UPI ID not set — QR codes unavailable. Add it in Settings.",
                                 "⚠️ UPI ID नहीं है — QR कोड नहीं बनेगा। Settings में डालें।"))

                # Bulk dispatch
                low_risk = result_df[result_df["Category"]=="Low"]
                if len(low_risk) > 0:
                    with st.expander(t(
                        f"📤 Bulk Send to all Low-Risk accounts ({len(low_risk)} customers)",
                        f"📤 सभी Low-Risk ग्राहकों को भेजें ({len(low_risk)} ग्राहक)"
                    )):
                        for _, lr in low_risk.iterrows():
                            enc = urllib.parse.quote(lr["Message"])
                            st.markdown(f"""
                            <div style="display:flex;justify-content:space-between;
                                        align-items:center;padding:8px 0;
                                        border-bottom:1px solid #1e3a5a;">
                                <span style="color:#f0f6ff;font-size:13px;font-weight:600;">
                                    {lr['Name']}</span>
                                <a href="https://wa.me/?text={enc}" target="_blank"
                                   style="background:#25D366;color:#fff;font-size:11px;
                                          font-weight:700;padding:4px 12px;border-radius:6px;
                                          text-decoration:none;">Open WhatsApp</a>
                            </div>""", unsafe_allow_html=True)

                # Individual customer
                selected = st.selectbox(
                    t("Select Customer Profile:","ग्राहक चुनें:"),
                    result_df["Name"].tolist())

                if selected:
                    ci = result_df[result_df["Name"]==selected].iloc[0]
                    bc = {"High":"#ef4444","Medium":"#f5a623","Low":"#26d97f"}.get(ci["Category"],"#8eacc8")

                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#0d2745,#132033);
                                padding:20px;border-radius:12px;border:1px solid #1e3a5a;
                                margin-bottom:16px;">
                        <div style="display:flex;justify-content:space-between;
                                    align-items:center;margin-bottom:12px;">
                            <span style="color:#8eacc8;font-size:11px;text-transform:uppercase;
                                         letter-spacing:1.2px;font-weight:700;">
                                {t('Generated Recovery Message','तैयार किया गया मैसेज')}</span>
                            <span style="background:{bc}18;border:1px solid {bc}40;
                                         color:{bc};font-size:10px;font-weight:700;
                                         padding:2px 10px;border-radius:20px;">
                                {ci['Category'].upper()} RISK</span>
                        </div>
                        <p style="color:#f0f6ff;font-size:14px;line-height:1.65;margin:0;">
                            {ci['Message']}</p>
                    </div>""", unsafe_allow_html=True)

                    b1, b2, b3 = st.columns(3)
                    with b1:
                        phone = st.text_input(
                            t("WhatsApp Number (91xxxxxxxxxx)","व्हाट्सएप नंबर"),
                            value="919876543210")
                        clean_ph = phone.replace("+","").replace(" ","").strip()
                        enc_msg  = urllib.parse.quote(ci["Message"])
                        st.link_button(
                            t("📲 Send via WhatsApp","📲 WhatsApp पर भेजें"),
                            f"https://wa.me/{clean_ph}?text={enc_msg}",
                            use_container_width=True)

                        if st.button(t("📝 Log Transmission","📝 लॉग करें"),
                                     use_container_width=True):
                            cursor.execute(
                                "INSERT INTO communications (username,customer,message_enc,timestamp,status) VALUES (?,?,?,?,?)",
                                (username, ci["Name"], encrypt(ci["Message"]),
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Dispatched"))
                            conn.commit()
                            st.toast(t("✅ Logged.","✅ लॉग हो गया।"), icon="✅")

                    with b2:
                        # #18 — Email reminder
                        cust_email = st.text_input(
                            t("Customer Email (optional)","ग्राहक ईमेल (वैकल्पिक)"),
                            placeholder="customer@email.com")
                        if st.button(t("📧 Send Email Reminder","📧 ईमेल भेजें"),
                                     use_container_width=True):
                            if cust_email and "@" in cust_email:
                                with st.spinner("Sending…"):
                                    ok = send_email_reminder(
                                        cust_email, ci["Name"],
                                        ci["Amount"], ci["Message"])
                                if ok:
                                    st.toast(t("Email sent!","ईमेल भेजा गया!"), icon="📧")
                                else:
                                    st.warning(t("SMTP not configured. Set SMTP_USER & SMTP_PASSWORD in secrets.",
                                                 "SMTP सेट नहीं है। Secrets में डालें।"))
                            else:
                                st.error(t("Enter a valid email.","सही ईमेल डालें।"))

                        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                        if st.button(t("✅ Mark as Paid","✅ पैसा मिल गया"),
                                     type="primary", use_container_width=True):
                            cursor.execute(
                                "UPDATE transactions SET status='Recovered' WHERE customer=? AND username=? AND amount=? AND status='Pending'",
                                (ci["Name"], username, ci["Amount"]))
                            conn.commit()
                            st.toast(f"✅ {ci['Name']} marked recovered.", icon="💰")

                    with b3:
                        # #7 + #8 — QR CODE
                        if current_upi:
                            st.markdown(f"""
                            <div style="font-size:11px;color:#8eacc8;text-transform:uppercase;
                                        letter-spacing:1px;font-weight:700;margin-bottom:8px;">
                                📱 {t('UPI QR Code','UPI QR कोड')}</div>""",
                                unsafe_allow_html=True)
                            with st.spinner("Generating QR…"):
                                qr_bytes = generate_upi_qr(current_upi, ci["Amount"], ci["Name"])
                            st.image(qr_bytes, width=180)
                            st.download_button(
                                t("⬇️ Download QR","⬇️ QR डाउनलोड करें"),
                                data=qr_bytes,
                                file_name=f"QR_{ci['Name'].replace(' ','_')}.png",
                                mime="image/png",
                                use_container_width=True)
                        else:
                            st.markdown("""
                            <div style="background:#0f1f35;border:1px dashed #1e3a5a;
                                        border-radius:10px;padding:20px;text-align:center;
                                        color:#3d5a72;font-size:12px;">
                                Set UPI ID in Settings to generate QR</div>""",
                                unsafe_allow_html=True)

                # ── Recovery History ──
                st.markdown("<hr class='kk'>", unsafe_allow_html=True)
                st.subheader(t("Recovery History","रिकवरी इतिहास"))

                # #17 — Recovery trend chart
                hist_df = safe_read_sql(
                    "SELECT customer,amount,due_date,status,created_at FROM transactions WHERE username=?",
                    conn, params=(username,))

                if not hist_df.empty:
                    # Trend
                    hist_df["created_at"] = pd.to_datetime(hist_df["created_at"], errors="coerce")
                    trend_data = hist_df.groupby([hist_df["created_at"].dt.date, "status"]
                                                 ).size().reset_index(name="count")
                    if not trend_data.empty and "created_at" in trend_data.columns:
                        fig_trend = apply_chart_layout(
                            px.line(trend_data, x="created_at", y="count",
                                    color="status",
                                    color_discrete_map={"Pending":"#f5a623","Recovered":"#26d97f"},
                                    template="plotly_dark"),
                            t("Recovery Trend","रिकवरी ट्रेंड"))
                        st.plotly_chart(fig_trend, use_container_width=True)

                    st.dataframe(hist_df, use_container_width=True)
                else:
                    st.markdown("""
                    <div style="text-align:center;padding:28px;color:#3d5a72;">
                        <div style="font-size:36px;">📭</div>
                        <div style="font-size:14px;color:#8eacc8;margin-top:8px;">
                            No records yet. Save your ledger above.</div>
                    </div>""", unsafe_allow_html=True)

                # ── PDF ──
                st.markdown("<hr class='kk'>", unsafe_allow_html=True)
                st.subheader(t("Download Recovery Report","रिकवरी रिपोर्ट"))
                pdf_bytes = generate_pdf_report(result_df, current_upi)
                st.download_button(
                    t("📄 Download PDF Report","📄 PDF रिपोर्ट डाउनलोड करें"),
                    data=pdf_bytes,
                    file_name=f"KhataKhat_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True)

    # ════════════════════════════════════════════════
    #  TAB 2 — AGING REPORT  (#16)
    # ════════════════════════════════════════════════
    with tabs[2]:
        st.subheader(t("Receivables Aging Report","बकाया एजिंग रिपोर्ट"))
        st.markdown(f"""
        <p style="color:#8eacc8;font-size:13px;margin-top:-6px;">
            {t('Standard aging buckets: industry-accepted view of overdue risk.',
               'उद्योग-मानक एजिंग बकेट: बकाया रिस्क का स्पष्ट दृश्य।')}</p>""",
            unsafe_allow_html=True)

        aging_history = safe_read_sql(
            "SELECT customer,amount,aging_bucket,status,created_at FROM transactions WHERE username=?",
            conn, params=(username,))

        if aging_history.empty:
            st.markdown("""
            <div style="text-align:center;padding:40px;color:#3d5a72;">
                <div style="font-size:44px;">📊</div>
                <div style="font-size:15px;color:#8eacc8;margin-top:10px;">
                    Upload and save a ledger in Recovery Desk to populate aging data.</div>
            </div>""", unsafe_allow_html=True)
        else:
            aging_history["amount"] = pd.to_numeric(aging_history["amount"], errors="coerce")
            bucket_order = ["0–30 days","31–60 days","61–90 days","90+ days"]

            a1, a2, a3, a4 = st.columns(4)
            cols_map = [a1, a2, a3, a4]
            for i, bkt in enumerate(bucket_order):
                grp = aging_history[aging_history["aging_bucket"]==bkt]
                cols_map[i].metric(bkt, f"₹{grp['amount'].sum():,.0f}",
                                   f"{len(grp)} accounts")

            st.markdown("<br>", unsafe_allow_html=True)
            bucket_summary = (aging_history.groupby("aging_bucket")["amount"]
                              .sum().reset_index())
            bucket_summary["aging_bucket"] = pd.Categorical(
                bucket_summary["aging_bucket"], categories=bucket_order, ordered=True)
            bucket_summary = bucket_summary.sort_values("aging_bucket")

            fig_aging = apply_chart_layout(
                px.bar(bucket_summary, x="aging_bucket", y="amount",
                       color="amount",
                       color_continuous_scale=["#26d97f","#f5a623","#ef4444","#7c1d1d"],
                       template="plotly_dark"),
                t("Aging Bucket Analysis","एजिंग बकेट विश्लेषण"))
            st.plotly_chart(fig_aging, use_container_width=True)

            jaankari_box(
                "90+ day balances have the lowest recovery probability — they require immediate personal escalation.",
                "Assign a dedicated collector to all 90+ day accounts this week.",
                "90+ दिन वाले बकाये की वसूली सबसे मुश्किल है।",
                "इस हफ्ते 90+ दिन वाले हर ग्राहक को खुद कॉल करें।")

            st.dataframe(aging_history, use_container_width=True)

    # ════════════════════════════════════════════════
    #  TAB 3 — SETTINGS
    # ════════════════════════════════════════════════
    with tabs[3]:
        st.subheader(t("Account Settings","खाता सेटिंग्स"))
        st.markdown("<br>", unsafe_allow_html=True)

        s1, s2 = st.columns(2)
        with s1:
            st.markdown(f"""
            <div style="font-size:11px;color:#8eacc8;text-transform:uppercase;
                        letter-spacing:1.2px;font-weight:700;margin-bottom:8px;">
                {t('UPI Payment ID','UPI पेमेंट ID')}</div>""",
                unsafe_allow_html=True)
            cur_upi = get_upi_id(username)
            upi_inp = st.text_input("upi_settings", value=cur_upi,
                                    placeholder="yourname@okaxis",
                                    label_visibility="collapsed")
            if st.button(t("Update UPI ID","UPI ID अपडेट करें"), type="primary"):
                if is_valid_upi(upi_inp):
                    save_upi_id(username, upi_inp.strip())
                    st.toast(t("UPI ID updated!","UPI ID अपडेट हो गई!"), icon="✅")
                    st.rerun()
                else:
                    st.error(t("Invalid UPI ID (e.g. name@okaxis).","सही UPI ID डालें।"))

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="font-size:11px;color:#8eacc8;text-transform:uppercase;
                        letter-spacing:1.2px;font-weight:700;margin-bottom:8px;">
                {t('Email Address (for outbound reminders)','ईमेल (रिमाइंडर के लिए)')}</div>""",
                unsafe_allow_html=True)
            cur_email = get_email(username)
            email_inp = st.text_input("email_settings", value=cur_email,
                                      placeholder="you@company.com",
                                      label_visibility="collapsed")
            if st.button(t("Update Email","ईमेल अपडेट करें")):
                if "@" in email_inp and "." in email_inp:
                    save_email(username, email_inp.strip())
                    st.toast(t("Email saved!","ईमेल सेव हो गई!"), icon="✅")
                    st.rerun()
                else:
                    st.error(t("Enter a valid email address.","सही ईमेल डालें।"))

        with s2:
            st.markdown(f"""
            <div style="background:#0f1f35;border:1px solid #1e3a5a;border-radius:12px;
                        padding:22px 24px;">
                <div style="font-size:11px;color:#3d5a72;text-transform:uppercase;
                            letter-spacing:1px;margin-bottom:16px;font-weight:700;">
                    Account Info</div>
                <div style="color:#8eacc8;font-size:13.5px;margin-bottom:10px;">
                    Username: <strong style="color:#f0f6ff;">{username}</strong></div>
                <div style="color:#8eacc8;font-size:13.5px;margin-bottom:10px;">
                    Session timeout:
                    <strong style="color:#f0f6ff;">{SESSION_TIMEOUT_MINUTES} minutes</strong></div>
                <div style="color:#8eacc8;font-size:13.5px;margin-bottom:10px;">
                    Encryption: <span class="badge-ok">Fernet AES-128 Active</span></div>
                <div style="color:#8eacc8;font-size:13.5px;">
                    Passwords: <span class="badge-ok">bcrypt / rounds=12</span></div>
            </div>""", unsafe_allow_html=True)

            # Security summary
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#0f1f35;border:1px solid #1e3a5a;border-radius:12px;
                        padding:22px 24px;">
                <div style="font-size:11px;color:#3d5a72;text-transform:uppercase;
                            letter-spacing:1px;margin-bottom:14px;font-weight:700;">
                    🔒 Security Status</div>
                <div style="display:flex;flex-direction:column;gap:9px;font-size:13px;">
                    <div style="display:flex;justify-content:space-between;">
                        <span style="color:#8eacc8;">Login rate-limiting</span>
                        <span class="badge-ok">Active · {MAX_LOGIN_ATTEMPTS} attempts</span></div>
                    <div style="display:flex;justify-content:space-between;">
                        <span style="color:#8eacc8;">Account lockout</span>
                        <span class="badge-ok">Active · {LOCKOUT_MINUTES} min</span></div>
                    <div style="display:flex;justify-content:space-between;">
                        <span style="color:#8eacc8;">Session tokens</span>
                        <span class="badge-ok">Active · {SESSION_TIMEOUT_MINUTES} min expiry</span></div>
                    <div style="display:flex;justify-content:space-between;">
                        <span style="color:#8eacc8;">DB encryption (UPI/email)</span>
                        <span class="badge-ok">Fernet Active</span></div>
                    <div style="display:flex;justify-content:space-between;">
                        <span style="color:#8eacc8;">Input sanitization</span>
                        <span class="badge-ok">Active</span></div>
                </div>
            </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════
    #  TAB 4 — ADMIN PANEL  (admin only)
    # ════════════════════════════════════════════════
    if is_admin:
        with tabs[4]:
            st.header(t("Admin Panel","एडमिन पैनल"))

            at1, at2, at3 = st.tabs([
                t("Transmission Logs","संचार लॉग"),
                t("Transaction Ledger","ट्रांज़ैक्शन"),
                t("User Management","यूज़र्स"),
            ])

            with at1:
                comm = safe_read_sql(
                    "SELECT id,username,customer,timestamp,status FROM communications ORDER BY id DESC",
                    conn)
                if not comm.empty:
                    st.dataframe(comm, use_container_width=True)
                else:
                    st.markdown("<div style='color:#3d5a72;padding:20px;text-align:center;'>📭 No logs yet.</div>",
                                unsafe_allow_html=True)

            with at2:
                tx = safe_read_sql("SELECT * FROM transactions ORDER BY id DESC", conn)
                if not tx.empty:
                    st.dataframe(tx, use_container_width=True)
                    tx_csv = tx.to_csv(index=False).encode()
                    st.download_button("⬇️ Export All Transactions",
                                       tx_csv, "all_transactions.csv", "text/csv")
                else:
                    st.markdown("<div style='color:#3d5a72;padding:20px;text-align:center;'>📭 Empty.</div>",
                                unsafe_allow_html=True)

            with at3:
                users = safe_read_sql(
                    "SELECT username,failed_attempts,locked_until,created_at FROM users",
                    conn)
                if not users.empty:
                    st.dataframe(users, use_container_width=True)
                # Active sessions
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:12px;color:#8eacc8;text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:8px;'>Active Sessions</div>", unsafe_allow_html=True)
                sessions = safe_read_sql(
                    "SELECT username,created_at,expires_at FROM sessions ORDER BY created_at DESC",
                    conn)
                if not sessions.empty:
                    st.dataframe(sessions, use_container_width=True)
                if st.button("🗑️ Purge Expired Sessions", type="primary"):
                    cursor.execute("DELETE FROM sessions WHERE expires_at < ?",
                                   (datetime.utcnow().isoformat(),))
                    conn.commit()
                    st.toast("Expired sessions purged.", icon="🗑️")

# -----------------------------------------------------------------------
# FOOTER
# -----------------------------------------------------------------------
st.markdown("""
<div style="text-align:center;margin-top:64px;padding:20px 0;
            color:#1e3a5a;font-size:12px;font-weight:600;
            border-top:1px solid #0f1f35;letter-spacing:.4px;">
    © 2025 KhataKhat · Built by Ebin Davis · All rights reserved ·
    <span style="color:#132033;">bcrypt · Fernet · Session-Secured</span>
</div>""", unsafe_allow_html=True)
