import os
import fitz  # PyMuPDF

# العمل من مجلد الكود نفسه
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# --- دالة لاستخراج النصوص من الصفحة بشكل متتابع ---
def extract_text_from_page(page):
    text = page.get_text("text")
    text = " ".join(text.split())  # إزالة الفراغات وجعل النص متتابع
    return text

# --- دالة لاستخراج الصور من الصفحة ---
def extract_images_from_page(doc, page, page_num, images_folder, max_per_folder=50):
    images = page.get_images(full=True)
    img_count = 0
    for img_info in images:
        xref = img_info[0]
        pix = fitz.Pixmap(doc, xref)
        img_count += 1

        # تحديد المجلد الفرعي
        folder_index = (img_count - 1) // max_per_folder + 1
        folder_path = os.path.join(images_folder, f"images_batch_{folder_index}")
        os.makedirs(folder_path, exist_ok=True)

        # اسم الصورة النهائي
        img_filename = os.path.join(folder_path, f"page{page_num}_img{img_count}.png")

        # التحويل إلى صيغة صالحة قبل الحفظ
        if pix.n > 4 or (pix.colorspace and pix.colorspace.n > 3):
            pix = fitz.Pixmap(fitz.csRGB, pix)
        elif pix.alpha:  # إذا كانت الصورة تحتوي على قناة ألفا (شفافية)
            pix0 = fitz.Pixmap(fitz.csRGB, pix)
            pix = fitz.Pixmap(fitz.csRGB, pix0)
            pix0 = None
        
        try:
            pix.save(img_filename)
        except Exception as e:
            print(f"حدث خطأ أثناء حفظ الصورة: {str(e)}")
        finally:
            pix = None

    return img_count

# --- الدالة الرئيسية لاستخراج النصوص والصور ---
def extract_text_and_images(pdf_path, output_folder, max_images_per_folder=50):
    os.makedirs(output_folder, exist_ok=True)
    images_folder = os.path.join(output_folder, "images")
    os.makedirs(images_folder, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    
    for page_num, page in enumerate(doc, start=1):
        # استخراج النصوص
        page_text = extract_text_from_page(page)
        txt_filename = os.path.join(output_folder, f"page_{page_num}.txt")
        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write(page_text)
        
        # استخراج الصور
        img_count = extract_images_from_page(doc, page, page_num, images_folder, max_images_per_folder)
        
        print(f"Page {page_num} processed: {len(page_text)} characters, {img_count} images saved.")
    
    print("Extraction completed successfully!")

# --- مثال استخدام ---
if __name__ == "__main__":
    pdf_file = "Biology.pdf"  # غيّر اسم الملف هنا إذا لزم الأمر
    output_dir = "extracted_pages"
    if os.path.exists(pdf_file):
        extract_text_and_images(pdf_file, output_dir, max_images_per_folder=50)
    else:
        print(f"الملف {pdf_file} غير موجود. يرجى التأكد من اسم الملف.")
        
      # Biology.pdf