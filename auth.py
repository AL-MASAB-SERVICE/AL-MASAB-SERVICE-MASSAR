import streamlit as st                      
from database import get_connection, get_system_status                      
from sqlalchemy import text                      
from datetime import datetime

# =========================  
# 🎨 CSS Animation + UI Pro  
# =========================  
def load_css():  
    st.markdown("""  
    <style>  

    /* Buttons */
    div.stButton > button {  
        background: linear-gradient(45deg, #1e3c72, #2a5298);  
        color: white;  
        border-radius: 10px;  
        padding: 10px 20px;  
        font-weight: bold;  
        border: none;  
        transition: all 0.3s ease-in-out;  
    }  

    div.stButton > button:hover {  
        transform: scale(1.08);  
        background: linear-gradient(45deg, #11998e, #38ef7d);  
        box-shadow: 0px 0px 15px rgba(0,0,0,0.2);  
    }  

    /* Header */
    .main-title {
        text-align:center;
        font-size:36px;
        font-weight:900;
    }

    .blue {
        background: linear-gradient(90deg,#1e3c72,#2a5298);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .red {
        background: linear-gradient(90deg,#2a5298,#4b6cb7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .green {
        background: linear-gradient(90deg,#11998e,#38ef7d);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .version {
        text-align:center;
        font-size:14px;
        font-weight:600;
        margin-bottom:20px;
    }

    .version-text {
        background: linear-gradient(90deg,#141E30,#243B55,#4b6cb7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .version-number {
        color:black;
        font-weight:bold;
    }

    .center-box {
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        margin-top:40px;
    }

    </style>  
    """, unsafe_allow_html=True)  


# =========================  
# 📩 Réclamation Dashboard (العادية) 
# =========================  
def reclamation_panel():  
    st.markdown("<div class='main-title'>📩 Support Client</div>", unsafe_allow_html=True)  
    st.markdown("<div class='version'><span class='version-text'>Envoyer une réclamation</span></div>", unsafe_allow_html=True)  

    with st.container():

        login = st.text_input("👤 Login")
        subject = st.text_input("📘 المادة")

        rec_subject = st.text_input("📌 عنوان الشكاية")  
        rec_message = st.text_area("📝 وصف الشكاية")  

        col1, col2 = st.columns(2)  

        with col1:  
            if st.button("📤 إرسال"):  
                if login.strip() == "" or subject.strip() == "" or rec_subject.strip() == "" or rec_message.strip() == "":  
                    st.error("❌ جميع الخانات مطلوبة من أجل التحقق")  
                else:  
                    conn = get_connection()  
                    conn.execute(text("""  
                        INSERT INTO reclamations (login, subject, message, status)  
                        VALUES (:login, :subject, :message, 'pending')  
                    """), {  
                        "login": login,  
                        "subject": rec_subject,  
                        "message": rec_message  
                    })  
                    conn.commit()  
                    conn.close()  

                    st.success("✅ تم إرسال الشكاية بنجاح، وهي الآن قيد المعالجة. يُرجى العلم أن المصلحة التقنية لدينا تحتاج إلى مدة 24 ساعة مفتوحة لمعالجة الطلب، وذلك دون احتساب أيام السبت والأحد والأعياد الوطنية والدينية. وعليه، نرجو منكم إبقاء هاتفكم مشغّلًا خلال هذه الفترة، حيث قد تضطر المصلحة التقنية إلى الاتصال بكم عند الحاجة. وفي حال رغبتم في تسجيل الدخول بشكل عاجل، يُرجى التواصل مع المصلحة التقنية على الرقم التالي: 0721825921.")

        with col2:  
            if st.button("🔙 رجوع"):  
                st.session_state["page"] = "login"  
                st.rerun()  


