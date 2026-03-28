import streamlit as st
import pandas as pd
import datetime
from database import get_connection
from sqlalchemy import text

def prof_panel():
    st.sidebar.title("📚 لوحة الأستاذ")

    menu = [
        "📌 تسجيل الغياب",
        "✏️ تعديل آخر غياب",
        "📩 تقرير سلوك",
        "📊 إحصائيات",
        "📝 التنقيط",
    ]

    choice = st.sidebar.selectbox("اختار", menu)

    conn = get_connection()

    # =========================
    # 📌 تسجيل الغياب
    # =========================
    if choice == "📌 تسجيل الغياب":
        st.markdown(
            "<h1 style='text-align: center; color: #4A90E2;'>👨‍🏫 تسجيل غياب التلاميذ</h1>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            level = st.selectbox(
                "السلك", ["الأولى إعدادي", "الثانية إعدادي", "الثالثة إعدادي", "جدع مشترك"]
            )
            session = st.selectbox(
                "اختر الحصة", ["الأولى", "الثانية", "الثالثة", "الرابعة"]
            )
        with col2:
            class_num = st.text_input("رقم القسم")
            today = datetime.date.today().isoformat()
            day_mapping = {
                "Monday": "الإثنين",
                "Tuesday": "الثلاثاء",
                "Wednesday": "الأربعاء",
                "Thursday": "الخميس",
                "Friday": "الجمعة",
                "Saturday": "السبت",
                "Sunday": "الأحد",
            }
            day_name = day_mapping.get(
                datetime.date.today().strftime("%A"), datetime.date.today().strftime("%A")
            )
            period = st.radio("الفترة", ["صباحية", "مسائية"], horizontal=True)

        full_class = f"{level} {class_num}"

        if st.button("🔍 بحث"):
            result = conn.execute(
                text(""" SELECT id FROM classes WHERE level=:level AND class_num=:class_num """),
                {"level": level, "class_num": full_class},
            ).fetchone()
            if result:
                st.session_state.class_id = result[0]
                st.session_state.show_list = True
                st.session_state.temp_absents = []
            else:
                st.error("❌ القسم غير موجود.")
                st.session_state.show_list = False

        if st.session_state.get("show_list", False):
            st.subheader("🚨 التلاميذ الموجهين للإدارة")
            directed = pd.read_sql(
                text("""
                    SELECT s.id AS numero, s.name || ' ' || s.lastname AS full_name, COUNT(a.id) AS total_absences
                    FROM attendance a
                    JOIN students s ON s.id = a.student_id
                    JOIN classes c ON c.id = s.class_id
                    WHERE c.level = :level AND c.class_num = :class_num AND a.allowed = 0
                    GROUP BY s.id, s.name, s.lastname
                    ORDER BY total_absences DESC
                """),
                conn,
                params={"level": level, "class_num": full_class},
            )
            if not directed.empty:
                directed = directed[["numero", "full_name", "total_absences"]]
                directed.columns = ["رقم التلميذ", "الاسم الكامل", "عدد الحصص الغياب"]
                st.dataframe(directed, use_container_width=True)
            else:
                st.success("لا يوجد تلاميذ موجهين")

        if st.session_state.get("show_list", False):
            st.divider()
            c_id = st.session_state.class_id
            students = pd.read_sql(
                text(""" SELECT id, name, lastname, status FROM students WHERE class_id=:id """),
                conn,
                params={"id": c_id},
            )

            absent_this_session = pd.read_sql(
                text(""" SELECT student_id FROM attendance WHERE date=:date AND session=:session AND period=:period AND allowed = 0 """),
                conn,
                params={"date": today, "session": session, "period": period},
            )["student_id"].tolist()

            absent_other_sessions = pd.read_sql(
                text(""" SELECT DISTINCT student_id FROM attendance WHERE date=:date AND session != :session AND allowed = 0 """),
                conn,
                params={"date": today, "session": session},
            )["student_id"].tolist()

            if "temp_absents" not in st.session_state:
                st.session_state.temp_absents = []

            for i, row in students.iterrows():
                col_n, col_btn = st.columns([4, 1])
                is_stopped = row["status"] == "stopped_by_admin"
                is_recorded_now = row["id"] in absent_this_session
                is_absent_before = row["id"] in absent_other_sessions
                is_selected = row["id"] in st.session_state.temp_absents

                if is_stopped:
                    bg_color = "#808080"
                    text_color = "white"
                else:
                    bg_color = (
                        "#FF4B4B"
                        if (is_recorded_now or is_absent_before or is_selected)
                        else "#f9f9f9"
                    )
                    text_color = "white" if bg_color == "#FF4B4B" else "black"

                status_info = ""
                if is_stopped:
                    status_info = " (🚫 موقوف من الإدارة)"
                elif is_recorded_now:
                    status_info = " (مسجل الآن)"
                elif is_absent_before:
                    status_info = " (غائب سابقاً)"

                col_n.markdown(
                    f"""
                    <div style="padding:12px;border-radius:8px;border:1px solid #ddd; background-color:{bg_color};color:{text_color};font-weight:bold;">
                        👤 {row['name']} {row['lastname']} {status_info}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                with col_btn:
                    if is_stopped:
                        st.button("🚫", key=f"stop_{row['id']}", disabled=True)
                    elif is_recorded_now:
                        st.button("🔒", key=f"lock_{row['id']}", disabled=True)
                    else:
                        label = "إلغاء" if is_selected else "غائب 🔴"
                        if st.button(label, key=f"abs_{row['id']}"):
                            if row["id"] not in st.session_state.temp_absents:
                                st.session_state.temp_absents.append(row["id"])
                            else:
                                st.session_state.temp_absents.remove(row["id"])
                            st.rerun()

            st.divider()

            if st.button("💾 حفظ المعلومات", type="primary", use_container_width=True):
                if st.session_state.temp_absents:
                    for s_id in st.session_state.temp_absents:
                        conn.execute(
                            text("""
                                INSERT INTO attendance (student_id, date, day, session, period, allowed)
                                VALUES (:student_id,:date,:day,:session,:period,0)
                            """),
                            {
                                "student_id": int(s_id),
                                "date": today,
                                "day": day_name,
                                "session": session,
                                "period": period,
                            },
                        )
                    conn.commit()
                    st.session_state.temp_absents = []
                    st.success("✅ تم الحفظ")
                    st.rerun()
                else:
                    st.warning("⚠️ لا يوجد غياب")

    # =========================
    # ✏️ تعديل آخر غياب
    # =========================
    elif choice == "✏️ تعديل آخر غياب":
        st.title("✏️ تعديل الغياب")
        df = pd.read_sql(
            """ SELECT * FROM attendance ORDER BY id DESC LIMIT 20 """,
            conn,
        )
        for _, row in df.iterrows():
            col1, col2 = st.columns([4, 1])
            col1.write(f"{row['student_id']} - {row['date']}")
            if col2.button("❌ حذف", key=row["id"]):
                conn.execute(text("DELETE FROM attendance WHERE id=:id"), {"id": row["id"]})
                conn.commit()
                st.rerun()

    # =========================
    # 📩 تقرير سلوك
    # =========================
    elif choice == "📩 تقرير سلوك":
        st.title("📩 تقرير سوء السلوك")
        name = st.text_input("اسم التلميذ")
        classe = st.text_input("القسم")
        number = st.text_input("رقم التلميذ")
        teacher = st.session_state.get("name", "")
        behavior = st.selectbox(
            "نوع السلوك",
            ["ضرب تلميذ", "تهجم على الأستاذ", "استفزاز", "كلام نابي", "حالة غير طبيعية"],
        )
        details = st.text_area("تفاصيل")

        if st.button("💾 حفظ"):
            conn.execute(
                text("""
                    INSERT INTO reports (student, class, number, teacher, behavior, details)
                    VALUES (:s,:c,:n,:t,:b,:d)
                """),
                {
                    "s": name,
                    "c": classe,
                    "n": number,
                    "t": teacher,
                    "b": behavior,
                    "d": details,
                },
            )
            conn.commit()
            st.success("تم الإرسال")

    # =========================
    # 📊 إحصائيات الغياب
    # =========================
    elif choice == "📊 إحصائيات":
        st.title("📊 إحصائيات الغياب")
        df = pd.read_sql(
            """ SELECT student_id, COUNT(*) as total FROM attendance GROUP BY student_id """,
            conn,
        )
        st.dataframe(df)

    # =========================
    # 📝 التنقيط (FINAL FIX - كل أستاذ لوحدو)
    # =========================
    elif choice == "📝 التنقيط":
        st.title("📝 تسجيل النقط")

        try:
            conn.rollback()
        except:
            pass

        teacher_login = str(st.session_state.get("login", "")).strip()
        teacher_name = str(st.session_state.get("name", "")).strip()
        subject = str(st.session_state.get("subject", "")).strip()

        if not subject or not teacher_login:
            st.error("❌ مشكل في تسجيل الدخول")
            st.stop()

        st.info(f"👨‍🏫 الأستاذ: {teacher_name}")
        st.info(f"📘 المادة: {subject}")

        st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"] {
            direction: rtl;
        }
        input[type=number]::-webkit-inner-spin-button,
        input[type=number]::-webkit-outer-spin-button {
            display: none;
        }
        </style>
        """, unsafe_allow_html=True)

        level = st.selectbox("السلك", ["الأولى إعدادي", "الثانية إعدادي", "الثالثة إعدادي", "جدع مشترك"])
        class_num = st.text_input("رقم القسم")

        full_class = f"{level} {class_num}"

        if st.button("🔍 بحث"):
            result = conn.execute(text("""
                SELECT id FROM classes
                WHERE level=:level AND class_num=:class_num
            """), {"level": level, "class_num": full_class}).fetchone()

            if not result:
                st.error("❌ القسم غير موجود")
                st.session_state.show_grades = False
            else:
                st.session_state.class_id = result[0]
                st.session_state.show_grades = True

        if st.session_state.get("show_grades", False):
            class_id = st.session_state.class_id

            # التحقق من وجود أستاذ آخر سجل نقاط
            other_teachers = conn.execute(text("""
                SELECT DISTINCT teacher_login FROM grades
                WHERE class_id=:class_id 
                AND subject=:subject
                AND teacher_login != :teacher
            """), {
                "class_id": class_id,
                "subject": subject,
                "teacher": teacher_login
            }).fetchall()

            if other_teachers:
                other_names = [t[0] for t in other_teachers]
                st.error(f"❌ هذا القسم مسجل من قبل الأستاذ: {', '.join(other_names)}")
                st.warning("⚠️ لا يمكنك تعديل نقاط أستاذ آخر")
                st.stop()

            # 📥 جلب التلاميذ
            students = pd.read_sql(text("""
                SELECT id, name, lastname FROM students
                WHERE class_id=:id
            """), conn, params={"id": class_id})

            if students.empty:
                st.warning("⚠️ لا يوجد تلاميذ")
                st.stop()

            st.subheader("📋 لائحة التنقيط")

            col_name, c1, c2, c3, c4, c5 = st.columns([3,1,1,1,1,1])
            col_name.write("👤 الاسم الكامل")
            c1.write("الفرض الأول")
            c2.write("الفرض التاني")
            c3.write("الفرض التالت")
            c4.write("الفرض الرابع")
            c5.write("الأنشطة المندمجة")

            data = []

            for _, s in students.iterrows():
                # جلب النقط الخاصة بهذا الأستاذ فقط
                old = conn.execute(text("""
                    SELECT id, n1, n2, n3, n4, activity FROM grades
                    WHERE student_id=:id 
                    AND class_id=:class_id 
                    AND subject=:subject
                    AND teacher_login=:teacher
                """), {
                    "id": s['id'],
                    "class_id": class_id,
                    "subject": subject,
                    "teacher": teacher_login,
                }).fetchone()

                if old:
                    gid = old[0]
                    n1_old, n2_old, n3_old, n4_old, act_old = old[1:]
                else:
                    gid = None
                    n1_old = n2_old = n3_old = n4_old = act_old = 0.0

                col_name, c1, c2, c3, c4, c5 = st.columns([3,1,1,1,1,1])

                col_name.write(f"{s['name']} {s['lastname']}")

                # مفاتيح فريدة تشمل teacher_login لمنع التداخل
                n1 = c1.number_input("", min_value=0.0, max_value=20.0, value=float(n1_old), step=0.01, format="%.2f", key=f"n1_{s['id']}_{teacher_login}")
                n2 = c2.number_input("", min_value=0.0, max_value=20.0, value=float(n2_old), step=0.01, format="%.2f", key=f"n2_{s['id']}_{teacher_login}")
                n3 = c3.number_input("", min_value=0.0, max_value=20.0, value=float(n3_old), step=0.01, format="%.2f", key=f"n3_{s['id']}_{teacher_login}")
                n4 = c4.number_input("", min_value=0.0, max_value=20.0, value=float(n4_old), step=0.01, format="%.2f", key=f"n4_{s['id']}_{teacher_login}")
                act = c5.number_input("", min_value=0.0, max_value=20.0, value=float(act_old), step=0.01, format="%.2f", key=f"act_{s['id']}_{teacher_login}")

                data.append((s['id'], gid, n1, n2, n3, n4, act))

            st.divider()

            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
            from reportlab.lib import colors

            def generate_pdf(data, students):
                pdf = SimpleDocTemplate("grades_report.pdf")
                table_data = [["الاسم الكامل", "الفرض الأول", "الفرض الثاني", "الفرض التالت", "الفرض الرابع", "الأنشطة المندمحة"]]

                for i, s in enumerate(students.itertuples()):
                    d = data[i]
                    table_data.append([
                        f"{s.name} {s.lastname}",
                        d[2], d[3], d[4], d[5], d[6]
                    ])

                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.grey),
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                ]))
                pdf.build([table])

            if st.button("💾 حفظ جميع النقط", use_container_width=True):
                try:
                    for d in data:
                        student_id, gid, n1, n2, n3, n4, act = d

                        if gid:
                            # تحديث السجل الموجود (مضمون أنه للأستاذ الحالي)
                            conn.execute(text("""
                                UPDATE grades SET
                                    n1=:n1,
                                    n2=:n2,
                                    n3=:n3,
                                    n4=:n4,
                                    activity=:act
                                WHERE id=:gid
                            """), {
                                "gid": gid,
                                "n1": n1,
                                "n2": n2,
                                "n3": n3,
                                "n4": n4,
                                "act": act
                            })
                        else:
                            # إنشاء سجل جديد للأستاذ الحالي
                            conn.execute(text("""
                                INSERT INTO grades 
                                (student_id, class_id, teacher_login, subject, n1, n2, n3, n4, activity)
                                VALUES (:id, :class_id, :teacher, :subject, :n1, :n2, :n3, :n4, :act)
                            """), {
                                "id": student_id,
                                "class_id": class_id,
                                "teacher": teacher_login,
                                "subject": subject,
                                "n1": n1,
                                "n2": n2,
                                "n3": n3,
                                "n4": n4,
                                "act": act
                            })

                    conn.commit()
                    generate_pdf(data, students)
                    st.success("✅ تم الحفظ + إنشاء PDF")
                    st.rerun()

                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ خطأ: {e}")