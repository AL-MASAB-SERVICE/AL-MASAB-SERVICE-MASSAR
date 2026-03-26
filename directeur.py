import streamlit as st  
import pandas as pd  
import random  
import string  
from database import get_connection  
from sqlalchemy import text  
  
def generate_password():  
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))  
  
def generate_login(name, lastname):  
    return f"{name.lower().replace(' ', '')}{lastname.lower().replace(' ', '')}@taalim.ma"  
  
def find_column(columns, keywords):  
    for key in keywords:  
        for col in columns:  
            if key in str(col).lower():  
                return col  
    return None  
  
def directeur_panel():  
    st.markdown("<h1 style='text-align: center;'>🤵 لوحة المدير</h1>", unsafe_allow_html=True)  
      
    menu = [  
        "➕ إضافة قسم جديد (Excel)",   
        "🗑️ حذف قسم",  
        "👤 إضافة تلميذ يدوي",   
        "🚫 توقيف تلميذ",   
        "✅ إرجاع تلميذ موقوف",  
        "📊 إحصائيات الغياب",  
        "🔐 إضافة Login"  
    ]  
  
    choice = st.sidebar.selectbox("القائمة", menu)  
    conn = get_connection()  
  
    # ===============================  
    # ➕ إضافة قسم + Excel  
    # ===============================  
    if choice == "➕ إضافة قسم جديد (Excel)":  
        level = st.selectbox("السلك", ["الأولى إعدادي","الثانية إعدادي","الثالثة إعدادي","جدع مشترك"])  
        class_num = st.text_input("رقم القسم")  
        file = st.file_uploader("Excel")  
  
        if st.button("حفظ"):  
            if file:  
                df = pd.read_excel(file).fillna("")  

                full_class = f"{level} {class_num}"
  
                conn.execute(text("""  
                INSERT INTO classes (level,class_num)  
                VALUES (:level,:class_num)  
                ON CONFLICT DO NOTHING  
                """), {"level": level, "class_num": full_class})  
  
                result = conn.execute(text("""  
                    SELECT id FROM classes WHERE level=:level AND class_num=:class_num  
                """), {"level": level, "class_num": full_class}).fetchone()  
  
                c_id = result[0]  
  
                df.columns = df.columns.str.strip()

                for _, row in df.iterrows():  
                    conn.execute(text("""  
                    INSERT INTO students (name,lastname,birth,number,gender,class_id,status)  
                    VALUES (:name,:lastname,:birth,:number,:gender,:class_id,'active')  
                    """), {  
                         "name": row["الإسم"],
                         "lastname": row["النسب"],
                         "birth": row["تاريخ الإزدياد"],
                         "number": row["ر.ت"],
                         "gender": row["النوع"],
                         "class_id": c_id  
                    })  
  
                conn.commit()  
                st.success("تم إنشاء القسم")  
  
    # ===============================  
    # 🗑️ حذف قسم  
    # ===============================  
    elif choice == "🗑️ حذف قسم":  
        df = pd.read_sql("SELECT * FROM classes", conn)  
  
        if not df.empty:  
            selected = st.selectbox("اختار القسم", df["class_num"])  
  
            if st.button("حذف"):  
  
                conn.execute(text("""  
                    DELETE FROM attendance WHERE student_id IN  
                    (SELECT id FROM students WHERE class_id IN  
                    (SELECT id FROM classes WHERE class_num=:cls))  
                """), {"cls": selected})  
  
                conn.execute(text("""  
                    DELETE FROM students WHERE class_id IN  
                    (SELECT id FROM classes WHERE class_num=:cls)  
                """), {"cls": selected})  
  
                conn.execute(text("DELETE FROM classes WHERE class_num=:cls"), {"cls": selected})  
  
                conn.commit()  
                st.success("تم الحذف")  
                st.rerun()  
  
    # ===============================  
    # 👤 إضافة تلميذ  
    # ===============================  
    elif choice == "👤 إضافة تلميذ يدوي":  
        name = st.text_input("الإسم")  
        lastname = st.text_input("النسب")  
        level = st.text_input("السلك")  
        class_num = st.text_input("القسم")  
  
        if st.button("إضافة"):  
            full_class = f"{level} {class_num}"

            res = conn.execute(text("""  
                SELECT id FROM classes WHERE class_num=:class_num  
            """), {"class_num": full_class}).fetchone()  
  
            if res:  
                conn.execute(text("""  
                INSERT INTO students (name,lastname,class_id,status)  
                VALUES (:name,:lastname,:class_id,'active')  
                """), {"name": name, "lastname": lastname, "class_id": res[0]})  
  
                conn.commit()  
                st.success("تمت الإضافة")  
            else:  
                st.error("القسم غير موجود")  
  
    # ===============================  
    # 🚫 توقيف تلميذ  
    # ===============================  
    elif choice == "🚫 توقيف تلميذ":  
        level = st.selectbox("السلك", ["الأولى إعدادي","الثانية إعدادي","الثالثة إعدادي","جدع مشترك"])  
        class_num = st.text_input("رقم القسم")  

        if st.button("بحث"):
            st.session_state.stop_search = True

        if st.session_state.get("stop_search", False):
            full_class = f"{level} {class_num}"

            students = pd.read_sql("""
                SELECT s.id, s.name, s.lastname
                FROM students s
                JOIN classes c ON s.class_id = c.id
                WHERE c.class_num = %s AND s.status='active'
            """, conn, params=(full_class,))

            for _, row in students.iterrows():
                col1, col2 = st.columns([4,1])

                col1.write(f"{row['name']} {row['lastname']}")

                if col2.button("🚫 توقيف", key=f"stop_{row['id']}"):
                    conn.execute(text("""
                        UPDATE students SET status='stopped_by_admin' WHERE id=:id
                    """), {"id": row['id']})
                    conn.commit()
                    st.rerun()

    # ===============================  
    # ✅ إرجاع تلميذ  
    # ===============================  
    elif choice == "✅ إرجاع تلميذ موقوف":  
        level = st.selectbox("السلك", ["الأولى إعدادي","الثانية إعدادي","الثالثة إعدادي","جدع مشترك"])  
        class_num = st.text_input("رقم القسم")  

        if st.button("بحث"):
            st.session_state.return_search = True

        if st.session_state.get("return_search", False):
            full_class = f"{level} {class_num}"

            students = pd.read_sql("""
                SELECT s.id, s.name, s.lastname
                FROM students s
                JOIN classes c ON s.class_id = c.id
                WHERE c.class_num = %s AND s.status='stopped_by_admin'
            """, conn, params=(full_class,))

            for _, row in students.iterrows():
                col1, col2 = st.columns([4,1])

                col1.write(f"{row['name']} {row['lastname']}")

                if col2.button("✅ إرجاع", key=f"return_{row['id']}"):
                    conn.execute(text("""
                        UPDATE students SET status='active' WHERE id=:id
                    """), {"id": row['id']})
                    conn.commit()
                    st.rerun()

    # ===============================  
    # 📊 إحصائيات الغياب  
    # ===============================  
    elif choice == "📊 إحصائيات الغياب":  
        level = st.selectbox("السلك", ["الأولى إعدادي","الثانية إعدادي","الثالثة إعدادي","جدع مشترك"])  
        class_num = st.text_input("رقم القسم")  

        if st.button("عرض"):
            st.session_state.stat_search = True

        if st.session_state.get("stat_search", False):
            full_class = f"{level} {class_num}"

            students = pd.read_sql("""
                SELECT s.id, s.name, s.lastname
                FROM students s
                JOIN classes c ON s.class_id = c.id
                WHERE c.class_num = %s
            """, conn, params=(full_class,))

            for _, row in students.iterrows():
                if st.button(f"📊 {row['name']} {row['lastname']}", key=f"stat_{row['id']}"):

                    absences = pd.read_sql("""
                        SELECT date, session, period, allowed
                        FROM attendance
                        WHERE student_id=%s
                        ORDER BY date ASC
                    """, conn, params=(row['id'],))

                    if absences.empty:
                        st.info("لا يوجد غياب")
                    else:
                        absences['الحالة'] = absences['allowed'].apply(lambda x: "مبرر" if x==1 else "غير مبرر")
                        st.dataframe(absences)

    # ===============================  
    # 🔐 إنشاء Login  
    # ===============================  
    elif choice == "🔐 إضافة Login":  
        name = st.text_input("الإسم")  
        lastname = st.text_input("النسب")  
        role = st.selectbox("الدور", ["prof", "surveillant"])  
  
        if st.button("إنشاء"):  
            login = generate_login(name, lastname)  
            password = generate_password()  
  
            conn.execute(text("""  
            INSERT INTO users (login,password,role,name,lastname,status)  
            VALUES (:login,:password,:role,:name,:lastname,'active')  
            """), {  
                "login": login,  
                "password": password,  
                "role": role,  
                "name": name,  
                "lastname": lastname  
            })  
  
            conn.commit()  
  
            st.success(f"Login: {login}")  
            st.warning(f"Password: {password}")  
  
    conn.close()