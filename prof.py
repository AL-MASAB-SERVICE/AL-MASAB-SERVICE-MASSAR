import streamlit as st
import pandas as pd
import datetime
from database import get_connection
from sqlalchemy import text

def prof_panel():
    st.markdown("<h1 style='text-align: center; color: #4A90E2;'>👨‍🏫 تسجيل غياب التلاميذ</h1>", unsafe_allow_html=True)
    
    conn = get_connection()

    col1, col2 = st.columns(2)
    with col1:
        level = st.selectbox("السلك", ["الأولى إعدادي", "الثانية إعدادي", "الثالثة إعدادي", "جدع مشترك"])
        session = st.selectbox("اختر الحصة", ["الأولى", "الثانية", "الثالثة", "الرابعة"])
    
    with col2:
        class_num = st.text_input("رقم القسم")
        today = datetime.date.today().isoformat()
        day_mapping = {"Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء", "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"}
        day_name = day_mapping.get(datetime.date.today().strftime('%A'), datetime.date.today().strftime('%A'))

    period = st.radio("الفترة", ["صباحية", "مسائية"], horizontal=True)

    # 👇 دمج السلك + القسم
    full_class = f"{level} {class_num}"

    if st.button("🔍 بحث"):
        result = conn.execute(text("""
            SELECT id FROM classes WHERE level=:level AND class_num=:class_num
        """), {"level": level, "class_num": full_class}).fetchone()

        if result:
            st.session_state.class_id = result[0]
            st.session_state.show_list = True
            st.session_state.temp_absents = [] 
        else:
            st.error("❌ القسم غير موجود.")
            st.session_state.show_list = False

    if st.session_state.get("show_list", False):
        st.divider()
        c_id = st.session_state.class_id
        
        # 👇 نجيبو جميع التلاميذ (حتى الموقوفين)
        students = pd.read_sql(text("""
            SELECT id, name, lastname, status 
            FROM students 
            WHERE class_id=:id
        """), conn, params={"id": c_id})
        
        absent_this_session = pd.read_sql(text("""
            SELECT student_id FROM attendance 
            WHERE date=:date AND session=:session AND period=:period AND allowed = 0
        """), conn, params={
            "date": today,
            "session": session,
            "period": period
        })['student_id'].tolist()

        absent_other_sessions = pd.read_sql(text("""
            SELECT DISTINCT student_id FROM attendance 
            WHERE date=:date AND session != :session AND allowed = 0
        """), conn, params={
            "date": today,
            "session": session
        })['student_id'].tolist()

        if "temp_absents" not in st.session_state:
            st.session_state.temp_absents = []

        for i, row in students.iterrows():
            col_n, col_btn = st.columns([4, 1])
            
            is_stopped = row['status'] == "stopped_by_admin"
            is_recorded_now = row['id'] in absent_this_session
            is_absent_before = row['id'] in absent_other_sessions
            is_selected = row['id'] in st.session_state.temp_absents
            
            # 👇 ألوان
            if is_stopped:
                bg_color = "#808080"
                text_color = "white"
            else:
                bg_color = "#FF4B4B" if (is_recorded_now or is_absent_before or is_selected) else "#f9f9f9"
                text_color = "white" if bg_color == "#FF4B4B" else "black"
            
            status_info = ""
            if is_stopped:
                status_info = " (🚫 موقوف من الإدارة)"
            elif is_recorded_now:
                status_info = " (مسجل الآن)"
            elif is_absent_before:
                status_info = " (غائب سابقاً)"

            col_n.markdown(f"""
                <div style="padding:12px;border-radius:8px;border:1px solid #ddd;
                            background-color:{bg_color};color:{text_color};font-weight:bold;">
                    👤 {row['name']} {row['lastname']} {status_info}
                </div>
            """, unsafe_allow_html=True)
            
            with col_btn:
                if is_stopped:
                    st.button("🚫", key=f"stop_{row['id']}", disabled=True)
                elif is_recorded_now:
                    st.button("🔒", key=f"lock_{row['id']}", disabled=True)
                else:
                    label = "إلغاء" if is_selected else "غائب 🔴"
                    if st.button(label, key=f"abs_{row['id']}"):
                        if row['id'] not in st.session_state.temp_absents:
                            st.session_state.temp_absents.append(row['id'])
                        else:
                            st.session_state.temp_absents.remove(row['id'])
                        st.rerun()

        st.divider()
        if st.button("💾 حفظ المعلومات", type="primary", use_container_width=True):
            if st.session_state.temp_absents:
                for s_id in st.session_state.temp_absents:
                    conn.execute(text("""
                        INSERT INTO attendance (student_id, date, day, session, period, allowed)
                        VALUES (:student_id,:date,:day,:session,:period,0)
                    """), {
                        "student_id": int(s_id),
                        "date": today,
                        "day": day_name,
                        "session": session,
                        "period": period
                    })

                conn.commit()
                st.session_state.temp_absents = []
                st.success("✅ تم الحفظ")
                st.rerun()
            else:
                st.warning("⚠️ لا يوجد غياب")

    conn.close()