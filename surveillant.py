import streamlit as st
import pandas as pd
from database import get_connection
from sqlalchemy import text

def surveillant_panel():
    st.markdown("<h1 style='text-align: center; color: #2E86C1;'>🧑‍💼 تتبع غياب التلاميذ</h1>", unsafe_allow_html=True)
    
    conn = get_connection()

    col1, col2 = st.columns(2)
    with col1:
        level = st.selectbox("يرجى اختيار السلك المناسب", ["الأولى إعدادي", "الثانية إعدادي", "الثالثة إعدادي", "جدع مشترك"])
    with col2:
        class_num = st.text_input("رقم القسم")

    # 👇 دمج السلك + القسم
    full_class = f"{level} {class_num}"

    if st.button("🔎 بحث"):
        st.session_state.view_class = True
    
    if st.session_state.get("view_class", False):
        st.divider()
        
        query = text("""
            SELECT a.id as abs_id, s.id as std_id, s.name, s.lastname, s.status,
                   a.date, a.session, a.period, a.allowed
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            JOIN classes c ON s.class_id = c.id
            WHERE c.level = :level AND c.class_num = :class_num
            ORDER BY a.date DESC, a.session ASC
        """)

        df = pd.read_sql(query, conn, params={
            "level": level,
            "class_num": full_class
        })

        if df.empty:
            st.success("✅ لا يوجد سجل غياب لهذا القسم.")
        else:
            students_with_abs = df[['std_id', 'name', 'lastname', 'status']].drop_duplicates()

            for _, std in students_with_abs.iterrows():
                unallowed_abs = df[(df['std_id'] == std['std_id']) & (df['allowed'] == 0)]
                full_history = df[df['std_id'] == std['std_id']]

                total_hours = len(unallowed_abs)

                is_stopped = std['status'] == "stopped_by_admin"

                title = f"👤 {std['name']} {std['lastname']} | الساعات غير المبررة: {total_hours}"
                if is_stopped:
                    title += " 🚫 (موقوف من الإدارة)"

                with st.expander(title):
                    
                    if is_stopped:
                        st.error("🚫 هذا التلميذ موقوف من طرف المدير ولا يمكن السماح له بالدخول")
                    
                    elif total_hours > 0:
                        st.markdown("<h4 style='color:red;'>⏳ غيابات تنتظر السماح بالدخول</h4>", unsafe_allow_html=True)
                        
                        dates = unallowed_abs['date'].unique()
                        for d in dates:
                            day_abs = unallowed_abs[unallowed_abs['date'] == d]
                            st.markdown(f"📅 يوم {d} (🕕 عدد الساعات: {len(day_abs)})")
                            for _, row in day_abs.iterrows():
                                st.write(f"🔹 الحصة {row['session']} - الفترة {row['period']}")
                        
                        if st.button(f"✅ السماح بي الدخول لـ {std['name']}", key=f"btn_{std['std_id']}"):

                            conn.execute(text("""
                                UPDATE attendance 
                                SET allowed = 1 
                                WHERE student_id = :id AND allowed = 0
                            """), {
                                "id": int(std['std_id'])
                            })

                            conn.commit()
                            st.success("تم السماح بالدخول")
                            st.rerun()
                    else:
                        st.success("✅ التلميذ حاضر")

                    st.divider()
                    with st.expander("🗂️ أرشيف الغياب الكامل"):
                        if full_history.empty:
                            st.write("الأرشيف فارغ.")
                        else:
                            archive_df = full_history[['date', 'session', 'period', 'allowed']].copy()
                            archive_df['الحالة'] = archive_df['allowed'].apply(lambda x: "مبرر" if x==1 else "غير مبرر")
                            st.table(archive_df[['date', 'session', 'period', 'الحالة']])

    conn.close()