# =========================  
# 🔐 Login (مع تتبع المحاولات والتوقيف التلقائي)
# =========================  
def login():                      
    load_css()  

    if "page" not in st.session_state:  
        st.session_state["page"] = "login"  

    if "show_reclamation_btn" not in st.session_state:
        st.session_state["show_reclamation_btn"] = False

    # =========================  
    # 📩 Réclamation Page  
    # =========================  
    if st.session_state["page"] == "reclamation":  
        reclamation_panel()  
        return  

    # =========================  
    # 🔐 Login Page  
    # =========================  
    st.markdown("""
    <div class='main-title'>
        🎓 
        <span class='blue'>Al</span> 
        <span class='red'>Masab</span> 
        <span class='green'>Service</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='version'>
        <span class='version-text'>⚙️ Système Entreprise </span>
        <span class='version-number'>v2.1.0</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        login_input = st.text_input("Login")                      
        password = st.text_input("Password", type="password")                      

        if st.button("Se connecter"):                      
            system_status = get_system_status()                      

            if system_status == "off" and login_input != "yassinederra@service":                      
                st.session_state["show_reclamation_btn"] = True
                st.session_state["error_msg"] = "🔧 نود إعلامكم بأن النظام متوقف مؤقتًا لأغراض الصيانة للاستفسار أو لمزيد من المعلومات يرجى التواصل مع خدمة العملاء على الرقم 07.21.82.59.21"
                st.rerun()
                return                      

            conn = get_connection()
            
            # جلب معلومات المستخدم مع failed_login_attempts
            result = conn.execute(text("""                      
                SELECT role, name, subject, status, failed_login_attempts, login                      
                FROM users                       
                WHERE login = :login                      
            """), {                      
                "login": login_input                      
            }).fetchone()                      
            
            if result:
                role, name, subject, status, failed_attempts, user_login = result
                
                # التحقق من صحة كلمة المرور
                pass_result = conn.execute(text("""
                    SELECT password FROM users WHERE login = :login AND password = :password
                """), {
                    "login": login_input,
                    "password": password
                }).fetchone()
                
                if pass_result:
                    # ✅ تسجيل الدخول ناجح
                    if status == "stopped":
                        st.session_state["show_reclamation_btn"] = True
                        st.session_state["error_msg"] = "⚠️ حسابك موقوف. الرجاء التواصل مع المصلاحة التقني على الرقم الأخضر 0721825921."
                        st.rerun()
                        return
                    
                    # تحديث عدد المحاولات الفاشلة إلى 0
                    conn.execute(text("""
                        UPDATE users SET failed_login_attempts = 0, login_count = login_count + 1, last_login = NOW()
                        WHERE login = :login
                    """), {"login": login_input})
                    conn.commit()
                    
                    st.session_state["login"] = True                      
                    st.session_state["role"] = role                      
                    st.session_state["name"] = name    
                    st.session_state["login_user"] = login_input  
                    st.session_state["subject"] = subject  
                    st.session_state["show_reclamation_btn"] = False

                    st.success(f"مرحباً {name}!")                      
                    st.rerun()
                else:
                    # ❌ كلمة مرور خاطئة
                    new_attempts = (failed_attempts or 0) + 1
                    
                    # تلقائياً: إذا تعدت 3 محاولات خاطئة، يتم توقيف الحساب
                    if new_attempts >= 3:
                        conn.execute(text("""
                            UPDATE users 
                            SET status = 'stopped', 
                                blocked_at = NOW(), 
                                blocked_reason = 'تجاوز عدد المحاولات الفاشلة (3 محاولات)',
                                blocked_by = 'auto_system'
                            WHERE login = :login
                        """), {"login": login_input})
                        
                        # تسجيل في سجل التوقيف
                        conn.execute(text("""
                            INSERT INTO users_block_log (user_login, blocked_reason, blocked_by)
                            VALUES (:login, 'تجاوز عدد المحاولات الفاشلة (3 محاولات)', 'auto_system')
                        """), {"login": login_input})
                        
                        conn.commit()
                        st.session_state["show_reclamation_btn"] = True
                        st.session_state["error_msg"] = "🔒 تم إيقاف حسابكم بشكلٍ تلقائي، نظرًا لاكتشاف نشاطٍ مشبوه أثناء عملية تسجيل الدخول. يُرجى التواصل مع الجهة المختصة أو تواصل معا المصلاحة تقنيا بي الإتصال بي رقم 0721825921 أو الضغط على زر شكاية لاستعادة الوصول إلى الحساب  ."
                    else:
                        conn.execute(text("""
                            UPDATE users SET failed_login_attempts = :attempts WHERE login = :login
                        """), {"attempts": new_attempts, "login": login_input})
                        conn.commit()
                        st.session_state["show_reclamation_btn"] = True
                        st.session_state["error_msg"] = f"❌ كلمة المرور غير صحيحة. تبقى لك {3 - new_attempts} محاولة قبل توقيف الحساب."
                    
                    conn.close()
                    st.rerun()
            else:
                # المستخدم غير موجود
                st.session_state["show_reclamation_btn"] = True
                st.session_state["error_msg"] = "❌ معلومات تسجيل الدخول غير صحيحة، يُرجى التحقق منها"
                st.rerun()
            
            conn.close()

        if "error_msg" in st.session_state:
            st.error(st.session_state["error_msg"])

        if st.session_state["show_reclamation_btn"]:
            if st.button("📩 Réclamation"):  
                st.session_state["page"] = "reclamation"  
                st.rerun()