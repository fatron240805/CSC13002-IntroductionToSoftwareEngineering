# intelligentRAG
Need not to know.
=======
🤖 Intelligent RAG System (Gemini & OpenAI)
Hệ thống RAG (Retrieval-Augmented Generation) thông minh cho phép người dùng tải lên file PDF, trích xuất kiến thức và trò chuyện trực tiếp với tài liệu dựa trên sức mạnh của LLMs (Gemini/OpenAI) và Vector Database (Supabase).

🌟 Tính năng chính
Xử lý PDF: Đọc và tách nội dung từ các tệp PDF phức tạp.

Vector Search: Sử dụng sentence-transformers để chuyển đổi văn bản thành vector và lưu trữ trên Supabase Vector.

Đa mô hình: Hỗ trợ cả Google Gemini API và OpenAI API.

Giao diện Streamlit: Giao diện chatbot thân thiện, dễ sử dụng.

Hệ thống thông báo: Tích hợp gửi mã OTP hoặc thông báo qua Email (SMTP).

📁 Cấu trúc thư mục
Plaintext

├── backend/
│   ├── services/
│   │   └── rag_core.py       # Xử lý logic RAG chính
│   └── utils/
│       └── supabase_client.py # Kết nối Supabase
├── app.py                   # File chạy chính (Streamlit UI)
├── .env                     # Lưu trữ API Keys (Không công khai)
├── requirements.txt         # Danh sách thư viện cần cài đặt
└── README.md                # Hướng dẫn sử dụng
🚀 Hướng dẫn cài đặt
1. Chuẩn bị môi trường
Yêu cầu Python 3.9 trở lên. Tốt nhất nên sử dụng môi trường ảo:

Bash

python -m venv venv
# Windows:
venv\Scripts\activate
# MacOS/Linux:
source venv/bin/activate
2. Cài đặt thư viện
Bash

pip install -r requirements.txt
3. Cấu hình biến môi trường
Tạo một file .env nằm ở thư mục gốc và điền các thông tin sau:

Đoạn mã

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key

# AI API Keys
GOOGLE_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# Email Configuration (Nếu dùng tính năng gửi mail)
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
4. Khởi chạy ứng dụng
Bash
streamlit run app.py

🛠 Luồng hoạt động (Workflow)
Ingestion: Người dùng upload PDF -> Hệ thống chia nhỏ văn bản (Chunking).

Embedding: Chuyển các đoạn văn bản thành vector bằng SentenceTransformer.

Storage: Lưu trữ vector vào Supabase.

Retrieval: Khi người dùng đặt câu hỏi, hệ thống tìm kiếm các đoạn văn bản có nội dung liên quan nhất.

Generation: Gửi ngữ cảnh (context) tìm được vào Gemini/OpenAI để tạo câu trả lời cuối cùng.
