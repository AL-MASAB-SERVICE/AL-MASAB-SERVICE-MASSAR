import streamlit as st  
from datetime import datetime  
import pandas as pd  
from database import get_connection  
from pdf_utils import generate_pdf  
from sqlalchemy import text  
import plotly.graph_objects as go  
  
# =========================  
# 🔢 توليد رقم فريد  
# =========================  
def generate_number(prefix="N°"):  
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}"  
  
# =========================  
# 🎯 MAIN PANEL  
# =========================  
def parents_panel(user_login):  
  
    st.title("👨‍👩‍👧‍👦 جمعية آباء وأمهات التلاميذ")  
  
    menu = [  
        "💰 مدخول الجمعية",  
        "📊 إحصائيات المؤسسة",  
        "📁 المشاريع",  
        "⚙️ معالجة المشاريع",  
        "🎉 تنظيم حفلة",  
        "🖼️ عرض الحفلات"  
    ]  
  
    choice = st.sidebar.selectbox("القائمة", menu)  
  
    # =========================  
    # 💰 مدخول الجمعية  
    # =========================  
    if choice == "💰 مدخول الجمعية":  
  
        st.subheader("إضافة مدخول")  
  
        amount = st.number_input("المبلغ بالدرهم", min_value=0.0)  
        source = st.text_input("المصدر")  
        contributors = st.text_area("المساهمين")  
        collector = st.text_input("المكلف بجمع المال")  
        report = st.text_area("تقرير شامل")  
  
        today = datetime.now()  
  
        if st.button("حفظ المعلومات"):  
  
            ref = generate_number()  
  
            conn = get_connection()  
  
            conn.execute(text("""  
                INSERT INTO finance (amount, source, created_by, type)  
                VALUES (:amount, :source, :user, 'income')  
            """), {  
                "amount": amount,  
                "source": source,  
                "user": user_login  
            })  
  
            conn.commit()  
            conn.close()  
  
            pdf = generate_pdf("مدخول الجمعية", {  
                "رقم العملية": ref,  
                "المبلغ": amount,  
                "المصدر": source,  
                "المساهمين": contributors,  
                "المكلف": collector,  
                "التاريخ": today,  
                "التقرير": report  
            })  
  
            st.success("تم الحفظ بنجاح")  
            st.download_button("📄 تحميل PDF", pdf, f"{ref}.pdf")  
  
    # =========================  
    # 📊 إحصائيات  
    # =========================  
    elif choice == "📊 إحصائيات المؤسسة":  
  
        conn = get_connection()  
        df = pd.read_sql("SELECT * FROM finance ORDER BY created_at", conn)  
        conn.close()  
  
        income = df[df['type'] == 'income']['amount'].sum()  
        expense = df[df['type'] == 'expense']['amount'].sum()  
        total = income - expense  
  
        if len(df) > 1:  
            last = df.iloc[-1]['amount']  
            prev = df.iloc[-2]['amount']  
            delta_val = last - prev  
        else:  
            delta_val = 0  
  
        col1, col2, col3 = st.columns(3)  
  
        col1.metric("💰 الميزانية", total)  
  
        col2.metric("📈 المدخول", income, delta=delta_val)  
  
        col3.metric("📉 المصاريف", expense, delta=-delta_val)  
  
        df['created_at'] = pd.to_datetime(df['created_at'])  
  
        daily = df.groupby(['created_at', 'type'])['amount'].sum().unstack().fillna(0)  
  
        if 'income' not in daily:  
            daily['income'] = 0  
        if 'expense' not in daily:  
            daily['expense'] = 0  
  
        daily['balance'] = daily['income'] - daily['expense']  
  
        fig = go.Figure()  
  
        fig.add_trace(go.Scatter(  
            x=daily.index,  
            y=daily['income'],  
            mode='lines+markers',  
            name='📈 المدخول',  
            line=dict(color='green', width=3)  
        ))  
  
        fig.add_trace(go.Scatter(  
            x=daily.index,  
            y=daily['expense'],  
            mode='lines+markers',  
            name='📉 المصاريف',  
            line=dict(color='red', width=3)  
        ))  
  
        fig.update_layout(  
            title="📊 تحليل الميزانية",  
            template="plotly_dark"  
        )  
  
        st.plotly_chart(fig, use_container_width=True)  
  
        st.markdown("### 📂 التفاصيل")  
  
        colA, colB = st.columns(2)  
  
        if colA.button("📂 عرض كل المدخول"):  
            st.dataframe(df[df['type'] == 'income'])  
  
        if colB.button("📂 عرض كل المصاريف"):  
            st.dataframe(df[df['type'] == 'expense'])  
  
    # =========================  
    # 📁 المشاريع  
    # =========================  
    elif choice == "📁 المشاريع":  
  
        st.subheader("إنشاء مشروع")  
  
        name = st.text_input("نوع المشروع")  
        budget = st.number_input("الميزانية", min_value=0.0)  
        report = st.text_area("📄 تقرير المشروع")  
        objectives = st.text_area("🎯 أهداف المشروع")  
        execution_plan = st.text_area("🛠️ طريقة التنفيذ")  
        contributors = st.text_area("المساهمين")  
        supervisors = st.text_area("المؤطرين")  
  
        if st.button("حفظ المشروع"):  
  
            ref = generate_number("P°")  
  
            full_report = f"""  
التقرير: {report}  
الأهداف: {objectives}  
طريقة التنفيذ: {execution_plan}  
"""  
  
            conn = get_connection()  
  
            conn.execute(text("""  
                INSERT INTO projects (name, budget, report, contributors)  
                VALUES (:name, :budget, :report, :contributors)  
            """), {  
                "name": name,  
                "budget": budget,  
                "report": full_report,  
                "contributors": contributors + " | مؤطرين: " + supervisors  
            })  
  
            conn.commit()  
            conn.close()  
  
            pdf = generate_pdf("مشروع", {  
                "رقم المشروع": ref,  
                "النوع": name,  
                "الميزانية": budget,  
                "📄 تقرير المشروع": report,  
                "🎯 الأهداف": objectives,  
                "🛠️ التنفيذ": execution_plan,  
                "المساهمين": contributors,  
                "المؤطرين": supervisors,  
                "التاريخ": datetime.now()  
            })  
  
            st.success("تم حفظ المشروع")  
            st.download_button("📄 تحميل PDF", pdf, f"{ref}.pdf")  
  
    # =========================  
    # ⚙️ معالجة المشاريع  
    # =========================  
    elif choice == "⚙️ معالجة المشاريع":  
  
        conn = get_connection()  
        df = pd.read_sql("SELECT * FROM projects", conn)  
  
        st.subheader("📋 جميع المشاريع")  
  
        for _, row in df.iterrows():  
  
            st.markdown(f"### 📁 {row['name']}")  
  
            if st.button(f"👁️ عرض التفاصيل {row['id']}"):  
                st.info(row['report'])  
  
            col1, col2 = st.columns(2)  
  
            if col1.button(f"✅ قبول {row['id']}"):  
  
                conn.execute(text("""  
                    INSERT INTO finance (amount, source, created_by, type)  
                    VALUES (:amount, :source, :user, 'expense')  
                """), {  
                    "amount": row['budget'],  
                    "source": row['name'],  
                    "user": user_login  
                })  
  
                conn.execute(text("DELETE FROM projects WHERE id=:id"), {"id": row['id']})  
                conn.commit()  
                st.success("تم قبول المشروع")  
  
            if col2.button(f"❌ رفض {row['id']}"):  
                conn.execute(text("DELETE FROM projects WHERE id=:id"), {"id": row['id']})  
                conn.commit()  
                st.warning("تم رفض المشروع")  
  
            st.divider()  
  
        conn.close()  
  
    # =========================  
    # 🎉 تنظيم حفلة  
    # =========================  
    elif choice == "🎉 تنظيم حفلة":  
  
        participants = st.text_area("أسماء المشاركين")  
        supervisors = st.text_area("أسماء المؤطرين")  
        contributors = st.text_area("أسماء المساهمين")  
        report = st.text_area("تقرير الحفل")  
  
        if "event_images" not in st.session_state:  
            st.session_state.event_images = []  
  
        st.subheader("📸 التقاط صور متعددة")  
  
        cam = st.camera_input("تصوير")  
  
        if cam is not None:  
            if st.button("📸 إضافة الصورة"):  
                st.session_state.event_images.append(cam)  
                st.success("تم حفظ الصورة")  
  
        if st.button("🗑️ مسح الصور"):  
            st.session_state.event_images = []  
  
        st.write(f"عدد الصور: {len(st.session_state.event_images)}")  
  
        if st.button("حفظ الحفل"):  
  
            ref = generate_number("E°")  
  
            conn = get_connection()  
  
            conn.execute(text("""  
                INSERT INTO events (event_id, report, created_by)  
                VALUES (:id, :report, :user)  
            """), {  
                "id": ref,  
                "report": report,  
                "user": user_login  
            })  
  
            conn.commit()  
            conn.close()  
  
            image_paths = []  
  
            for i, img in enumerate(st.session_state.event_images):  
                path = f"event_{i}.png"  
                with open(path, "wb") as f:  
                    f.write(img.getvalue())  
                image_paths.append(path)  
  
            pdf = generate_pdf("تقرير حفلة", {  
                "رقم الحفل": ref,  
                "المشاركين": participants,  
                "المؤطرين": supervisors,  
                "المساهمين": contributors,  
                "التقرير": report,  
                "التاريخ": datetime.now()  
            }, image_paths)  
  
            st.success("تم حفظ الحفل")  
            st.download_button("📄 تحميل PDF", pdf, f"{ref}.pdf")  
  
    # =========================  
    # 🖼️ عرض الحفلات  
    # =========================  
    elif choice == "🖼️ عرض الحفلات":  
  
        conn = get_connection()  
        df = pd.read_sql("SELECT * FROM events ORDER BY created_at DESC", conn)  
  
        st.subheader("🎉 جميع الحفلات")  
  
        for _, row in df.iterrows():  
            st.markdown(f"### 🎉 {row['event_id']}")  
            st.write("📝 التقرير:", row['report'])  
            st.write("📅 التاريخ:", row['created_at'])  
            st.divider()  
  
        conn.close()