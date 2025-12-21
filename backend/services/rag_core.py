# import os
# import google.generativeai as genai
# from sentence_transformers import SentenceTransformer
# from backend.utils.supabase_client import supabase
# from dotenv import load_dotenv

# load_dotenv()

# class RAGCore:
#     def __init__(self):
#         api_key = os.getenv("GOOGLE_API_KEY")
#         genai.configure(api_key=api_key)
        
#         # Tự động tìm model có sẵn trong tài khoản của bạn
#         available_models = [m.name for m in genai.list_models() 
#                            if 'generateContent' in m.supported_generation_methods]
        
#         if not available_models:
#             raise ValueError("Không tìm thấy model Gemini nào khả dụng với API Key này.")
            
#         # Chọn model đầu tiên trong danh sách (thường là gemini-pro hoặc gemini-1.5-flash)
#         self.llm = genai.GenerativeModel(available_models[0])
#         print(f"✅ RAGCore: Đã kết nối thành công với {available_models[0]}")
            
#         # Model embedding miễn phí 384 chiều
#         self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')

#     def generate_response(self, query: str, category: str = "All"):
#         # 1. Tạo vector cho câu hỏi (Miễn phí)
#         query_vector = self.embed_model.encode(query).tolist()

#         # 2. Tìm kiếm trong Supabase (FR3.6)
#         res = supabase.rpc("match_embeddings", {
#             "query_embedding": query_vector,
#             "filter_category": category
#         }).execute()

#         chunks = res.data
#         if not chunks:
#             return "Tôi không tìm thấy thông tin này trong tài liệu công ty. Hãy đảm bảo bạn đã chạy main.py để nạp dữ liệu.", []
            
#         context = "\n".join([c['content'] for c in chunks])
#         citations = [{"file": c['metadata']['file'], "page": c['metadata']['page']} for c in chunks]

#         # 3. Tạo phản hồi dùng Gemini
#         prompt = f"Ngữ cảnh: {context}\n\nCâu hỏi: {query}"
#         response = self.llm.generate_content(prompt)
        
#         return response.text, citations

import os
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from backend.utils.supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()

class RAGCore:
    def __init__(self):
        # 1. Cấu hình API Key
        api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        
        # 2. Tự động lấy tên model chính xác từ hệ thống (Fix lỗi 404)
        try:
            # Lấy danh sách model hỗ trợ tạo nội dung
            available_models = [
                m.name for m in genai.list_models() 
                if 'generateContent' in m.supported_generation_methods
            ]
            
            # Ưu tiên gemini-1.5-flash, nếu không có thì lấy gemini-1.5-pro hoặc cái đầu tiên
            selected_model = next((m for m in available_models if "flash" in m), None)
            if not selected_model:
                selected_model = next((m for m in available_models if "pro" in m), available_models[0])
            
            self.llm = genai.GenerativeModel(selected_model)
            print(f"✅ RAGCore: Đã kết nối với model thực tế: {selected_model}")
            
        except Exception as e:
            # Nếu không list được model, thử dùng tên cứng chuẩn nhất hiện tại
            self.llm = genai.GenerativeModel('gemini-1.5-flash')
            print(f"⚠️ Cảnh báo: Không list được model, đang dùng mặc định gemini-1.5-flash. Lỗi: {e}")

        # 3. Model embedding miễn phí 384 chiều
        self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')

    def generate_response(self, query: str, category: str = "All"):
        # Tạo vector câu hỏi
        query_vector = self.embed_model.encode(query).tolist()

        # Tìm kiếm trên Supabase (FR3.6)
        res = supabase.rpc("match_embeddings", {
            "query_embedding": query_vector,
            "match_threshold": 0.2, 
            "match_count": 5,
            "filter_category": category
        }).execute()

        chunks = res.data
        if not chunks:
            return "Tôi không tìm thấy thông tin này trong tài liệu hệ thống.", []
            
        context = "\n".join([c['content'] for c in chunks])
        citations = [{"file": c['metadata']['file'], "page": c['metadata']['page']} for c in chunks]

        # Gọi AI tạo phản hồi
        prompt = f"Dựa vào nội dung: {context}\n\nCâu hỏi: {query}\nTrả lời bằng tiếng Việt:"
        response = self.llm.generate_content(prompt)
        
        return response.text, citations