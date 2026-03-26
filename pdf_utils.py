from fpdf import FPDF  
from datetime import datetime  
import os  

import arabic_reshaper  
from bidi.algorithm import get_display  


# =========================  
# 🔁 دالة تصحيح العربية  
# =========================  
def ar(text):  
    if text is None:  
        return ""  
    text = str(text)  
    reshaped = arabic_reshaper.reshape(text)  
    return get_display(reshaped)  


# =========================  
# 📄 PDF CLASS  
# =========================  
class PDF(FPDF):  

    def __init__(self):  
        super().__init__()  
        self.add_font("Amiri", "", "Amiri-Regular.ttf", uni=True)  

    def header(self):  
        self.set_font("Amiri", "", 18)  
        self.cell(0, 10, ar("جمعية آباء وأمهات التلاميذ"), 0, 1, "C")  

        self.set_font("Amiri", "", 12)  
        self.cell(0, 8, ar("المصب"), 0, 1, "C")  

        self.ln(3)  

        self.set_draw_color(180, 180, 180)  
        self.line(10, 30, 200, 30)  

        self.ln(10)  

    def footer(self):  
        # غير التاريخ فقط في الأسفل
        self.set_y(-15)  
        self.set_font("Amiri", "", 10)  
        self.cell(0, 8, ar(f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), 0, 0, "L")  


# =========================  
# 📄 GENERATE PDF  
# =========================  
def generate_pdf(title, data, images=None):  

    pdf = PDF()  
    pdf.add_page()  

    # =========================  
    # TITLE  
    # =========================  
    pdf.set_font("Amiri", "", 16)  
    pdf.cell(0, 10, ar(title), 0, 1, "C")  

    pdf.ln(5)  

    # =========================  
    # TABLE HEADER  
    # =========================  
    pdf.set_fill_color(200, 200, 200)  
    pdf.set_font("Amiri", "", 12)  

    pdf.cell(90, 10, ar("القيمة"), 1, 0, "C", True)  
    pdf.cell(100, 10, ar("البيان"), 1, 1, "C", True)  

    # =========================  
    # TABLE DATA  
    # =========================  
    pdf.set_fill_color(245, 245, 245)  

    for key, value in data.items():  
        pdf.cell(90, 10, ar(value), 1, 0, "R")  
        pdf.cell(100, 10, ar(key), 1, 1, "R", True)  

    pdf.ln(15)  


    # =========================  
    # 🖼️ IMAGES  
    # =========================  
    if images:  
        pdf.set_font("Amiri", "", 12)  
        pdf.cell(0, 10, ar("صور الحفل"), 0, 1, "R")  

        for img in images:  
            if os.path.exists(img):  
                pdf.image(img, x=30, w=150)  
                pdf.ln(10)  


    # =========================  
    # ✍️ SIGNATURE (احترافي)
    # =========================  
    pdf.ln(15)

    # خطوط التوقيع
    y = pdf.get_y()

    pdf.set_draw_color(0, 0, 0)

    # خط توقيع الإدارة (يسار)
    pdf.line(20, y, 90, y)

    # خط توقيع الجمعية (يمين)
    pdf.line(120, y, 190, y)

    pdf.ln(5)

    pdf.set_font("Amiri", "", 12)

    # النص تحت الخطوط
    pdf.cell(90, 10, ar("توقيع الإدارة"), 0, 0, "C")
    pdf.cell(100, 10, ar("توقيع الجمعية"), 0, 1, "C")


    # =========================  
    # OUTPUT  
    # =========================  
    return bytes(pdf.output(dest='S'))