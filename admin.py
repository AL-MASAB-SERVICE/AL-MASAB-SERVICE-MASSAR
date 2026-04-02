import streamlit as st
import random
import string
import pandas as pd
from database import get_connection, get_system_status, set_system_status
from sqlalchemy import text
from datetime import datetime
import re
import hashlib
import secrets
from io import BytesIO
import plotly.graph_objects as go

# =========================
# 🔐 Hashing + Salt
# =========================
def hash_password(password: str) -> tuple:
    """توليد Salt + Hash لكلمة المرور"""
    salt = secrets.token_hex(32)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt, hash_obj.hex()

def verify_password(password: str, salt: str, hash_value: str) -> bool:
    """التحقق من صحة كلمة المرور"""
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hash_obj.hex() == hash_value

# =========================
# 📝 Audit Log
# =========================
def log_audit(action: str, target_type: str = None, target_id: str = None, 
              target_name: str = None, details: str = None):
    """تسجيل كل عملية في سجل التدقيق"""
    try:
        conn = get_connection()
        conn.execute(text("""
            INSERT INTO audit_log (admin_login, admin_name, action, target_type, target_id, target_name, details, ip_address, user_agent, created_at)
            VALUES (:admin_login, :admin_name, :action, :target_type, :target_id, :target_name, :details, :ip, :ua, NOW())
        """), {
            "admin_login": st.session_state.get("login_user", "unknown"),
            "admin_name": st.session_state.get("name", "unknown"),
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "target_name": target_name,
            "details": details,
            "ip": st.context.headers.get("X-Forwarded-For", "unknown") if hasattr(st, 'context') else "unknown",
            "ua": st.context.headers.get("User-Agent", "unknown") if hasattr(st, 'context') else "unknown"
        })
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"خطأ في تسجيل التدقيق: {e}")

# =========================
# 🔐 التحقق من الصلاحيات (RBAC)
# =========================
def has_permission(permission: str) -> bool:
    """التحقق من صلاحية المستخدم"""
    if "user_permissions" not in st.session_state:
        conn = get_connection()
        role = st.session_state.get("role", "viewer")
        perms = conn.execute(text("""
            SELECT permissions FROM user_permissions WHERE role = :role
        """), {"role": role}).fetchone()
        conn.close()
        if perms:
            st.session_state.user_permissions = perms[0]
        else:
            st.session_state.user_permissions = ['view_users']
    
    perms = st.session_state.user_permissions
    return '*' in perms or permission in perms

# =========================
# 🔐 توليد معلومات
# =========================
def generate_password():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))

def generate_login(name, lastname):
    base = f"{name.lower()}{lastname.lower()}"
    base = re.sub(r'[^a-z]', '', base)
    return f"{base}@taalim.ma"

# =========================
# 🎨 Status Color
# =========================
def format_status(status):
    if status == "done":
        return "✅ تم المعالجة"
    elif status == "rejected":
        return "❌ مرفوض"
    elif status == "pending":
        return "⏳ قيد الانتظار"
    else:
        return status

