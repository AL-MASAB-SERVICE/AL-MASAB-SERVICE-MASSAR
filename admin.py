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
    except Exception:
        pass

# =========================
# 🔐 التحقق من الصلاحيات
# =========================
def has_permission(permission: str) -> bool:
    if "user_permissions" not in st.session_state:
        try:
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
        except Exception:
            st.session_state.user_permissions = ['*']
    
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
    else:
        return "⏳ قيد الانتظار"

# =========================
# 🌓 Dark/Light Mode
# =========================
def toggle_theme():
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    
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
    
    try:
        conn = get_connection()
        
        users_count = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
        active_users = conn.execute(text("SELECT COUNT(*) FROM users WHERE status='active' AND (partial_block_percent IS NULL OR partial_block_percent=0)")).fetchone()[0]
        stopped_users = conn.execute(text("SELECT COUNT(*) FROM users WHERE status='stopped'")).fetchone()[0]
        partial_blocked = conn.execute(text("SELECT COUNT(*) FROM users WHERE status='active' AND partial_block_percent > 0")).fetchone()[0]
        pending_recl = conn.execute(text("SELECT COUNT(*) FROM reclamations_extended WHERE status='pending'")).fetchone()[0]
        
        conn.close()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("👥 إجمالي المستخدمين", users_count)
        col2.metric("🟢 النشطين بالكامل", active_users)
        col3.metric("🟡 الموقوفين جزئياً", partial_blocked)
        col4.metric("🔴 الموقوفين كلياً", stopped_users)
        col5.metric("📩 الشكايات المعلقة", pending_recl)
        
        st.divider()
        
        st.markdown("### 🟡 الحسابات الموقوفة جزئياً")
        try:
            conn = get_connection()
            partial_users = pd.read_sql("""
                SELECT login, name, lastname, partial_block_percent, partial_block_reason 
                FROM users WHERE status='active' AND partial_block_percent > 0
            """, conn)
            conn.close()
            if not partial_users.empty:
                st.dataframe(partial_users, use_container_width=True)
            else:
                st.info("لا توجد حسابات موقوفة جزئياً")
        except Exception:
            st.info("لا توجد حسابات موقوفة جزئياً")
        
        st.divider()
        
        st.markdown("### 📋 آخر العمليات المسجلة")
        try:
            conn = get_connection()
            audit = pd.read_sql("""
                SELECT admin_name, action, target_name, details, created_at 
                FROM audit_log ORDER BY id DESC LIMIT 10
            """, conn)
            conn.close()
            if not audit.empty:
                st.dataframe(audit, use_container_width=True)
            else:
                st.info("لا توجد عمليات مسجلة بعد")
        except Exception:
            st.info("لا توجد عمليات مسجلة بعد")
            
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}")

