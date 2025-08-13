import os
import fitz  

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def extract_text_from_page(page):
    text = page.get_text("text")
    text = " ".join(text.split())
    return text

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


# -------------------- الإضافة الجديدة فقط --------------------
def split_into_chunks(text, chunk_size=1000):
    """تقسم النص إلى قطع بحجم محدد"""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    return chunks

def process_chunks(input_folder, output_folder, chunk_size=1000):
    """تقسيم الملفات النصية إلى قطع"""
    os.makedirs(output_folder, exist_ok=True)
    
    for filename in os.listdir(input_folder):
        if filename.endswith(".txt"):
            with open(os.path.join(input_folder, filename), 'r', encoding='utf-8') as f:
                text = f.read()
            
            chunks = split_into_chunks(text, chunk_size)
            
            for i, chunk in enumerate(chunks, 1):
                chunk_filename = f"{os.path.splitext(filename)[0]}_chunk_{i}.txt"
                with open(os.path.join(output_folder, chunk_filename), 'w', encoding='utf-8') as f:
                    f.write(chunk)
    
    print(f"تم تقسيم الملفات إلى قطع بحجم {chunk_size} حرف")


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