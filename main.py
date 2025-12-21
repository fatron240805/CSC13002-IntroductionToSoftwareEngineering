import os
import logging
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from supabase import create_client
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

model = SentenceTransformer('all-MiniLM-L6-v2')
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def ingest_pdf(file_path):
    try:
        file_name = os.path.basename(file_path)
        logger.info(f"--- Đang xử lý: {file_name} ---")
        
        category = "General"
        if "HR" in file_name.upper(): category = "HR"
        elif "IT" in file_name.upper(): category = "IT"
        elif "SALES" in file_name.upper(): category = "Sales"

        reader = PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text or not text.strip(): continue

            embedding = model.encode(text).tolist()

            supabase.table("knowledge_embeddings").insert({
                "content": text,
                "embedding": embedding,
                "category": category, 
                "metadata": {"page": i + 1, "file": file_name}
            }).execute()

        logger.info(f"✅ Thành công: {file_name} (Phòng ban: {category})")
    except Exception as e:
        logger.error(f"❌ Lỗi xử lý {file_path}: {str(e)}")

if __name__ == "__main__":
    doc_dir = os.getenv("WATCHED_DIR", "./documents")
    if not os.path.exists(doc_dir):
        os.makedirs(doc_dir)
        logger.info(f"Đã tạo thư mục {doc_dir}. Hãy bỏ file PDF vào đây.")
    
    for file in os.listdir(doc_dir):
        if file.endswith(".pdf"):
            ingest_pdf(os.path.join(doc_dir, file))