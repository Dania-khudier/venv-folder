import os
import fitz
import json
from datetime import datetime
from ollama import Client
import sqlite3

# -------------------- استخراج النصوص والصور من PDF --------------------
def extract_text_and_images(pdf_path, output_dir, max_images_per_folder=50):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    images_dir = os.path.join(output_dir, "images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
    
    doc = fitz.open(pdf_path)
    image_counter = 0
    folder_counter = 0
    current_image_dir = os.path.join(images_dir, f"images_{folder_counter}")
    os.makedirs(current_image_dir, exist_ok=True)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        
        # حفظ النص
        with open(os.path.join(output_dir, f"page_{page_num}.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        
        # استخراج الصور
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_filename = f"page{page_num}_img{img_index}.{image_ext}"
            image_path = os.path.join(current_image_dir, image_filename)
            
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            image_counter += 1
            
            if image_counter >= max_images_per_folder:
                image_counter = 0
                folder_counter += 1
                current_image_dir = os.path.join(images_dir, f"images_{folder_counter}")
                os.makedirs(current_image_dir, exist_ok=True)
    
    print("تم استخراج النصوص والصور بنجاح.")

# -------------------- معالجة القطع النصية --------------------
def process_chunks(input_dir, output_dir, chunk_size=1000, overlap=200):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    metadata_dir = os.path.join(output_dir, "metadata")
    embeddings_dir = os.path.join(output_dir, "embeddings")
    os.makedirs(metadata_dir, exist_ok=True)
    os.makedirs(embeddings_dir, exist_ok=True)
    
    client = Client(host='http://localhost:11434')
    model_name = "nomic-embed-text"
    
    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            page_num = filename.split("_")[1].split(".")[0]
            file_path = os.path.join(input_dir, filename)
            
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            # تقسيم النص إلى chunks متداخلة
            chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - overlap)]
            
            for i, chunk in enumerate(chunks):
                chunk_filename = f"page_{page_num}_chunk_{i}.txt"
                with open(os.path.join(output_dir, chunk_filename), "w", encoding="utf-8") as f:
                    f.write(chunk)
                
                # إنشاء metadata
                metadata = {
                    "page": page_num,
                    "chunk": i,
                    "size": len(chunk)
                }
                metadata_filename = f"page_{page_num}_chunk_{i}_metadata.json"
                with open(os.path.join(metadata_dir, metadata_filename), "w", encoding="utf-8") as f:
                    json.dump(metadata, f)
                
                # توليد embeddings
                response = client.embeddings(model=model_name, prompt=chunk)
                embeddings = response["embedding"]
                embeddings_data = {
                    "embeddings": embeddings,
                    "model": model_name,
                    "generated_at": datetime.now().isoformat()
                }
                embeddings_filename = f"page_{page_num}_chunk_{i}_embeddings.json"
                with open(os.path.join(embeddings_dir, embeddings_filename), "w", encoding="utf-8") as f:
                    json.dump(embeddings_data, f)
    
    print("تم معالجة القطع النصية بنجاح.")

# -------------------- إعداد قاعدة البيانات --------------------
def setup_database(db_name="pdf_data.db"):
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_name)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS pages (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 page_number INTEGER,
                 content TEXT,
                 created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS images (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 page_number INTEGER,
                 image_path TEXT,
                 created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS chunks (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 page_id INTEGER,
                 chunk_number INTEGER,
                 content TEXT,
                 created_at TEXT,
                 FOREIGN KEY (page_id) REFERENCES pages(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS embeddings (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 chunk_id INTEGER,
                 embeddings_data TEXT,
                 model TEXT,
                 generated_at TEXT,
                 FOREIGN KEY (chunk_id) REFERENCES chunks(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS metadata (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 chunk_id INTEGER,
                 metadata_json TEXT,
                 created_at TEXT,
                 FOREIGN KEY (chunk_id) REFERENCES chunks(id))''')
    
    conn.commit()
    conn.close()
    
    print(f" قاعدة البيانات تم إنشاؤها في: {os.path.abspath(db_path)}")

# -------------------- حفظ الصفحات في قاعدة البيانات --------------------
def save_pages_to_db(input_folder, db_name="pdf_data.db"):
    conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), db_name))
    c = conn.cursor()
    
    for filename in os.listdir(input_folder):
        if filename.endswith(".txt"):
            try:
                page_num = int(filename.split('_')[1].split('.')[0])
            except:
                page_num = 0
            
            with open(os.path.join(input_folder, filename), 'r', encoding='utf-8') as f:
                content = f.read()
            
            created_at = datetime.now().isoformat()
            
            c.execute('''INSERT INTO pages (page_number, content, created_at)
                         VALUES (?, ?, ?)''', 
                      (page_num, content, created_at))
    
    conn.commit()
    conn.close()
    print(f"تم حفظ صفحات النص في قاعدة البيانات")

# -------------------- حفظ الصور في قاعدة البيانات --------------------
def save_images_to_db(output_dir, db_name="pdf_data.db"):
    conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), db_name))
    c = conn.cursor()
    
    images_folder = os.path.join(output_dir, "images")
    if not os.path.exists(images_folder):
        print("مجلد الصور غير موجود، سيتم تخطي حفظ الصور.")
        conn.close()
        return
    
    for root, dirs, files in os.walk(images_folder):
        for filename in files:
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                try:
                    parts = filename.split('_')
                    page_num = int(parts[0].replace("page", ""))
                except:
                    page_num = 0
                
                image_path = os.path.join(root, filename)
                created_at = datetime.now().isoformat()
                
                c.execute('''INSERT INTO images (page_number, image_path, created_at)
                             VALUES (?, ?, ?)''', 
                          (page_num, image_path, created_at))
    
    conn.commit()
    conn.close()
    print("تم حفظ الصور في قاعدة البيانات.")

# -------------------- حفظ القطع النصية والـ embeddings في قاعدة البيانات --------------------
def save_chunks_to_db(output_folder, db_name="pdf_data.db"):
    conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), db_name))
    c = conn.cursor()
    
    metadata_folder = os.path.join(output_folder, "metadata")
    embeddings_folder = os.path.join(output_folder, "embeddings")
    
    page_map = {}
    c.execute("SELECT id, page_number FROM pages")
    for row in c.fetchall():
        page_map[row[1]] = row[0]
    
    for filename in os.listdir(output_folder):
        if filename.endswith(".txt") and "_chunk_" in filename:
            try:
                parts = filename.split('_')
                page_num = int(parts[1])
                chunk_num = int(parts[3].split('.')[0])
            except:
                page_num = 0
                chunk_num = 0
            
            page_id = page_map.get(page_num, None)
            
            if page_id is None:
                continue
            
            with open(os.path.join(output_folder, filename), 'r', encoding='utf-8') as f:
                content = f.read()
            
            created_at = datetime.now().isoformat()
            c.execute('''INSERT INTO chunks (page_id, chunk_number, content, created_at)
                         VALUES (?, ?, ?, ?)''', 
                      (page_id, chunk_num, content, created_at))
            chunk_id = c.lastrowid
            
            metadata_filename = f"{os.path.splitext(filename)[0]}_metadata.json"
            metadata_path = os.path.join(metadata_folder, metadata_filename)
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                c.execute('''INSERT INTO metadata (chunk_id, metadata_json, created_at)
                             VALUES (?, ?, ?)''', 
                          (chunk_id, json.dumps(metadata), created_at))
            
            embeddings_filename = f"{os.path.splitext(filename)[0]}_embeddings.json"
            embeddings_path = os.path.join(embeddings_folder, embeddings_filename)
            if os.path.exists(embeddings_path):
                with open(embeddings_path, 'r', encoding='utf-8') as f:
                    embeddings_data = json.load(f)
                
                c.execute('''INSERT INTO embeddings (chunk_id, embeddings_data, model, generated_at)
                             VALUES (?, ?, ?, ?)''', 
                          (chunk_id, json.dumps(embeddings_data["embeddings"]), 
                           embeddings_data["model"], embeddings_data["generated_at"]))
    
    conn.commit()
    conn.close()
    print("تم حفظ القطع النصية والـ embeddings والـ metadata في قاعدة البيانات.")

# -------------------- التنفيذ الرئيسي --------------------
if __name__ == "__main__":
    pdf_file = "Biology.pdf"
    output_dir = "extracted_pages"
    chunks_dir = "extracted_chunks"
    
    if os.path.exists(pdf_file):
        # إعداد قاعدة البيانات
        setup_database()
        
        # استخراج النصوص والصور
        extract_text_and_images(pdf_file, output_dir, max_images_per_folder=50)
        
        # حفظ الصفحات والصور في قاعدة البيانات
        save_pages_to_db(output_dir)
        save_images_to_db(output_dir)
        
        # معالجة القطع النصية
        process_chunks(output_dir, chunks_dir, chunk_size=1000, overlap=200)
        
        # حفظ القطع النصية والـ embeddings في قاعدة البيانات
        save_chunks_to_db(chunks_dir)
    else:
        print(f"الملف {pdf_file} غير موجود. يرجى التأكد من اسم الملف.")
      # Biology.pdf