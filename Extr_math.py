import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import pdf2image
from pdf2image import convert_from_path
import re
import pandas as pd
import shutil
from typing import List, Tuple, Dict

os.chdir(os.path.dirname(os.path.abspath(__file__)))

class PDFExtractor:
    def __init__(self, pdf_path: str, output_dir: str = "extracted_content"):
        """
        تهيئة مستخرج PDF مع مسار الملف ومسار الإخراج
        
        :param pdf_path: مسار ملف PDF المدخل
        :param output_dir: مجلد الإخراج الرئيسي
        """
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.images_dir = os.path.join(output_dir, "images")
        self.text_dir = os.path.join(output_dir, "text")
        self.equations_dir = os.path.join(output_dir, "equations")
        
        # إنشاء المجلدات إذا لم تكن موجودة
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.text_dir, exist_ok=True)
        os.makedirs(self.equations_dir, exist_ok=True)
        
        # إعداد ترقيم الصفحات
        self.page_counter = 1
        
    def extract_content(self, dpi: int = 300, max_images_per_folder: int = 50):
        """
        استخراج جميع المحتويات من PDF
        
        :param dpi: دقة الصور المستخرجة
        :param max_images_per_folder: الحد الأقصى للصور في كل مجلد فرعي
        """
        print(f"جارٍ استخراج المحتوى من {self.pdf_path}...")
        
        # استخراج النصوص والمعادلات
        self._extract_text_and_equations()
        
        # استخراج الصور بدقة عالية
        self._extract_images_with_high_quality(dpi, max_images_per_folder)
        
        print(f"تم استخراج المحتوى بنجاح في {self.output_dir}")
    
    def _extract_text_and_equations(self):
        """استخراج النصوص والمعادلات من PDF باستخدام PyMuPDF"""
        doc = fitz.open(self.pdf_path)
        
        full_text = []
        equations = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            
            # حفظ نص الصفحة
            page_text_path = os.path.join(self.text_dir, f"page_{page_num + 1}.txt")
            with open(page_text_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            full_text.append(text)
            
            # البحث عن المعادلات (هذا نموذج بسيط، يمكن تحسينه)
            page_equations = self._find_equations(text)
            if page_equations:
                equations.extend([(page_num + 1, eq) for eq in page_equations])
        
        # حفظ جميع النصوص في ملف واحد
        with open(os.path.join(self.text_dir, "full_text.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(full_text))
        
        # حفظ المعادلات في ملف Excel
        if equations:
            df = pd.DataFrame(equations, columns=["Page", "Equation"])
            df.to_excel(os.path.join(self.equations_dir, "equations.xlsx"), index=False)
    
    def _find_equations(self, text: str) -> List[str]:
        """اكتشاف المعادلات في النص (هذا نموذج بسيط يمكن تحسينه)"""
        # نمط بسيط للكشف عن المعادلات الرياضية
        equation_pattern = r"\$[^$]+\$|\\\(.*?\\\)|\\\[.*?\\\]"
        return re.findall(equation_pattern, text)
    
    def _extract_images_with_high_quality(self, dpi: int, max_images_per_folder: int):
        """استخراج الصور من PDF بدقة عالية"""
        print(f"جارٍ استخراج الصور بدقة {dpi} DPI...")
        
        # تحويل PDF إلى صور
        images = convert_from_path(
            self.pdf_path,
            dpi=dpi,
            output_folder=self.images_dir,
            fmt="jpeg",
            thread_count=4,
            paths_only=True
        )
        
        # تنظيم الصور في مجلدات فرعية
        current_folder = os.path.join(self.images_dir, f"images_1")
        os.makedirs(current_folder, exist_ok=True)
        folder_counter = 1
        image_counter = 1
        
        for img_path in images:
            if image_counter > max_images_per_folder:
                folder_counter += 1
                current_folder = os.path.join(self.images_dir, f"images_{folder_counter}")
                os.makedirs(current_folder, exist_ok=True)
                image_counter = 1
            
            # إنشاء اسم ملف جديد
            new_path = os.path.join(current_folder, f"image_{image_counter}.jpg")
            shutil.move(img_path, new_path)
            image_counter += 1
        
        print(f"تم استخراج {len(images)} صورة في {folder_counter} مجلد(ات) فرعية.")

    def _ocr_image(self, image_path: str) -> str:
        """استخراج النص من الصورة باستخدام OCR"""
        try:
            return pytesseract.image_to_string(Image.open(image_path))
        except Exception as e:
            print(f"خطأ في معالجة الصورة {image_path}: {e}")
            return ""

if __name__ == "__main__":
    # استخدام الكود
    pdf_file = "math_book.pdf"  # تأكد من وجود الملف في نفس المجلد
    if os.path.exists(pdf_file):
        extractor = PDFExtractor(pdf_file)
        extractor.extract_content(dpi=300, max_images_per_folder=50)
    else:
        print(f"الملف {pdf_file} غير موجود. يرجى التأكد من اسم الملف.")