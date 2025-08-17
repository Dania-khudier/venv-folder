import os
import fitz
import sqlite3
from datetime import datetime
from ollama import Client
import hashlib
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pathlib import Path

# -------------------- إعداد Ollama --------------------
client = Client(host='http://localhost:11434')
model_name = "nomic-embed-text"

def generate_embedding(text):
    response = client.embeddings(model=model_name, prompt=text)
    return response["embedding"]

# -------------------- استخدام LLM من Ollama --------------------
def query_llm(prompt_text, model="gemma3:1b"):
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt_text}]
    )
    return response.get("content", "")

# -------------------- إعداد قاعدة البيانات --------------------
def setup_database(db_name="pdf_data.db"):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        current_dir = os.getcwd()
    db_path = os.path.join(current_dir, db_name)

    conn = sqlite3.connect(db_path)  
    c = conn.cursor()  
    
    c.execute('''CREATE TABLE IF NOT EXISTS pages (  
                 id INTEGER PRIMARY KEY AUTOINCREMENT,  
                 page_number INTEGER UNIQUE,  
                 content TEXT,  
                 created_at TEXT)''')  
    
    c.execute('''CREATE TABLE IF NOT EXISTS images (  
                 id INTEGER PRIMARY KEY AUTOINCREMENT,  
                 page_number INTEGER,  
                 image_hash TEXT UNIQUE,  
                 image_path TEXT,  
                 created_at TEXT)''')  
    
    c.execute('''CREATE TABLE IF NOT EXISTS chunks (  
                 id INTEGER PRIMARY KEY AUTOINCREMENT,  
                 page_id INTEGER,  
                 chunk_number INTEGER,  
                 content TEXT,  
                 created_at TEXT,  
                 FOREIGN KEY (page_id) REFERENCES pages(id),  
                 UNIQUE(page_id, chunk_number))''')  
    
    c.execute('''CREATE TABLE IF NOT EXISTS embeddings (  
                 id INTEGER PRIMARY KEY AUTOINCREMENT,  
                 chunk_id INTEGER UNIQUE,  
                 embeddings_data TEXT,  
                 model TEXT,  
                 generated_at TEXT,  
                 FOREIGN KEY (chunk_id) REFERENCES chunks(id))''')  
    
    c.execute('''CREATE TABLE IF NOT EXISTS metadata (  
                 id INTEGER PRIMARY KEY AUTOINCREMENT,  
                 chunk_id INTEGER UNIQUE,  
                 metadata_json TEXT,  
                 created_at TEXT,  
                 FOREIGN KEY (chunk_id) REFERENCES chunks(id))''')  
    
    conn.commit()  
    conn.close()  
    print(f" قاعدة البيانات تم إنشاؤها في: {os.path.abspath(db_path)}")

# -------------------- استخراج النصوص والصور --------------------
def extract_text_and_images(pdf_path):
    conn = sqlite3.connect("pdf_data.db")
    c = conn.cursor()
    doc = fitz.open(pdf_path)

    images_dir = "extracted_images"
    os.makedirs(images_dir, exist_ok=True)

    for page_num in range(len(doc)):  
        page = doc.load_page(page_num)  
        text = page.get_text().strip()  
        created_at = datetime.now().isoformat()  
          
        c.execute('''INSERT OR IGNORE INTO pages (page_number, content, created_at)  
                     VALUES (?, ?, ?)''', (page_num, text, created_at))  
        conn.commit()  
          
        c.execute("SELECT id FROM pages WHERE page_number=?", (page_num,))  
        page_id = c.fetchone()[0]  
          
        for img in page.get_images(full=True):  
            xref = img[0]  
            base_image = doc.extract_image(xref)  
            image_bytes = base_image["image"]  
            image_hash = hashlib.md5(image_bytes).hexdigest()  
            image_path = os.path.join(images_dir, f"{image_hash}.png")
            
            if not os.path.exists(image_path):
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
              
            c.execute('''INSERT OR IGNORE INTO images (page_number, image_hash, image_path, created_at)
                         VALUES (?, ?, ?, ?)''', (page_num, image_hash, image_path, created_at))
        conn.commit()  
          
        chunk_size = 1000  
        overlap = 200  
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - overlap)]  
          
        for i, chunk in enumerate(chunks):  
            c.execute('''INSERT OR IGNORE INTO chunks (page_id, chunk_number, content, created_at)  
                         VALUES (?, ?, ?, ?)''', (page_id, i, chunk, created_at))  
            conn.commit()  
              
            c.execute("SELECT id FROM chunks WHERE page_id=? AND chunk_number=?", (page_id, i))  
            chunk_id = c.fetchone()[0]  
              
            metadata = {"page": page_num, "chunk": i, "size": len(chunk)}  
            c.execute('''INSERT OR IGNORE INTO metadata (chunk_id, metadata_json, created_at)  
                         VALUES (?, ?, ?)''', (chunk_id, json.dumps(metadata), created_at))  
              
            embedding = generate_embedding(chunk)  
            c.execute('''INSERT OR IGNORE INTO embeddings (chunk_id, embeddings_data, model, generated_at)  
                         VALUES (?, ?, ?, ?)''', (chunk_id, json.dumps(embedding), model_name, created_at))  
            conn.commit()  

            llm_response = query_llm(chunk)  
            print(f"رد النموذج على chunk {i} من الصفحة {page_num}: {llm_response}\n")  
    
    doc.close()  
    conn.close()  
    print("✅ تم استخراج النصوص والصور وتخزينها في قاعدة البيانات، وتم استخدام LLM على كل chunk.")

# -------------------- FastAPI --------------------
app = FastAPI(title="PDF Processing API")

@app.get("/")
def read_root():
    return {"message": "API is running!"}

@app.post("/process_pdf/")
def process_pdf(filename: str):
    pdf_path = Path(filename)
    if not pdf_path.exists():
        return JSONResponse(status_code=404, content={"error": f"الملف {filename} غير موجود!"})
    
    setup_database()
    extract_text_and_images(str(pdf_path))
    return {"message": f"تم معالجة الملف {filename} بنجاح!"}

# -------------------- التشغيل المباشر بدون API --------------------
if __name__ == "__main__":
    pdf_file = "Biology.pdf"
    if os.path.exists(pdf_file):
        setup_database()
        extract_text_and_images(pdf_file)
    else:
        print(f"الملف {pdf_file} غير موجود. يرجى التأكد من اسم الملف.")