# =========================
# 🔍 دالة البحث الذكية
# =========================
def normalize_text(text):
    if text is None:
        return ""
    text = str(text).lower().strip()
    text = re.sub(r'[ًٌٍَُِّْ]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text

# =========================
# 🌓 Dark/Light Mode
# =========================
def toggle_theme():
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🌓" if st.session_state.theme == "light" else "☀️"):
            st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
            st.rerun()
    
    if st.session_state.theme == "dark":
        st.markdown("""
        <style>
            .stApp, .main, .stSidebar, .stMarkdown, .stDataFrame {
                background-color: #0e1117 !important;
                color: #ffffff !important;
            }
            .stTextInput>div>div>input, .stSelectbox>div>div, .stTextArea>div>textarea {
                background-color: #1e1e2e !important;
                color: #ffffff !important;
                border: 1px solid #444 !important;
            }
            div.stButton > button {
                background: linear-gradient(45deg, #11998e, #38ef7d) !important;
                color: white !important;
            }
            .stDataFrame {
                background-color: #1e1e2e !important;
            }
        </style>
        """, unsafe_allow_html=True)

# =========================
# 📊 Dashboard الرئيسي
# =========================
def show_dashboard():
    st.markdown("""
    <style>
        .dashboard-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            padding: 20px;
            color: white;
            text-align: center;
            margin: 10px;
        }
        .dashboard-number {
            font-size: 36px;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center;'>🏢 لوحة التحكم الرئيسية</h1>", unsafe_allow_html=True)
    
    conn = get_connection()
    
    # إحصائيات سريعة
    users_count = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
    active_users = conn.execute(text("SELECT COUNT(*) FROM users WHERE status='active'")).fetchone()[0]
    stopped_users = conn.execute(text("SELECT COUNT(*) FROM users WHERE status='stopped'")).fetchone()[0]
    pending_recl = conn.execute(text("SELECT COUNT(*) FROM reclamations_extended WHERE status='pending'")).fetchone()[0]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class='dashboard-card'>
            <div>👥 إجمالي المستخدمين</div>
            <div class='dashboard-number'>{users_count}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class='dashboard-card' style='background: linear-gradient(135deg, #11998e, #38ef7d);'>
            <div>🟢 المستخدمين النشطين</div>
            <div class='dashboard-number'>{active_users}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class='dashboard-card' style='background: linear-gradient(135deg, #eb3349, #f45c43);'>
            <div>🔴 المستخدمين الموقوفين</div>
            <div class='dashboard-number'>{stopped_users}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class='dashboard-card' style='background: linear-gradient(135deg, #f093fb, #f5576c);'>
            <div>📩 الشكايات المعلقة</div>
            <div class='dashboard-number'>{pending_recl}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # الرسم البياني لعدد المستخدمين
    users_by_role = pd.read_sql("""
        SELECT role, COUNT(*) as count FROM users GROUP BY role
    """, conn)
    
    fig = go.Figure(data=[go.Pie(labels=users_by_role['role'], values=users_by_role['count'], hole=.3)])
    fig.update_layout(title="توزيع المستخدمين حسب الدور", template="plotly_dark" if st.session_state.get("theme") == "dark" else "plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    
    # آخر 10 عمليات في سجل التدقيق
    st.markdown("### 📋 آخر العمليات المسجلة")
    audit = pd.read_sql("""
        SELECT admin_name, action, target_name, created_at 
        FROM audit_log ORDER BY id DESC LIMIT 10
    """, conn)
    conn.close()
    
    if not audit.empty:
        st.dataframe(audit, use_container_width=True)
    else:
        st.info("لا توجد عمليات مسجلة بعد")

# =========================
# 🧑‍🔧 لوحة admin الرئيسية
# =========================
def admin_panel():
    # تفعيل الثيم
    toggle_theme()
    
    # قائمة الصلاحيات الديناميكية
    menu = ["🏠 Dashboard"]
    
    if has_permission("create_user"):
        menu.append("➕ إنشاء حساب")
    if has_permission("create_reclamation"):
        menu.append("📝 إنشاء شكاية جديدة")
    if has_permission("view_users"):
        menu.append("📋 إدارة الحسابات")
    if has_permission("block_user"):
        menu.append("🚫 توقيف حساب")
    if has_permission("unblock_user"):
        menu.append("🔄 إعادة تفعيل حساب")
    if has_permission("change_password"):
        menu.append("🔑 تغيير كلمة المرور")
    if has_permission("delete_user"):
        menu.append("🗑️ حذف حساب")
    if has_permission("view_reclamations"):
        menu.append("📩 الشكايات")
    if has_permission("manage_system"):
        menu.append("🔌 التحكم في النظام")
    if has_permission("view_audit_log"):
        menu.append("📊 سجل التدقيق")
    if has_permission("manage_admins"):
        menu.append("👑 إدارة الصلاحيات")
    
    choice = st.sidebar.selectbox("القائمة الرئيسية", menu)
    
    # عرض اسم المستخدم والصلاحية
    st.sidebar.divider()
    st.sidebar.markdown(f"""
    ### 👤 {st.session_state.get('name', 'Admin')}
    *الدور:* {st.session_state.get('role', 'admin')}
    *الصلاحية:* {"🟢 Super Admin" if '*' in st.session_state.get('user_permissions', []) else "🟡 Admin"}
    """)
    
    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.clear()
        st.rerun()
    
    # =========================
    # 🏠 Dashboard
    # =========================
    if choice == "🏠 Dashboard":
        show_dashboard()
    
    # =========================
    # ➕ إنشاء حساب
    # =========================
    elif choice == "➕ إنشاء حساب":
        st.subheader("➕ إنشاء حساب جديد")
        
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("الإسم")
                lastname = st.text_input("النسب")
                phone = st.text_input("الهاتف")
            with col2:
                subject = st.text_input("المادة")
                role = st.selectbox("الدور", ["prof", "surveillant", "directeur", "parents", "admin", "tech_support", "viewer"])
            
            admin_name = st.session_state.get("name", "admin")
            
            if st.form_submit_button("إنشاء حساب"):
                if name and lastname:
                    login = generate_login(name, lastname)
                    password = generate_password()
                    salt, hash_val = hash_password(password)
                    
                    conn = get_connection()
                    conn.execute(text("""
                        INSERT INTO users (login, password_hash, password_salt, role, name, lastname, phone, subject, status, created_by, created_at)
                        VALUES (:login, :hash, :salt, :role, :name, :lastname, :phone, :subject, 'active', :created_by, NOW())
                    """), {
                        "login": login,
                        "hash": hash_val,
                        "salt": salt,
                        "role": role,
                        "name": name,
                        "lastname": lastname,
                        "phone": phone,
                        "subject": subject,
                        "created_by": admin_name
                    })
                    conn.commit()
                    conn.close()
                    
                    # تسجيل في Audit Log
                    log_audit("create_user", "user", login, f"{name} {lastname}", f"تم إنشاء حساب بدور {role}")
                    
                    st.success(f"✅ تم إنشاء الحساب بنجاح")
                    st.info(f"*Login:* {login}")
                    st.warning(f"*Password:* {password}")
                else:
                    st.error("❌ الإسم والنسب مطلوبان")
    
    # =========================
    # 📝 إنشاء شكاية جديدة
    # =========================
    elif choice == "📝 إنشاء شكاية جديدة":
        st.subheader("📝 إنشاء شكاية جديدة")
        
        with st.form("reclamation_form"):
            st.markdown("### 📞 معلومات المتصل")
            col1, col2 = st.columns(2)
            with col1:
                caller_name = st.text_input("إسم المتصل")
            with col2:
                caller_lastname = st.text_input("نسب المتصل")
            
            st.markdown("### 👤 معلومات صاحب الحساب")
            col3, col4 = st.columns(2)
            with col3:
                account_name = st.text_input("إسم صاحب الحساب")
            with col4:
                account_lastname = st.text_input("نسب صاحب الحساب")
            
            if account_name and account_lastname:
                conn = get_connection()
                user_info = conn.execute(text("""
                    SELECT login, created_at, phone, status, name, lastname
                    FROM users 
                    WHERE name ILIKE :name AND lastname ILIKE :lastname
                """), {"name": f"%{account_name}%", "lastname": f"%{account_lastname}%"}).fetchone()
                conn.close()
                
                if user_info:
                    st.success("✅ تم العثور على الحساب")
                    st.markdown(f"""
                    - *إسم الحساب:* {user_info[0]}
                    - *تاريخ الإنشاء:* {user_info[1].strftime('%Y-%m-%d') if user_info[1] else 'غير معروف'}
                    - *رقم التواصل:* {user_info[2] if user_info[2] else 'غير مسجل'}
                    - *حالة الحساب:* {"🟢 نشط" if user_info[3] == 'active' else "🔴 موقوف"}
                    """)
                    account_login = user_info[0]
                else:
                    st.warning("⚠️ لم يتم العثور على حساب بهذه المعلومات")
                    account_login = None
            else:
                account_login = None
            
            st.markdown("### 📝 معلومات الشكاية")
            reason = st.text_area("سبب الشكاية", height=150)
            
            if st.form_submit_button("📤 إرسال الشكاية"):
                if not caller_name or not caller_lastname or not account_name or not account_lastname or not reason:
                    st.error("❌ جميع الحقول مطلوبة")
                elif not account_login:
                    st.error("❌ لم يتم العثور على حساب صاحب الحساب")
                else:
                    conn = get_connection()
                    conn.execute(text("""
                        INSERT INTO reclamations_extended 
                        (caller_name, caller_lastname, account_name, account_lastname, account_login, reason, created_at, created_time, status)
                        VALUES (:caller_name, :caller_lastname, :account_name, :account_lastname, :account_login, :reason, CURRENT_DATE, CURRENT_TIME, 'pending')
                    """), {
                        "caller_name": caller_name,
                        "caller_lastname": caller_lastname,
                        "account_name": account_name,
                        "account_lastname": account_lastname,
                        "account_login": account_login,
                        "reason": reason
                    })
                    conn.commit()
                    conn.close()
                    
                    log_audit("create_reclamation", "reclamation", account_login, f"{account_name} {account_lastname}", reason)
                    st.success("✅ تم حفظ الشكاية بنجاح")
                    st.balloons()
    
    # =========================
    # 📋 إدارة الحسابات
    # =========================
    elif choice == "📋 إدارة الحسابات":
        st.subheader("📋 إدارة الحسابات")
        
        col1, col2 = st.columns(2)
        with col1:
            search_name = st.text_input("🔍 إسم المستخدم")
        with col2:
            search_lastname = st.text_input("🔍 نسب المستخدم")
        
        if st.button("🔍 بحث", use_container_width=True):
            conn = get_connection()
            query = """
                SELECT u.*, 
                       (SELECT COUNT(*) FROM reclamations_extended WHERE account_login = u.login) as recl_count
                FROM users u
                WHERE 1=1
            """
            params = {}
            if search_name:
                query += " AND u.name ILIKE :name"
                params["name"] = f"%{search_name}%"
            if search_lastname:
                query += " AND u.lastname ILIKE :lastname"
                params["lastname"] = f"%{search_lastname}%"
            
            users = pd.read_sql(query, conn, params=params)
            conn.close()
            
            if not users.empty:
                for _, user in users.iterrows():
                    with st.expander(f"👤 {user['name']} {user['lastname']} - {user['login']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"""
                            - *الدور:* {user['role']}
                            - *الهاتف:* {user['phone'] if user['phone'] else 'غير مسجل'}
                            - *المادة:* {user['subject'] if user['subject'] else '-'}
                            - *الحالة:* {"🟢 نشط" if user['status'] == 'active' else "🔴 موقوف"}
                            - *تاريخ الإنشاء:* {user['created_at'].strftime('%Y-%m-%d %H:%M') if user['created_at'] else 'غير معروف'}
                            - *أنشأ الحساب:* {user['created_by'] if user['created_by'] else 'غير معروف'}
                            - *عدد مرات الدخول:* {user['login_count'] if user['login_count'] else 0}
                            """)
                        with col2:
                            if user['status'] == 'stopped' and has_permission("unblock_user"):
                                if st.button(f"✅ إعادة تفعيل", key=f"unblock_{user['login']}"):
                                    conn = get_connection()
                                    conn.execute(text("""
                                        UPDATE users SET status='active', blocked_at=NULL, blocked_reason=NULL, blocked_by=NULL, failed_login_attempts=0
                                        WHERE login=:login
                                    """), {"login": user['login']})
                                    conn.commit()
                                    conn.close()
                                    log_audit("unblock_user", "user", user['login'], f"{user['name']} {user['lastname']}", "تم إعادة التفعيل")
                                    st.success("✅ تم إعادة التفعيل")
                                    st.rerun()
                            elif user['status'] == 'active' and has_permission("block_user"):
                                if st.button(f"🚫 توقيف", key=f"block_{user['login']}"):
                                    conn = get_connection()
                                    conn.execute(text("""
                                        UPDATE users SET status='stopped', blocked_at=NOW(), blocked_by=:admin
                                        WHERE login=:login
                                    """), {"login": user['login'], "admin": st.session_state.get("name", "admin")})
                                    conn.commit()
                                    conn.close()
                                    log_audit("block_user", "user", user['login'], f"{user['name']} {user['lastname']}", "تم التوقيف يدوياً")
                                    st.success("🚫 تم التوقيف")
                                    st.rerun()
            else:
                st.warning("❌ لم يتم العثور على حسابات")
        
        # عرض جميع الحسابات
        if st.button("📊 عرض جميع الحسابات", use_container_width=True):
            conn = get_connection()
            all_users = pd.read_sql("SELECT login, name, lastname, role, status, created_at, created_by, login_count FROM users ORDER BY created_at DESC", conn)
            conn.close()
            st.dataframe(all_users, use_container_width=True)
    
    # =========================
    # 🚫 توقيف حساب
    # =========================
    elif choice == "🚫 توقيف حساب":
        st.subheader("🚫 توقيف حساب")
        
        conn = get_connection()
        users = pd.read_sql("SELECT login, name, lastname FROM users WHERE status='active'", conn)
        conn.close()
        
        if not users.empty:
            user = st.selectbox("اختار الحساب", users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1))
            login = user.split("(")[-1].replace(")", "")
            reason = st.text_area("سبب التوقيف")
            
            if st.button("توقيف", type="primary"):
                conn = get_connection()
                conn.execute(text("""
                    UPDATE users SET status='stopped', blocked_at=NOW(), blocked_reason=:reason, blocked_by=:admin
                    WHERE login=:login
                """), {"login": login, "reason": reason if reason else "تم التوقيف يدوياً", "admin": st.session_state.get("name", "admin")})
                conn.execute(text("""
                    INSERT INTO users_block_log (user_login, blocked_reason, blocked_by)
                    VALUES (:login, :reason, :admin)
                """), {"login": login, "reason": reason if reason else "تم التوقيف يدوياً", "admin": st.session_state.get("name", "admin")})
                conn.commit()
                conn.close()
                
                log_audit("manual_block", "user", login, user, reason)
                st.success("✅ تم التوقيف بنجاح")
                st.rerun()
        else:
            st.info("لا توجد حسابات نشطة للتوقيف")
    
    # =========================
    # 🔄 إعادة تفعيل حساب
    # =========================
    elif choice == "🔄 إعادة تفعيل حساب":
        st.subheader("🔄 إعادة تفعيل حساب موقوف")
        
        conn = get_connection()
        users = pd.read_sql("SELECT login, name, lastname, blocked_at, blocked_reason FROM users WHERE status='stopped'", conn)
        conn.close()
        
        if not users.empty:
            user = st.selectbox("اختار الحساب الموقوف", users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1))
            login = user.split("(")[-1].replace(")", "")
            
            # عرض معلومات التوقيف
            user_data = users[users['login'] == login].iloc[0]
            st.info(f"""
            *معلومات التوقيف:*
            - *تاريخ التوقيف:* {user_data['blocked_at']}
            - *سبب التوقيف:* {user_data['blocked_reason'] if user_data['blocked_reason'] else 'غير مسجل'}
            """)
            
            # التحقق من وجود شكاية
            conn = get_connection()
            recl_count = conn.execute(text("SELECT COUNT(*) FROM reclamations_extended WHERE account_login=:login"), {"login": login}).fetchone()[0]
            conn.close()
            
            if recl_count == 0:
                st.error("❌ لا يمكن إعادة التفعيل بدون شكاية مسجلة")
            else:
                if st.button("✅ إعادة تفعيل", type="primary"):
                    conn = get_connection()
                    conn.execute(text("""
                        UPDATE users SET status='active', blocked_at=NULL, blocked_reason=NULL, blocked_by=NULL, failed_login_attempts=0
                        WHERE login=:login
                    """), {"login": login})
                    conn.commit()
                    conn.close()
                    
                    log_audit("unblock_user", "user", login, user, "تم إعادة التفعيل عبر شكاية")
                    st.success("✅ تم إعادة التفعيل بنجاح")
                    st.rerun()
        else:
            st.info("لا توجد حسابات موقوفة")
    
    # =========================
    # 🔑 تغيير كلمة المرور
    # =========================
    elif choice == "🔑 تغيير كلمة المرور":
        st.subheader("🔑 تغيير كلمة المرور")
        
        conn = get_connection()
        users = pd.read_sql("SELECT login, name, lastname FROM users", conn)
        conn.close()
        
        if not users.empty:
            user = st.selectbox("اختار الحساب", users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1))
            login = user.split("(")[-1].replace(")", "")
            new_password = st.text_input("كلمة المرور الجديدة", type="password")
            confirm_password = st.text_input("تأكيد كلمة المرور", type="password")
            
            if st.button("تحديث"):
                if new_password != confirm_password:
                    st.error("❌ كلمتا المرور غير متطابقتين")
                elif len(new_password) < 6:
                    st.error("❌ كلمة المرور يجب أن تكون 6 أحرف على الأقل")
                else:
                    salt, hash_val = hash_password(new_password)
                    conn = get_connection()
                    conn.execute(text("""
                        UPDATE users SET password_hash=:hash, password_salt=:salt WHERE login=:login
                    """), {"hash": hash_val, "salt": salt, "login": login})
                    conn.commit()
                    conn.close()
                    
                    log_audit("change_password", "user", login, user, "تم تغيير كلمة المرور")
                    st.success("✅ تم تغيير كلمة المرور بنجاح")
    
    # =========================
    # 🗑️ حذف حساب
    # =========================
    elif choice == "🗑️ حذف حساب":
        st.subheader("🗑️ حذف حساب")
        st.warning("⚠️ تحذير: هذا الإجراء لا يمكن التراجع عنه")
        
        conn = get_connection()
        users = pd.read_sql("SELECT login, name, lastname, role FROM users WHERE login != :current", 
                            conn, params={"current": st.session_state.get("login_user", "")})
        conn.close()
        
        if not users.empty:
            user = st.selectbox("اختار الحساب للحذف", users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']}) - {x['role']}", axis=1))
            login = user.split("(")[-1].replace(")", "").split(" ")[0]
            confirm = st.text_input("اكتب DELETE لتأكيد الحذف")
            
            if st.button("🗑️ حذف نهائي", type="primary"):
                if confirm == "DELETE":
                    conn = get_connection()
                    conn.execute(text("DELETE FROM users WHERE login=:login"), {"login": login})
                    conn.commit()
                    conn.close()
                    
                    log_audit("delete_user", "user", login, user, "تم حذف الحساب نهائياً")
                    st.success("✅ تم حذف الحساب")
                    st.rerun()
                else:
                    st.error("❌ اكتب DELETE لتأكيد الحذف")
        else:
            st.info("لا توجد حسابات للحذف")
    
    # =========================
    # 📩 الشكايات
    # =========================
    elif choice == "📩 الشكايات":
        st.subheader("📩 إدارة الشكايات")
        
        tab1, tab2 = st.tabs(["📋 الشكايات الموسعة", "📋 الشكايات العادية"])
        
        with tab1:
            conn = get_connection()
            df = pd.read_sql("SELECT * FROM reclamations_extended ORDER BY id DESC", conn)
            conn.close()
            
            if df.empty:
                st.info("لا توجد شكايات")
            else:
                for _, row in df.iterrows():
                    with st.expander(f"📄 #{row['id']} - {row['caller_name']} {row['caller_lastname']} - {row['account_name']} {row['account_lastname']}"):
                        st.write(f"*المتصل:* {row['caller_name']} {row['caller_lastname']}")
                        st.write(f"*صاحب الحساب:* {row['account_name']} {row['account_lastname']} ({row['account_login']})")
                        st.write(f"*السبب:* {row['reason']}")
                        st.write(f"*التاريخ:* {row['created_at']}")
                        st.write(f"*الحالة:* {format_status(row['status'])}")
                        
                        if row['status'] == 'pending':
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"✅ قبول", key=f"accept_{row['id']}"):
                                    conn = get_connection()
                                    conn.execute(text("UPDATE reclamations_extended SET status='done' WHERE id=:id"), {"id": row['id']})
                                    conn.commit()
                                    conn.close()
                                    log_audit("approve_reclamation", "reclamation", str(row['id']), row['account_login'], "تم قبول الشكاية")
                                    st.rerun()
                            with col2:
                                if st.button(f"❌ رفض", key=f"reject_{row['id']}"):
                                    conn = get_connection()
                                    conn.execute(text("UPDATE reclamations_extended SET status='rejected' WHERE id=:id"), {"id": row['id']})
                                    conn.commit()
                                    conn.close()
                                    log_audit("reject_reclamation", "reclamation", str(row['id']), row['account_login'], "تم رفض الشكاية")
                                    st.rerun()
        
        with tab2:
            conn = get_connection()
            df = pd.read_sql("SELECT * FROM reclamations ORDER BY id DESC", conn)
            conn.close()
            
            if df.empty:
                st.info("لا توجد شكايات عادية")
            else:
                st.dataframe(df, use_container_width=True)
    
    # =========================
    # 🔌 التحكم في النظام
    # =========================
    elif choice == "🔌 التحكم في النظام":
        st.subheader("🔌 التحكم في النظام")
        
        current_status = get_system_status()
        
        col1, col2 = st.columns(2)
        with col1:
            if current_status == "on":
                st.success("✅ النظام يعمل بشكل طبيعي")
                if st.button("🛑 إيقاف النظام", use_container_width=True):
                    set_system_status("off")
                    log_audit("system_off", "system", None, None, "تم إيقاف النظام")
                    st.rerun()
            else:
                st.error("🔴 النظام متوقف")
                if st.button("▶️ تشغيل النظام", use_container_width=True):
                    set_system_status("on")
                    log_audit("system_on", "system", None, None, "تم تشغيل النظام")
                    st.rerun()
        
        with col2:
            if st.button("🔄 إعادة تشغيل الجلسة", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
    
    # =========================
    # 📊 سجل التدقيق
    # =========================
    elif choice == "📊 سجل التدقيق":
        st.subheader("📊 سجل التدقيق (Audit Log)")
        
        conn = get_connection()
        audit = pd.read_sql("""
            SELECT admin_name, action, target_name, details, created_at 
            FROM audit_log ORDER BY id DESC LIMIT 100
        """, conn)
        conn.close()
        
        if not audit.empty:
            st.dataframe(audit, use_container_width=True)
            
            # تصدير إلى CSV
            csv = audit.to_csv(index=False).encode('utf-8')
            st.download_button("📥 تصدير إلى CSV", csv, f"audit_log_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.info("لا توجد سجلات تدقيق")
    
    # =========================
    # 👑 إدارة الصلاحيات
    # =========================
    elif choice == "👑 إدارة الصلاحيات":
        st.subheader("👑 إدارة صلاحيات المستخدمين")
        
        conn = get_connection()
        permissions = pd.read_sql("SELECT * FROM user_permissions", conn)
        conn.close()
        
        st.dataframe(permissions, use_container_width=True)
        
        st.markdown("### 📝 إضافة صلاحية جديدة")
        new_role = st.text_input("اسم الدور الجديد")
        new_perms = st.text_input("الصلاحيات (مفصولة بفاصلة)")
        
        if st.button("إضافة"):
            if new_role and new_perms:
                perms_list = [p.strip() for p in new_perms.split(",")]
                conn = get_connection()
                conn.execute(text("""
                    INSERT INTO user_permissions (role, permissions) VALUES (:role, :perms)
                """), {"role": new_role, "perms": perms_list})
                conn.commit()
                conn.close()
                log_audit("add_permission", "permission", new_role, None, f"تم إضافة دور {new_role} بالصلاحيات {new_perms}")
                st.success("✅ تمت الإضافة")
                st.rerun()
