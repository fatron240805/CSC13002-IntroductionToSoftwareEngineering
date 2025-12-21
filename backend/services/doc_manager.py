from PyPDF2 import PdfReader
from backend.utils.supabase_client import supabase
from openai import OpenAI
import os

class DocumentManager:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def upload_and_index(self, file_path, category):
        # 1. Đọc nội dung PDF (Class C9)
        reader = PdfReader(file_path)
        file_name = os.path.basename(file_path)
        
        # Tạo bản ghi document trong database
        doc_res = supabase.table("documents").insert({
            "file_name": file_name,
            "category": category,
            "status": "Processing"
        }).execute()
        doc_id = doc_res.data[0]['id']

        # 2. Chia nhỏ và tạo Embedding (Class C6)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text.strip(): continue
            
            # Tạo vector 1536 chiều
            embed = self.client.embeddings.create(
                input=[text], model="text-embedding-ada-002"
            ).data[0].embedding

            # 3. Lưu vào pgvector (Class C4)
            supabase.table("knowledge_embeddings").insert({
                "document_id": doc_id,
                "content": text,
                "embedding": embed,
                "metadata": {"page": i + 1, "file": file_name, "category": category}
            }).execute()
        
        # Cập nhật trạng thái hoàn tất
        supabase.table("documents").update({"status": "Completed"}).eq("id", doc_id).execute()
        return doc_id