# =========================
# 🧑‍🔧 لوحة admin الرئيسية
# =========================
def admin_panel():
    # تفعيل الثيم
    toggle_theme()
    
    # عنوان التطبيق في السايدبار
    st.sidebar.markdown("# 🏢 AL MASAB SERVICE")
    st.sidebar.markdown("---")
    
    # ثيم الزر
    theme_col1, theme_col2 = st.sidebar.columns([1, 4])
    with theme_col1:
        theme_icon = "🌙" if st.session_state.get("theme", "light") == "light" else "☀️"
        if st.button(theme_icon, key="theme_btn"):
            st.session_state.theme = "dark" if st.session_state.get("theme", "light") == "light" else "light"
            st.rerun()
    
    # معلومات المستخدم
    st.sidebar.markdown(f"""
    ---
    ### 👤 {st.session_state.get('name', 'Admin')}
    *الدور:* {st.session_state.get('role', 'admin')}
    ---
    """)
    
    # بناء القائمة الكاملة (جميع الأزرار)
    menu_list = ["🏠 Dashboard"]
    menu_list.append("➕ إنشاء حساب")
    menu_list.append("📋 عرض الحسابات")
    menu_list.append("🚫 توقيف كامل")
    menu_list.append("⚠️ توقيف جزئي")
    menu_list.append("🔄 استرجاع جزئي")
    menu_list.append("✅ إعادة تفعيل كامل")
    menu_list.append("🔑 تغيير كلمة المرور")
    menu_list.append("🗑️ حذف حساب")
    menu_list.append("📩 الشكايات")
    menu_list.append("🔌 التحكم في النظام")
    menu_list.append("📊 سجل التدقيق")
    menu_list.append("👑 إدارة الصلاحيات")
    
    choice = st.sidebar.selectbox("القائمة", menu_list, key="main_menu")
    
    # زر تسجيل الخروج (مرة واحدة فقط)
    if st.sidebar.button("🚪 تسجيل الخروج", key="logout_btn"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # =========================
    # Dashboard
    # =========================
    if choice == "🏠 Dashboard":
        show_dashboard()
    
    # =========================
    # إنشاء حساب
    # =========================
    elif choice == "➕ إنشاء حساب":
        st.subheader("➕ إنشاء حساب جديد")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("الإسم", key="create_name")
            lastname = st.text_input("النسب", key="create_lastname")
        with col2:
            phone = st.text_input("الهاتف", key="create_phone")
            subject = st.text_input("المادة", key="create_subject")
        
        role = st.selectbox("الدور", ["prof", "surveillant", "directeur", "parents", "admin", "tech_support", "viewer"], key="create_role")
        
        if st.button("إنشاء حساب", key="create_btn"):
            if name and lastname:
                login = generate_login(name, lastname)
                password = generate_password()
                salt, hash_val = hash_password(password)
                
                try:
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
                        "created_by": st.session_state.get("name", "admin")
                    })
                    conn.commit()
                    conn.close()
                    
                    log_audit("create_user", "user", login, f"{name} {lastname}", f"تم إنشاء حساب بدور {role}")
                    
                    st.success(f"✅ تم إنشاء الحساب")
                    st.code(f"Login: {login}\nPassword: {password}")
                except Exception as e:
                    st.error(f"خطأ: {e}")
            else:
                st.error("❌ الإسم والنسب مطلوبان")
    
    # =========================
    # عرض الحسابات
    # =========================
    elif choice == "📋 عرض الحسابات":
        st.subheader("📋 عرض الحسابات")
        
        col1, col2 = st.columns(2)
        with col1:
            search_name = st.text_input("🔍 إسم المستخدم", key="search_name")
        with col2:
            search_lastname = st.text_input("🔍 نسب المستخدم", key="search_lastname")
        
        if st.button("🔍 بحث", key="search_btn"):
            try:
                conn = get_connection()
                query = "SELECT login, name, lastname, role, status, partial_block_percent, created_at, created_by FROM users WHERE 1=1"
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
                    users['الحالة'] = users.apply(lambda x: 
                        '🔴 موقوف كلياً' if x['status'] == 'stopped' 
                        else f'🟡 موقوف جزئياً ({x["partial_block_percent"]}%)' if x.get('partial_block_percent', 0) > 0 
                        else '🟢 نشط', axis=1)
                    st.dataframe(users, use_container_width=True)
                else:
                    st.warning("❌ لم يتم العثور على حسابات")
            except Exception as e:
                st.error(f"خطأ: {e}")
        
        if st.button("📊 عرض جميع الحسابات", key="show_all"):
            try:
                conn = get_connection()
                all_users = pd.read_sql("SELECT login, name, lastname, role, status, partial_block_percent, created_at, created_by FROM users ORDER BY created_at DESC", conn)
                conn.close()
                all_users['الحالة'] = all_users.apply(lambda x: 
                    '🔴 موقوف كلياً' if x['status'] == 'stopped' 
                    else f'🟡 موقوف جزئياً ({x["partial_block_percent"]}%)' if x.get('partial_block_percent', 0) > 0 
                    else '🟢 نشط', axis=1)
                st.dataframe(all_users, use_container_width=True)
            except Exception as e:
                st.error(f"خطأ: {e}")
    
    # =========================
    # توقيف كامل
    # =========================
    elif choice == "🚫 توقيف كامل":
        st.subheader("🚫 توقيف حساب (كلياً)")
        
        try:
            conn = get_connection()
            users = pd.read_sql("SELECT login, name, lastname FROM users WHERE status='active'", conn)
            conn.close()
            
            if not users.empty:
                user_options = users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1).tolist()
                selected_user = st.selectbox("اختار الحساب", user_options, key="full_block_select")
                login = selected_user.split("(")[-1].replace(")", "")
                reason = st.text_area("سبب التوقيف", key="full_block_reason")
                
                if st.button("توقيف كلياً", key="full_block_btn"):
                    conn = get_connection()
                    conn.execute(text("""
                        UPDATE users SET status='stopped', blocked_at=NOW(), blocked_reason=:reason, blocked_by=:admin, partial_block_percent=0
                        WHERE login=:login
                    """), {"login": login, "reason": reason if reason else "تم التوقيف كلياً", "admin": st.session_state.get("name", "admin")})
                    conn.commit()
                    conn.close()
                    
                    log_audit("full_block", "user", login, selected_user, reason)
                    st.success("✅ تم التوقيف الكلي")
                    st.rerun()
            else:
                st.info("لا توجد حسابات نشطة")
        except Exception as e:
            st.error(f"خطأ: {e}")
    
    # =========================
    # توقيف جزئي
    # =========================
    elif choice == "⚠️ توقيف جزئي":
        st.subheader("⚠️ توقيف جزئي للحساب")
        
        try:
            conn = get_connection()
            users = pd.read_sql("SELECT login, name, lastname, partial_block_percent FROM users WHERE status='active'", conn)
            conn.close()
            
            if not users.empty:
                user_options = users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']}) - حالياً: {x['partial_block_percent']}%", axis=1).tolist()
                selected_user = st.selectbox("اختار الحساب", user_options, key="partial_block_select")
                login = selected_user.split("(")[-1].replace(")", "").split(" -")[0]
                
                st.markdown("### اختر نسبة التوقيف")
                
                percent_options = ["10%", "25%", "50%", "75%"]
                percent = st.radio("النسبة", percent_options, horizontal=True, key="partial_percent_radio")
                percent_value = int(percent.replace("%", ""))
                
                reason = st.text_area("سبب التوقيف الجزئي", key="partial_block_reason")
                
                if st.button("تطبيق التوقيف الجزئي", key="apply_partial_btn"):
                    conn = get_connection()
                    conn.execute(text("""
                        UPDATE users 
                        SET partial_block_percent = :percent,
                            partial_block_reason = :reason,
                            partial_blocked_at = NOW(),
                            partial_blocked_by = :admin
                        WHERE login = :login
                    """), {
                        "percent": percent_value,
                        "reason": reason if reason else f"تم التوقيف الجزئي بنسبة {percent_value}%",
                        "admin": st.session_state.get("name", "admin"),
                        "login": login
                    })
                    conn.commit()
                    conn.close()
                    
                    log_audit("partial_block", "user", login, selected_user, f"تم التوقيف بنسبة {percent_value}%")
                    st.success(f"✅ تم توقيف الحساب بنسبة {percent_value}%")
                    st.rerun()
            else:
                st.info("لا توجد حسابات نشطة")
        except Exception as e:
            st.error(f"خطأ: {e}")
    
    # =========================
    # استرجاع جزئي
    # =========================
    elif choice == "🔄 استرجاع جزئي":
        st.subheader("🔄 استرجاع حساب موقوف جزئياً")
        
        try:
            conn = get_connection()
            users = pd.read_sql("""
                SELECT login, name, lastname, partial_block_percent, partial_block_reason, partial_blocked_at 
                FROM users WHERE status='active' AND (partial_block_percent IS NOT NULL AND partial_block_percent > 0)
            """, conn)
            conn.close()
            
            if not users.empty:
                user_options = users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']}) - موقوف {x['partial_block_percent']}%", axis=1).tolist()
                selected_user = st.selectbox("اختار الحساب الموقوف جزئياً", user_options, key="restore_select")
                login = selected_user.split("(")[-1].replace(")", "").split(" -")[0]
                
                user_data = users[users['login'] == login].iloc[0]
                current_percent = user_data['partial_block_percent']
                
                st.warning(f"""
                *معلومات التوقيف الحالية:*
                - *نسبة التوقيف:* {current_percent}%
                - *سبب التوقيف:* {user_data['partial_block_reason'] if user_data['partial_block_reason'] else 'غير مسجل'}
                """)
                
                st.markdown("### اختر نسبة الاسترجاع")
                restore_options = ["10%", "25%", "50%", "75%"]
                restore_percent = st.radio("نسبة الاسترجاع", restore_options, horizontal=True, key="restore_percent_radio")
                restore_value = int(restore_percent.replace("%", ""))
                
                new_percent = max(0, current_percent - restore_value)
                
                st.info(f"""
                *الاسترجاع المقترح:*
                - النسبة الحالية: {current_percent}%
                - نسبة الاسترجاع: {restore_value}%
                - النسبة الجديدة: {new_percent}%
                """)
                
                if st.button("تطبيق الاسترجاع", key="apply_restore_btn"):
                    conn = get_connection()
                    if new_percent == 0:
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
                        conn.execute(text("""
                            UPDATE users 
                            SET partial_block_percent = :new_percent
                            WHERE login = :login
                        """), {"new_percent": new_percent, "login": login})
                        st.success(f"✅ تم استرجاع {restore_value}% من الحساب، النسبة المتبقية: {new_percent}%")
                    
                    conn.commit()
                    conn.close()
                    
                    log_audit("partial_restore", "user", login, selected_user, f"تم استرجاع {restore_value}%")
                    st.rerun()
            else:
                st.info("لا توجد حسابات موقوفة جزئياً")
        except Exception as e:
            st.error(f"خطأ: {e}")
    
    # =========================
    # إعادة تفعيل كامل
    # =========================
    elif choice == "✅ إعادة تفعيل كامل":
        st.subheader("✅ إعادة تفعيل حساب موقوف كلياً")
        
        try:
            conn = get_connection()
            users = pd.read_sql("SELECT login, name, lastname FROM users WHERE status='stopped'", conn)
            conn.close()
            
            if not users.empty:
                user_options = users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1).tolist()
                selected_user = st.selectbox("اختار الحساب", user_options, key="full_unblock_select")
                login = selected_user.split("(")[-1].replace(")", "")
                
                if st.button("✅ إعادة تفعيل كلياً", key="full_unblock_btn"):
                    conn = get_connection()
                    conn.execute(text("""
                        UPDATE users SET status='active', blocked_at=NULL, blocked_reason=NULL, blocked_by=NULL, failed_login_attempts=0, partial_block_percent=0
                        WHERE login=:login
                    """), {"login": login})
                    conn.commit()
                    conn.close()
                    
                    log_audit("full_unblock", "user", login, selected_user, "تم إعادة التفعيل الكلي")
                    st.success("✅ تم إعادة التفعيل الكلي")
                    st.rerun()
            else:
                st.info("لا توجد حسابات موقوفة كلياً")
        except Exception as e:
            st.error(f"خطأ: {e}")
    
    # =========================
    # تغيير كلمة المرور
    # =========================
    elif choice == "🔑 تغيير كلمة المرور":
        st.subheader("🔑 تغيير كلمة المرور")
        
        try:
            conn = get_connection()
            users = pd.read_sql("SELECT login, name, lastname FROM users", conn)
            conn.close()
            
            if not users.empty:
                user_options = users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1).tolist()
                selected_user = st.selectbox("اختار الحساب", user_options, key="change_pwd_select")
                login = selected_user.split("(")[-1].replace(")", "")
                new_password = st.text_input("كلمة المرور الجديدة", type="password", key="new_pwd")
                confirm_password = st.text_input("تأكيد كلمة المرور", type="password", key="confirm_pwd")
                
                if st.button("تحديث", key="change_pwd_btn"):
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
                        
                        log_audit("change_password", "user", login, selected_user, "تم تغيير كلمة المرور")
                        st.success("✅ تم تغيير كلمة المرور")
        except Exception as e:
            st.error(f"خطأ: {e}")
    
    # =========================
    # حذف حساب
    # =========================
    elif choice == "🗑️ حذف حساب":
        st.subheader("🗑️ حذف حساب")
        st.warning("⚠️ تحذير: هذا الإجراء لا يمكن التراجع عنه")
        
        try:
            conn = get_connection()
            users = pd.read_sql("SELECT login, name, lastname, role FROM users WHERE login != :current", 
                                conn, params={"current": st.session_state.get("login_user", "")})
            conn.close()
            
            if not users.empty:
                user_options = users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1).tolist()
                selected_user = st.selectbox("اختار الحساب للحذف", user_options, key="delete_select")
                login = selected_user.split("(")[-1].replace(")", "").split(" ")[0]
                confirm = st.text_input("اكتب DELETE لتأكيد الحذف", key="delete_confirm")
                
                if st.button("🗑️ حذف نهائي", key="delete_btn"):
                    if confirm == "DELETE":
                        conn = get_connection()
                        conn.execute(text("DELETE FROM users WHERE login=:login"), {"login": login})
                        conn.commit()
                        conn.close()
                        
                        log_audit("delete_user", "user", login, selected_user, "تم حذف الحساب")
                        st.success("✅ تم الحذف")
                        st.rerun()
                    else:
                        st.error("❌ اكتب DELETE لتأكيد الحذف")
            else:
                st.info("لا توجد حسابات للحذف")
        except Exception as e:
            st.error(f"خطأ: {e}")
    
    # =========================
    # الشكايات
    # =========================
    elif choice == "📩 الشكايات":
        st.subheader("📩 إدارة الشكايات")
        
        try:
            conn = get_connection()
            df = pd.read_sql("SELECT * FROM reclamations_extended ORDER BY id DESC", conn)
            conn.close()
            
            if df.empty:
                st.info("لا توجد شكايات")
            else:
                for idx, row in df.iterrows():
                    with st.expander(f"📄 #{row['id']} - {row['caller_name']} {row['caller_lastname']}"):
                        st.write(f"*صاحب الحساب:* {row['account_name']} {row['account_lastname']} ({row['account_login']})")
                        st.write(f"*السبب:* {row['reason']}")
                        st.write(f"*التاريخ:* {row['created_at']}")
                        st.write(f"*الحالة:* {format_status(row['status'])}")
        except Exception as e:
            st.error(f"خطأ: {e}")
    
    # =========================
    # التحكم في النظام
    # =========================
    elif choice == "🔌 التحكم في النظام":
        st.subheader("🔌 التحكم في النظام")
        
        current_status = get_system_status()
        
        if current_status == "on":
            st.success("✅ النظام يعمل بشكل طبيعي")
            if st.button("🛑 إيقاف النظام", key="system_off_btn"):
                set_system_status("off")
                log_audit("system_off", "system", None, None, "تم إيقاف النظام")
                st.rerun()
        else:
            st.error("🔴 النظام متوقف")
            if st.button("▶️ تشغيل النظام", key="system_on_btn"):
                set_system_status("on")
                log_audit("system_on", "system", None, None, "تم تشغيل النظام")
                st.rerun()
    
    # =========================
    # سجل التدقيق
    # =========================
    elif choice == "📊 سجل التدقيق":
        st.subheader("📊 سجل التدقيق (Audit Log)")
        
        try:
            conn = get_connection()
            audit = pd.read_sql("""
                SELECT admin_name, action, target_name, details, created_at 
                FROM audit_log ORDER BY id DESC LIMIT 100
            """, conn)
            conn.close()
            
            if not audit.empty:
                st.dataframe(audit, use_container_width=True)
                
                csv = audit.to_csv(index=False).encode('utf-8')
                st.download_button("📥 تصدير إلى CSV", csv, f"audit_log_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="download_audit")
            else:
                st.info("لا توجد سجلات تدقيق")
        except Exception:
            st.info("لا توجد سجلات تدقيق بعد")
    
    # =========================
    # إدارة الصلاحيات
    # =========================
    elif choice == "👑 إدارة الصلاحيات":
        st.subheader("👑 إدارة صلاحيات المستخدمين")
        
        try:
            conn = get_connection()
            permissions = pd.read_sql("SELECT * FROM user_permissions", conn)
            conn.close()
            st.dataframe(permissions, use_container_width=True)
        except Exception:
            st.info("لا توجد بيانات صلاحيات")
        
        st.markdown("### 📝 تغيير صلاحيات مستخدم")
        
        try:
            conn = get_connection()
            users = pd.read_sql("SELECT login, name, lastname, role FROM users", conn)
            conn.close()
            
            if not users.empty:
                user_options = users.apply(lambda x: f"{x['name']} {x['lastname']} ({x['login']})", axis=1).tolist()
                selected_user = st.selectbox("اختار المستخدم", user_options, key="permission_user")
                login = selected_user.split("(")[-1].replace(")", "")
                new_role = st.selectbox("الدور الجديد", ["viewer", "tech_support", "admin", "super_admin"], key="new_role")
                
                if st.button("تحديث الصلاحية", key="update_permission"):
                    conn = get_connection()
                    conn.execute(text("UPDATE users SET role=:role WHERE login=:login"), {"role": new_role, "login": login})
                    conn.commit()
                    conn.close()
                    
                    log_audit("change_permission", "user", login, selected_user, f"تم تغيير الدور إلى {new_role}")
                    st.success("✅ تم تحديث الصلاحية")
                    st.rerun()
        except Exception as e:
            st.error(f"خطأ: {e}")
