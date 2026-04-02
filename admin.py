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

# =========================
# 🔐 Hashing + Salt
# =========================
def hash_password(password: str) -> tuple:
    salt = secrets.token_hex(32)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt, hash_obj.hex()

def verify_password(password: str, salt: str, hash_value: str) -> bool:
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hash_obj.hex() == hash_value

# =========================
# 📝 Audit Log
# =========================
def log_audit(action: str, target_type: str = None, target_id: str = None, 
              target_name: str = None, details: str = None):
    try:
        conn = get_connection()
        conn.execute(text("""
            INSERT INTO audit_log (admin_login, admin_name, action, target_type, target_id, target_name, details, created_at)
            VALUES (:admin_login, :admin_name, :action, :target_type, :target_id, :target_name, :details, NOW())
        """), {
            "admin_login": st.session_state.get("login_user", "unknown"),
            "admin_name": st.session_state.get("name", "unknown"),
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "target_name": target_name,
            "details": details
        })
        conn.commit()
        conn.close()
    except Exception as e:
        pass

# =========================
# 🔐 التحقق من الصلاحيات
# =========================
def has_permission(permission: str) -> bool:
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
        if st.button("🌙" if st.session_state.theme == "light" else "☀️"):
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
            }
            div.stButton > button {
                background: linear-gradient(45deg, #11998e, #38ef7d) !important;
                color: white !important;
            }
        </style>
        """, unsafe_allow_html=True)

# =========================
# 📊 Dashboard
# =========================
def show_dashboard():
    st.markdown("<h1 style='text-align: center;'>🏢 لوحة التحكم الرئيسية</h1>", unsafe_allow_html=True)
    
    conn = get_connection()
    
    users_count = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
    active_users = conn.execute(text("SELECT COUNT(*) FROM users WHERE status='active' AND partial_block_percent=0")).fetchone()[0]
    stopped_users = conn.execute(text("SELECT COUNT(*) FROM users WHERE status='stopped'")).fetchone()[0]
    partial_blocked = conn.execute(text("SELECT COUNT(*) FROM users WHERE status='active' AND partial_block_percent > 0")).fetchone()[0]
    pending_recl = conn.execute(text("SELECT COUNT(*) FROM reclamations_extended WHERE status='pending'")).fetchone()[0]
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👥 إجمالي المستخدمين", users_count)
    col2.metric("🟢 النشطين بالكامل", active_users)
    col3.metric("🟡 الموقوفين جزئياً", partial_blocked)
    col4.metric("🔴 الموقوفين كلياً", stopped_users)
    col5.metric("📩 الشكايات المعلقة", pending_recl)
    
    st.divider()
    
    st.markdown("### 📋 آخر العمليات المسجلة")
    audit = pd.read_sql("""
        SELECT admin_name, action, target_name, details, created_at 
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
    toggle_theme()
    
    # بناء القائمة حسب الصلاحيات
    menu = ["🏠 Dashboard"]
    
    if has_permission("create_user"):
        menu.append("➕ إنشاء حساب")
    if has_permission("view_users"):
        menu.append("📋 عرض الحسابات")
    if has_permission("block_user"):
        menu.append("🚫 توقيف كامل")
    if has_permission("partial_block_user"):
        menu.append("⚠️ توقيف جزئي")
    if has_permission("partial_unblock_user"):
        menu.append("🔄 استرجاع حساب موقوف جزئياً")
    if has_permission("unblock_user"):
        menu.append("✅ إعادة تفعيل كامل")
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
    if has_permission("manage_permissions"):
        menu.append("👑 إدارة الصلاحيات")
    
    choice = st.sidebar.selectbox("القائمة", menu)
    
    # عرض معلومات المستخدم
    st.sidebar.divider()
    st.sidebar.markdown(f"""
    ### 👤 {st.session_state.get('name', 'Admin')}
    *الدور:* {st.session_state.get('role', 'admin')}
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
                        INSERT INTO users (login, password_hash, password_salt, role, name, lastname, phone, subject, status, created_by, created_at, partial_block_percent)
                        VALUES (:login, :hash, :salt, :role, :name, :lastname, :phone, :subject, 'active', :created_by, NOW(), 0)
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
                    
                    log_audit("create_user", "user", login, f"{name} {lastname}", f"تم إنشاء حساب بدور {role}")
                    
                    st.success(f"✅ تم إنشاء الحساب")
                    st.info(f"*Login:* {login}")
                    st.warning(f"*Password:* {password}")
                else:
                    st.error("❌ الإسم والنسب مطلوبان")
    
    # =========================
    # 📋 عرض الحسابات
    # =========================
    elif choice == "📋 عرض الحسابات":
        st.subheader("📋 عرض الحسابات")
        
        col1, col2 = st.columns(2)
        with col1:
            search_name = st.text_input("🔍 إسم المستخدم")
        with col2:
            search_lastname = st.text_input("🔍 نسب المستخدم")
        
        if st.button("🔍 بحث", use_container_width=True):
            conn = get_connection()
            query = "SELECT * FROM users WHERE 1=1"
            params = {}
            if search_name:
                query += " AND name ILIKE :name"
                params["name"] = f"%{search_name}%"
            if search_lastname:
                query += " AND lastname ILIKE :lastname"
                params["lastname"] = f"%{search_lastname}%"
            
            users = pd.read_sql(query, conn, params=params)
            conn.close()
            
            if not users.empty:
                # إضافة عمود الحالة المعروضة
                users['الحالة'] = users.apply(lambda x: 
                    '🔴 موقوف كلياً' if x['status'] == 'stopped' 
                    else f'🟡 موقوف جزئياً ({x["partial_block_percent"]}%)' if x.get('partial_block_percent', 0) > 0 
                    else '🟢 نشط', axis=1)
                st.dataframe(users[['login', 'name', 'lastname', 'role', 'الحالة', 'created_at', 'created_by']], use_container_width=True)
            else:
                st.warning("❌ لم يتم العثور على حسابات")
        
        if st.button("📊 عرض جميع الحسابات", use_container_width=True):
            conn = get_connection()
            all_users = pd.read_sql("SELECT login, name, lastname, role, status, partial_block_percent, created_at, created_by FROM users ORDER BY created_at DESC", conn)
            conn.close()
            all_users['الحالة'] = all_users.apply(lambda x: 
                '🔴 موقوف كلياً' if x['status'] == 'stopped' 
                else f'🟡 موقوف جزئياً ({x["partial_block_percent"]}%)' if x.get('partial_block_percent', 0) > 0 
                else '🟢 نشط', axis=1)
            st.dataframe(all_users, use_container_width=True)
    
    # =========================
    # 🚫 توقيف كامل
    # =========================
    elif choice == "🚫 توقيف كامل":
        st.subheader("🚫 توقيف حساب (كلياً)")
        
        conn = get_connection()
        users = pd.read_sql("SELECT login, name, lastname FROM users WHERE status='active'", conn)
        conn.close()
        
        if not users.empty:
            user = st.selectbox("اختار الحساب", users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1))
            login = user.split("(")[-1].replace(")", "")
            reason = st.text_area("سبب التوقيف")
            
            if st.button("توقيف كلياً", type="primary"):
                conn = get_connection()
                conn.execute(text("""
                    UPDATE users SET status='stopped', blocked_at=NOW(), blocked_reason=:reason, blocked_by=:admin, partial_block_percent=0
                    WHERE login=:login
                """), {"login": login, "reason": reason if reason else "تم التوقيف كلياً", "admin": st.session_state.get("name", "admin")})
                conn.execute(text("""
                    INSERT INTO users_block_log (user_login, blocked_reason, blocked_by)
                    VALUES (:login, :reason, :admin)
                """), {"login": login, "reason": reason if reason else "تم التوقيف كلياً", "admin": st.session_state.get("name", "admin")})
                conn.commit()
                conn.close()
                
                log_audit("full_block", "user", login, user, reason)
                st.success("✅ تم التوقيف الكلي")
                st.rerun()
        else:
            st.info("لا توجد حسابات نشطة")
    
    # =========================
    # ⚠️ توقيف جزئي (جديد)
    # =========================
    elif choice == "⚠️ توقيف جزئي":
        st.subheader("⚠️ توقيف جزئي للحساب")
        
        conn = get_connection()
        users = pd.read_sql("SELECT login, name, lastname, partial_block_percent FROM users WHERE status='active'", conn)
        conn.close()
        
        if not users.empty:
            user = st.selectbox("اختار الحساب", users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']}) - حالياً: {x['partial_block_percent']}%", axis=1))
            login = user.split("(")[-1].replace(")", "").split(" -")[0]
            
            st.markdown("### اختر نسبة التوقيف")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🔴 10%", use_container_width=True):
                    st.session_state.partial_percent = 10
            with col2:
                if st.button("🟠 25%", use_container_width=True):
                    st.session_state.partial_percent = 25
            with col3:
                if st.button("🟡 50%", use_container_width=True):
                    st.session_state.partial_percent = 50
            with col4:
                if st.button("🟤 75%", use_container_width=True):
                    st.session_state.partial_percent = 75
            
            # عرض النسبة المختارة
            if "partial_percent" in st.session_state:
                st.info(f"النسبة المختارة: *{st.session_state.partial_percent}%*")
                reason = st.text_area("سبب التوقيف الجزئي")
                
                if st.button("تطبيق التوقيف الجزئي", type="primary"):
                    conn = get_connection()
                    conn.execute(text("""
                        UPDATE users 
                        SET partial_block_percent = :percent,
                            partial_block_reason = :reason,
                            partial_blocked_at = NOW(),
                            partial_blocked_by = :admin
                        WHERE login = :login
                    """), {
                        "percent": st.session_state.partial_percent,
                        "reason": reason if reason else f"تم التوقيف الجزئي بنسبة {st.session_state.partial_percent}%",
                        "admin": st.session_state.get("name", "admin"),
                        "login": login
                    })
                    conn.execute(text("""
                        INSERT INTO partial_block_log (user_login, block_percent, block_reason, blocked_by)
                        VALUES (:login, :percent, :reason, :admin)
                    """), {
                        "login": login,
                        "percent": st.session_state.partial_percent,
                        "reason": reason if reason else f"تم التوقيف الجزئي بنسبة {st.session_state.partial_percent}%",
                        "admin": st.session_state.get("name", "admin")
                    })
                    conn.commit()
                    conn.close()
                    
                    log_audit("partial_block", "user", login, user, f"تم التوقيف بنسبة {st.session_state.partial_percent}% - {reason}")
                    st.success(f"✅ تم توقيف الحساب بنسبة {st.session_state.partial_percent}%")
                    del st.session_state.partial_percent
                    st.rerun()
        else:
            st.info("لا توجد حسابات نشطة")
    
    # =========================
    # 🔄 استرجاع حساب موقوف جزئياً (جديد)
    # =========================
    elif choice == "🔄 استرجاع حساب موقوف جزئياً":
        st.subheader("🔄 استرجاع حساب موقوف جزئياً")
        
        conn = get_connection()
        users = pd.read_sql("""
            SELECT login, name, lastname, partial_block_percent, partial_block_reason, partial_blocked_at 
            FROM users WHERE status='active' AND partial_block_percent > 0
        """, conn)
        conn.close()
        
        if not users.empty:
            user = st.selectbox("اختار الحساب الموقوف جزئياً", users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']}) - موقوف {x['partial_block_percent']}%", axis=1))
            login = user.split("(")[-1].replace(")", "").split(" -")[0]
            
            # عرض معلومات التوقيف الحالية
            user_data = users[users['login'] == login].iloc[0]
            st.warning(f"""
            *معلومات التوقيف الحالية:*
            - *نسبة التوقيف:* {user_data['partial_block_percent']}%
            - *سبب التوقيف:* {user_data['partial_block_reason'] if user_data['partial_block_reason'] else 'غير مسجل'}
            - *تاريخ التوقيف:* {user_data['partial_blocked_at']}
            """)
            
            st.markdown("### اختر نسبة الاسترجاع")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🟢 استرجاع 10%", use_container_width=True):
                    st.session_state.restore_percent = 10
            with col2:
                if st.button("🟢 استرجاع 25%", use_container_width=True):
                    st.session_state.restore_percent = 25
            with col3:
                if st.button("🟢 استرجاع 50%", use_container_width=True):
                    st.session_state.restore_percent = 50
            with col4:
                if st.button("🟢 استرجاع 75%", use_container_width=True):
                    st.session_state.restore_percent = 75
            
            if "restore_percent" in st.session_state:
                current_percent = user_data['partial_block_percent']
                new_percent = max(0, current_percent - st.session_state.restore_percent)
                
                st.info(f"""
                *الاسترجاع المقترح:*
                - النسبة الحالية: {current_percent}%
                - نسبة الاسترجاع: {st.session_state.restore_percent}%
                - النسبة الجديدة: {new_percent}%
                """)
                
                if st.button("تطبيق الاسترجاع", type="primary"):
                    conn = get_connection()
                    if new_percent == 0:
                        # استرجاع كامل
                        conn.execute(text("""
                            UPDATE users 
                            SET partial_block_percent = 0,
                                partial_block_reason = NULL,
                                partial_blocked_at = NULL,
                                partial_blocked_by = NULL
                            WHERE login = :login
                        """), {"login": login})
                        st.success(f"✅ تم استرجاع الحساب بالكامل")
                    else:
                        # استرجاع جزئي
                        conn.execute(text("""
                            UPDATE users 
                            SET partial_block_percent = :new_percent
                            WHERE login = :login
                        """), {"new_percent": new_percent, "login": login})
                        st.success(f"✅ تم استرجاع {st.session_state.restore_percent}% من الحساب، النسبة المتبقية: {new_percent}%")
                    
                    conn.commit()
                    conn.close()
                    
                    log_audit("partial_restore", "user", login, user, f"تم استرجاع {st.session_state.restore_percent}%")
                    del st.session_state.restore_percent
                    st.rerun()
        else:
            st.info("لا توجد حسابات موقوفة جزئياً")
    
    # =========================
    # ✅ إعادة تفعيل كامل
    # =========================
    elif choice == "✅ إعادة تفعيل كامل":
        st.subheader("✅ إعادة تفعيل حساب موقوف كلياً")
        
        conn = get_connection()
        users = pd.read_sql("SELECT login, name, lastname, blocked_at, blocked_reason FROM users WHERE status='stopped'", conn)
        conn.close()
        
        if not users.empty:
            user = st.selectbox("اختار الحساب", users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1))
            login = user.split("(")[-1].replace(")", "")
            
            if st.button("✅ إعادة تفعيل كلياً", type="primary"):
                conn = get_connection()
                conn.execute(text("""
                    UPDATE users SET status='active', blocked_at=NULL, blocked_reason=NULL, blocked_by=NULL, failed_login_attempts=0, partial_block_percent=0
                    WHERE login=:login
                """), {"login": login})
                conn.commit()
                conn.close()
                
                log_audit("full_unblock", "user", login, user, "تم إعادة التفعيل الكلي")
                st.success("✅ تم إعادة التفعيل الكلي")
                st.rerun()
        else:
            st.info("لا توجد حسابات موقوفة كلياً")
    
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
                    st.success("✅ تم تغيير كلمة المرور")
    
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
            user = st.selectbox("اختار الحساب للحذف", users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1))
            login = user.split("(")[-1].replace(")", "").split(" ")[0]
            confirm = st.text_input("اكتب DELETE لتأكيد الحذف")
            
            if st.button("🗑️ حذف نهائي", type="primary"):
                if confirm == "DELETE":
                    conn = get_connection()
                    conn.execute(text("DELETE FROM users WHERE login=:login"), {"login": login})
                    conn.commit()
                    conn.close()
                    
                    log_audit("delete_user", "user", login, user, "تم حذف الحساب")
                    st.success("✅ تم الحذف")
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
        
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM reclamations_extended ORDER BY id DESC", conn)
        conn.close()
        
        if df.empty:
            st.info("لا توجد شكايات")
        else:
            for _, row in df.iterrows():
                with st.expander(f"📄 #{row['id']} - {row['caller_name']} {row['caller_lastname']}"):
                    st.write(f"*صاحب الحساب:* {row['account_name']} {row['account_lastname']} ({row['account_login']})")
                    st.write(f"*السبب:* {row['reason']}")
                    st.write(f"*التاريخ:* {row['created_at']}")
                    st.write(f"*الحالة:* {format_status(row['status'])}")
    
    # =========================
    # 🔌 التحكم في النظام
    # =========================
    elif choice == "🔌 التحكم في النظام":
        st.subheader("🔌 التحكم في النظام")
        
        current_status = get_system_status()
        
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
        
        st.markdown("### 📝 تغيير صلاحيات مستخدم")
        
        conn = get_connection()
        users = pd.read_sql("SELECT login, name, lastname, role FROM users", conn)
        conn.close()
        
        if not users.empty:
            user = st.selectbox("اختار المستخدم", users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1))
            login = user.split("(")[-1].replace(")", "")
            new_role = st.selectbox("الدور الجديد", ["viewer", "tech_support", "admin", "super_admin"])
            
            if st.button("تحديث الصلاحية"):
                conn = get_connection()
                conn.execute(text("UPDATE users SET role=:role WHERE login=:login"), {"role": new_role, "login": login})
                conn.commit()
                conn.close()
                
                log_audit("change_permission", "user", login, user, f"تم تغيير الدور إلى {new_role}")
                st.success("✅ تم تحديث الصلاحية")
                st.rerun()
