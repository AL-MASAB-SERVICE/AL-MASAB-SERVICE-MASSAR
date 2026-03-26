import streamlit as st
import random
import string
import pandas as pd
from database import get_connection, get_system_status, set_system_status
from sqlalchemy import text

# =========================
# 🔐 توليد معلومات
# =========================
def generate_password():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))

def generate_login(name, lastname):
    return f"{name.lower()}{lastname.lower()}@taalim.ma"

# =========================
# 🎨 Status Color
# =========================
def format_status(status):
    if status == "done":
        return "✅ تم المعالجة"
    elif status == "rejected":
        return "❌ مرفوض"
    else:
        return "⏳ في طور المعالجة"

# =========================
# 🧑‍🔧 لوحة admin
# =========================
def admin_panel():
    st.title("🧑‍🔧 Service technique")

    menu = [
        "➕ إنشاء حساب",
        "📋 عرض الحسابات",
        "🚫 توقيف حساب",
        "🔄 إعادة تفعيل حساب",
        "🔑 تغيير كلمة المرور",
        "🗑️ حذف حساب",
        "📩 الشكايات",
        "🔌 التحكم في النظام"
    ]

    choice = st.sidebar.selectbox("القائمة", menu)

    # =========================
    # ➕ إنشاء حساب
    # =========================
    if choice == "➕ إنشاء حساب":
        st.subheader("إنشاء حساب جديد")

        name = st.text_input("الإسم")
        lastname = st.text_input("النسب")
        phone = st.text_input("الهاتف")
        subject = st.text_input("المادة")
        role = st.selectbox("الدور", ["prof", "surveillant", "directeur", "parents"])

        if st.button("إنشاء"):
            login = generate_login(name, lastname)
            password = generate_password()

            conn = get_connection()
            conn.execute(text("""
            INSERT INTO users (login, password, role, name, lastname, phone, subject, status)
            VALUES (:login,:password,:role,:name,:lastname,:phone,:subject,'active')
            """), {
                "login": login,
                "password": password,
                "role": role,
                "name": name,
                "lastname": lastname,
                "phone": phone,
                "subject": subject
            })

            conn.commit()
            conn.close()

            st.success(f"Login: {login}")
            st.warning(f"Password: {password}")

    # =========================
    # 📋 عرض الحسابات
    # =========================
    elif choice == "📋 عرض الحسابات":
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM users", conn)
        conn.close()
        st.dataframe(df)

    # =========================
    # 🚫 توقيف حساب
    # =========================
    elif choice == "🚫 توقيف حساب":
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM users WHERE status='active'", conn)
        conn.close()

        if not df.empty:
            user = st.selectbox("اختار الحساب", df["login"])
            if st.button("توقيف"):
                conn = get_connection()
                conn.execute(text("UPDATE users SET status='stopped' WHERE login=:login"), {"login": user})
                conn.commit()
                conn.close()
                st.success("تم التوقيف")
                st.rerun()

    # =========================
    # 🔄 إعادة تفعيل
    # =========================
    elif choice == "🔄 إعادة تفعيل حساب":
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM users WHERE status='stopped'", conn)
        conn.close()

        if not df.empty:
            user = st.selectbox("اختار الحساب", df["login"])
            if st.button("تفعيل"):
                conn = get_connection()
                conn.execute(text("UPDATE users SET status='active' WHERE login=:login"), {"login": user})
                conn.commit()
                conn.close()
                st.success("تم التفعيل")
                st.rerun()

    # =========================
    # 🔑 تغيير password
    # =========================
    elif choice == "🔑 تغيير كلمة المرور":
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM users", conn)
        conn.close()

        if not df.empty:
            user = st.selectbox("اختار الحساب", df["login"])
            new_password = st.text_input("كلمة المرور الجديدة", type="password")

            if st.button("تحديث"):
                conn = get_connection()
                conn.execute(
                    text("UPDATE users SET password=:p WHERE login=:l"),
                    {"p": new_password, "l": user}
                )
                conn.commit()
                conn.close()
                st.success("تم التحديث")

    # =========================
    # 🗑️ حذف
    # =========================
    elif choice == "🗑️ حذف حساب":
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM users", conn)
        conn.close()

        if not df.empty:
            user = st.selectbox("اختار الحساب", df["login"])
            if st.button("حذف"):
                conn = get_connection()
                conn.execute(text("DELETE FROM users WHERE login=:l"), {"l": user})
                conn.commit()
                conn.close()
                st.success("تم الحذف")
                st.rerun()

    # =========================
    # 📩 الشكايات
    # =========================
    elif choice == "📩 الشكايات":
        st.subheader("📩 Gestion des réclamations")

        conn = get_connection()
        df = pd.read_sql("SELECT * FROM reclamations ORDER BY id DESC", conn)
        conn.close()

        if df.empty:
            st.info("لا توجد شكايات")
        else:
            for _, row in df.iterrows():
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.markdown(f"""
                    🆔 #{row['id']} - {row['login']}  
                    الحالة: {format_status(row['status'])}
                    """)

                with col2:
                    if st.button("🔍", key=f"view_{row['id']}"):
                        st.session_state.selected_rec = row['id']

            if "selected_rec" in st.session_state:
                rec_id = st.session_state.selected_rec

                conn = get_connection()
                rec = pd.read_sql("SELECT * FROM reclamations WHERE id=%s", conn, params=(rec_id,))
                conn.close()

                if not rec.empty:
                    rec = rec.iloc[0]

                    st.divider()
                    st.subheader(f"📄 شكاية #{rec['id']}")
                    st.write(f"👤 {rec['login']}")
                    st.write(f"📌 الموضوع: {rec['subject']}")
                    st.write(f"📝 الرسالة: {rec['message']}")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button("✅ تم المعالجة"):
                            conn = get_connection()
                            conn.execute(text("UPDATE reclamations SET status='done' WHERE id=:id"), {"id": rec_id})
                            conn.commit()
                            conn.close()
                            st.success("تمت المعالجة")
                            del st.session_state.selected_rec
                            st.rerun()

                    with col2:
                        if st.button("❌ رفض"):
                            conn = get_connection()
                            conn.execute(text("UPDATE reclamations SET status='rejected' WHERE id=:id"), {"id": rec_id})
                            conn.commit()
                            conn.close()
                            st.error("تم الرفض")
                            del st.session_state.selected_rec
                            st.rerun()

                    with col3:
                        if st.button("🔙 خروج"):
                            del st.session_state.selected_rec
                            st.rerun()

    # =========================
    # 🔌 النظام
    # =========================
    elif choice == "🔌 التحكم في النظام":
        status = get_system_status()
        st.write(f"الحالة: {status}")

        if st.button("🚫 إيقاف"):
            set_system_status("off")
            st.rerun()

        if st.button("✅ تشغيل"):
            set_system_status("on")
            st.rerun()