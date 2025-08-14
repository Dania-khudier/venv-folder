import os
import fitz
import json
from datetime import datetime

# تغيير مسار العمل إلى مجلد الملف الحالي
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# دالة لاستخراج النص من صفحة PDF
def extract_text_from_page(page):
    text = page.get_text("text")
    text = " ".join(text.split())
    return text

# دالة لاستخراج الصور من صفحة PDF
def extract_images_from_page(doc, page, page_num, images_folder, max_per_folder=50):
    images = page.get_images(full=True)
    img_count = 0
    for img_info in images:
        xref = img_info[0]
        pix = fitz.Pixmap(doc, xref)
        img_count += 1

        folder_index = (img_count - 1) // max_per_folder + 1
        folder_path = os.path.join(images_folder, f"images_batch_{folder_index}")
        os.makedirs(folder_path, exist_ok=True)

        img_filename = os.path.join(folder_path, f"page{page_num}_img{img_count}.png")

        if pix.n > 4 or (pix.colorspace and pix.colorspace.n > 3):
            pix = fitz.Pixmap(fitz.csRGB, pix)
        elif pix.alpha:
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

# دالة رئيسية لاستخراج النصوص والصور من ملف PDF
def extract_text_and_images(pdf_path, output_folder, max_images_per_folder=50):
    os.makedirs(output_folder, exist_ok=True)
    images_folder = os.path.join(output_folder, "images")
    os.makedirs(images_folder, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    
    for page_num, page in enumerate(doc, start=1):
        page_text = extract_text_from_page(page)
        txt_filename = os.path.join(output_folder, f"page_{page_num}.txt")
        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write(page_text)
        
        img_count = extract_images_from_page(doc, page, page_num, images_folder, max_images_per_folder)
        print(f"Page {page_num} processed: {len(page_text)} characters, {img_count} images saved.")
    
    print("Extraction completed successfully!")



# دالة لإنشاء بيانات وصفية للقطع النصية
def generate_metadata(page_num, chunk_num, original_filename):
    return {
        "source": original_filename,
        "page_number": page_num,
        "chunk_number": chunk_num,
        "created_at": datetime.now().isoformat(),
        "processing_info": {
            "tool": "PDF Text Extractor",
            "version": "1.0"
        }
    }

# دالة لإنشاء تمثيل رقمي للنص 
def generate_embeddings(text):
    return [len(text)] * 10  

# دالة لتقسيم النص إلى أجزاء أصغر مع تداخل
def split_into_chunks(text, chunk_size=1000, overlap=200):
    """تقسم النص إلى قطع متداخلة بحجم محدد"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

# دالة رئيسية لمعالجة القطع النصية
def process_chunks(input_folder, output_folder, chunk_size=1000):
    os.makedirs(output_folder, exist_ok=True)
    
    metadata_folder = os.path.join(output_folder, "metadata")
    os.makedirs(metadata_folder, exist_ok=True)
    
    embeddings_folder = os.path.join(output_folder, "embeddings")
    os.makedirs(embeddings_folder, exist_ok=True)
    
    for filename in os.listdir(input_folder):
        if filename.endswith(".txt"):
            with open(os.path.join(input_folder, filename), 'r', encoding='utf-8') as f:
                text = f.read()
            
            try:
                page_num = int(filename.split('_')[1].split('.')[0])
            except:
                page_num = 0
            
            chunks = split_into_chunks(text, chunk_size)
            
            for i, chunk in enumerate(chunks, 1):
                chunk_filename = f"{os.path.splitext(filename)[0]}_chunk_{i}.txt"
                with open(os.path.join(output_folder, chunk_filename), 'w', encoding='utf-8') as f:
                    f.write(chunk)
                
                metadata = generate_metadata(page_num, i, filename)
                metadata_filename = f"{os.path.splitext(chunk_filename)[0]}_metadata.json"
                with open(os.path.join(metadata_folder, metadata_filename), 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                embeddings = generate_embeddings(chunk)
                embeddings_filename = f"{os.path.splitext(chunk_filename)[0]}_embeddings.json"
                with open(os.path.join(embeddings_folder, embeddings_filename), 'w', encoding='utf-8') as f:
                    json.dump({"embeddings": embeddings}, f, ensure_ascii=False, indent=2)
    
    print(f"تم تقسيم الملفات إلى قطع بحجم {chunk_size} حرف مع إنشاء metadata وembeddings")


if __name__ == "__main__":
    pdf_file = "Biology.pdf"
    output_dir = "extracted_pages"
    chunks_dir = "extracted_chunks"
    
    if os.path.exists(pdf_file):
        extract_text_and_images(pdf_file, output_dir, max_images_per_folder=50)
        process_chunks(output_dir, chunks_dir, chunk_size=1000)
    else:
        print(f"الملف {pdf_file} غير موجود. يرجى التأكد من اسم الملف.")
      # Biology.pdf