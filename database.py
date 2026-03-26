import pandas as pd
import os
from sqlalchemy import create_engine, text

SYSTEM_FILE = "system_state.txt"

DATABASE_URL = "postgresql://postgres.apvevjmtittiutcizgwt:Mamaty12..a@aws-1-eu-west-3.pooler.supabase.com:6543/postgres"

engine = create_engine(DATABASE_URL)

# =========================
# 🔌 CONNECTION
# =========================
def get_connection():
    return engine.connect()

# =========================
# 👤 USERS
# =========================

def load_users():
    return pd.read_sql("SELECT * FROM users", engine)

def save_user(login, password, role, name, lastname, phone=None, subject=None):
    query = text("""
        INSERT INTO users (login, password, role, name, lastname, phone, subject, status)
        VALUES (:login,:password,:role,:name,:lastname,:phone,:subject,'active')
    """)

    with engine.connect() as conn:
        conn.execute(query, {
            "login": login,
            "password": password,
            "role": role,
            "name": name,
            "lastname": lastname,
            "phone": phone,
            "subject": subject
        })
        conn.commit()

# =========================
# 🆕 👨‍👩‍👧‍👦 CREATE PARENT ACCOUNT
# =========================
def create_parent_account():
    query = text("""
        INSERT INTO users (login, password, role, name, lastname, status)
        VALUES ('parent@test', '1234', 'parents', 'Parent', 'User', 'active')
    """)

    with engine.connect() as conn:
        conn.execute(query)
        conn.commit()

# =========================
# 🔌 SYSTEM STATUS
# =========================

def get_system_status():
    if not os.path.exists(SYSTEM_FILE):
        return "on"
    with open(SYSTEM_FILE, "r") as f:
        return f.read().strip()

def set_system_status(status):
    with open(SYSTEM_FILE, "w") as f:
        f.write(status)