import streamlit as st
import os
import random
import smtplib
from email.mime.text import MIMEText
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from backend.services.rag_core import RAGCore
from backend.utils.supabase_client import supabase
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv()

# --- 1. CẤU HÌNH BAN ĐẦU ---
st.set_page_config(page_title="Intelligent RAG Assistant", layout="wide")

if "rag_service" not in st.session_state:
    st.session_state.rag_service = RAGCore()
if "embed_model" not in st.session_state:
    st.session_state.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
if "messages" not in st.session_state:
    st.session_state.messages = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- HÀM GỬI MÃ OTP (Xác minh thực tế - FR1.4) ---
def send_gmail_otp(to_email):
    sender = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_PASS") # Đảm bảo 16 ký tự viết liền
    otp_code = str(random.randint(100000, 999999))
    
    msg = MIMEText(f"Chào bạn,\n\nMã kích hoạt tài khoản RAG của bạn là: {otp_code}\n\nVui lòng đăng nhập và nhập mã này để đặt mật khẩu.")
    msg['Subject'] = 'Kich hoat tai khoan RAG Assistant'
    msg['From'] = f"RAG Admin <{sender}>"
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        
        # Lưu vào bảng users trạng thái chờ kích hoạt
        supabase.table("users").upsert({
            "email": to_email, 
            "role": "End-User", 
            "is_active": False, 
            "otp_code": otp_code
        }).execute()
        return True
    except Exception as e:
        st.error(f"Lỗi gửi mail: {e}")
        return False

# --- 2. SCREEN A: LOGIN & ACTIVATION ---
if not st.session_state.authenticated:
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Đăng nhập")
        email_login = st.text_input("Email nhân viên:", key="login_email")
        
        if email_login:
            res = supabase.table("users").select("*").eq("email", email_login).execute()
            user_in_db = res.data[0] if res.data else None

            # Trường hợp: Đã kích hoạt
            if user_in_db and user_in_db.get('is_active'):
                pass_login = st.text_input("Mật khẩu:", type="password")
                if st.button("Đăng nhập", type="primary", use_container_width=True):
                    if pass_login == user_in_db.get('password'):
                        st.session_state.authenticated = True
                        st.session_state.user_info = user_in_db
                        st.rerun()
                    else:
                        st.error("Mật khẩu không chính xác!")

            # Trường hợp: Kích hoạt lần đầu bằng OTP
            elif user_in_db and not user_in_db.get('is_active'):
                st.warning("Tài khoản chưa kích hoạt. Vui lòng nhập mã OTP từ Email.")
                with st.form("activation_form"):
                    otp_input = st.text_input("Nhập mã OTP:")
                    new_pass = st.text_input("Thiết lập mật khẩu mới:", type="password")
                    if st.form_submit_button("Xác nhận kích hoạt", use_container_width=True):
                        if otp_input == user_in_db.get('otp_code'):
                            supabase.table("users").update({
                                "password": new_pass, "is_active": True, "otp_code": None
                            }).eq("email", email_login).execute()
                            st.success("Kích hoạt thành công! Hãy đăng nhập lại.")
                            st.rerun()
                        else: st.error("Mã OTP không chính xác!")
            elif not user_in_db:
                st.error("Email này không có trong hệ thống.")
    st.stop()

# --- 3. KHỞI TẠO BIẾN SAU LOGIN ---
current_user = st.session_state.user_info

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🤖 RAG System")
    st.write(f"Chào: **{current_user['email']}**")
    
    menu_options = ["Trò chuyện (Screen B)", "Thư viện tài liệu (Screen C)", "Cài đặt (Screen D)"]
    menu = st.radio("Menu:", menu_options)
    
    if st.button("🚪 Đăng xuất"):
        st.session_state.authenticated = False
        st.rerun()

# --- 5. SCREEN B: CHAT DASHBOARD ---
if menu == "Trò chuyện (Screen B)":
    st.header("💬 Chat Dashboard")
    category = st.selectbox("Lọc theo phòng ban:", ["All", "HR", "IT", "Sales"])
    
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("citations"):
                with st.expander("📚 Nguồn"):
                    for c in msg["citations"]: st.write(f"- {c['file']} (Trang {c['page']})")
            
            if msg["role"] == "assistant":
                col1, col2 = st.columns([0.05, 0.95])
                if col1.button("👍", key=f"up_{i}"): st.toast("Đã ghi nhận!")
                if col2.button("👎", key=f"down_{i}"): st.toast("Cảm ơn phản hồi!")

    if prompt := st.chat_input("Nhập câu hỏi..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Đang xử lý..."):
                ans, cites = st.session_state.rag_service.generate_response(prompt, category)
                st.write(ans)
                if cites:
                    with st.expander("📚 Nguồn"):
                        for c in cites: st.write(f"- {c['file']} (Trang {c['page']})")
                st.session_state.messages.append({"role": "assistant", "content": ans, "citations": cites})

# --- 6. SCREEN C: DOCUMENT LIBRARY (XEM & TẢI VỀ) ---
elif "Screen C" in menu:
    st.header("📁 Thư viện tài liệu hệ thống")
    
    # --- PHẦN 1: DÀNH CHO QUẢN TRỊ VIÊN (Nạp tài liệu) ---
    if current_user['role'] == 'Administrator':
        with st.expander("📤 Nạp tài liệu mới vào Knowledge Base", expanded=True):
            with st.form("upload_form", clear_on_submit=True):
                file = st.file_uploader("Chọn tệp PDF (Dưới 200MB):", type="pdf")
                dept = st.selectbox("Phòng ban sở hữu kiến thức:", ["HR", "IT", "Sales", "General"])
                
                if st.form_submit_button("Bắt đầu nạp dữ liệu") and file:
                    with st.spinner("Đang lưu trữ lên Cloud và tạo Vector..."):
                        try:
                            # 1. Định nghĩa đường dẫn file trong Storage (documents/public/...)
                            file_path = f"public/{file.name}"
                            
                            # 2. Upload lên Supabase Storage
                            supabase.storage.from_("documents").upload(
                                file_path, 
                                file.getvalue(), 
                                {"upsert": "true"}
                            )
                            
                            # 3. Tạo link URL tuyệt đối để tải về (Sửa lỗi Access Denied)
                            base_url = os.getenv("SUPABASE_URL")
                            # Format: https://xyz.supabase.co/storage/v1/object/public/documents/public/file.pdf
                            file_url = f"{base_url}/storage/v1/object/public/documents/{file_path}"

                            # 4. Đọc PDF và Vector hóa (Kế thừa logic cũ của bạn)
                            reader = PdfReader(file)
                            pages = [{"text": p.extract_text(), "n": i+1} for i, p in enumerate(reader.pages) if p.extract_text()]
                            
                            if pages:
                                embeddings = st.session_state.embed_model.encode([p["text"] for p in pages]).tolist()
                                data = [{
                                    "content": p["text"], 
                                    "embedding": embeddings[i], 
                                    "category": dept, 
                                    "metadata": {
                                        "file": file.name, 
                                        "page": p["n"], 
                                        "url": file_url  # QUAN TRỌNG: Lưu link này để hiện nút tải
                                    }
                                } for i, p in enumerate(pages)]
                                
                                # Lưu vào bảng kiến thức
                                supabase.table("knowledge_embeddings").insert(data).execute()
                                st.success(f"✅ Thành công: Đã nạp '{file.name}' vào bộ nhớ AI.")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi khi nạp: {str(e)}")

    # --- PHẦN 2: DANH SÁCH TÀI LIỆU (Dành cho mọi User) ---
    st.subheader("📚 Danh sách tài liệu hiện có")
    
    # Truy vấn lấy metadata và category
    res = supabase.table("knowledge_embeddings").select("metadata, category").execute()
    
    if res.data:
        # Nhóm dữ liệu để mỗi file chỉ hiển thị 1 dòng duy nhất
        unique_docs = {}
        for d in res.data:
            meta = d['metadata']
            file_name = meta.get('file', 'Unknown')
            if file_name not in unique_docs:
                unique_docs[file_name] = {
                    "category": d['category'],
                    "url": meta.get('url') # Link URL để tải về
                }

        # Hiển thị danh sách file dưới dạng các card (khung)
        for f_name, info in unique_docs.items():
            with st.container(border=True):
                # Chia cột: Tên file | Nút Tải | Nút Xóa (nếu là Admin)
                if current_user['role'] == 'Administrator':
                    col_info, col_btn, col_del = st.columns([0.5, 0.3, 0.2])
                else:
                    col_info, col_btn = st.columns([0.7, 0.3])

                with col_info:
                    st.markdown(f"📄 **{f_name}**")
                    st.caption(f"Phòng ban: {info['category']}")

                with col_btn:
                    if info['url']:
                        # Nút bấm dẫn trực tiếp tới link PDF trên Supabase
                        st.link_button("📥 Tải về / Xem", info['url'], use_container_width=True)
                    else:
                        st.warning("⚠️ Cần nạp lại file")

                if current_user['role'] == 'Administrator':
                    with col_del:
                        if st.button("🗑️ Xóa", key=f"del_{f_name}", use_container_width=True):
                            # Xóa file trên Storage
                            supabase.storage.from_("documents").remove([f"public/{f_name}"])
                            # Xóa vector trong Database
                            supabase.table("knowledge_embeddings").delete().eq("metadata->>file", f_name).execute()
                            st.success(f"Đã xóa {f_name}")
                            st.rerun()
    else:
        st.info("Hiện tại chưa có tài liệu nào được nạp vào hệ thống.")
# --- 7. SCREEN D: CÀI ĐẶT ---
else:
    st.header("⚙️ Cài đặt")
    st.write(f"Email: {current_user['email']} | Quyền: {current_user['role']}")

    with st.expander("🔑 Thay đổi mật khẩu"):
        old_p = st.text_input("Mật khẩu hiện tại:", type="password")
        new_p = st.text_input("Mật khẩu mới:", type="password")
        if st.button("Cập nhật mật khẩu"):
            if old_p == current_user.get('password'):
                supabase.table("users").update({"password": new_p}).eq("email", current_user['email']).execute()
                st.session_state.user_info['password'] = new_p
                st.success("Đã đổi mật khẩu!")
            else: st.error("Mật khẩu cũ không đúng.")

    if current_user['role'] == 'Administrator':
        st.divider()
        st.subheader("🛠️ Quản trị")
        email_invite = st.text_input("Mời email mới:")
        if st.button("Gửi mã OTP qua Email"):
            if send_gmail_otp(email_invite):
                st.success(f"Đã gửi OTP tới {email_invite}")
# import streamlit as st
# import os
# from PyPDF2 import PdfReader
# from sentence_transformers import SentenceTransformer
# from backend.services.rag_core import RAGCore
# from backend.utils.supabase_client import supabase
# import resend

# # --- CẤU HÌNH BAN ĐẦU ---
# st.set_page_config(page_title="Intelligent RAG Assistant", layout="wide")

# resend.api_key = os.getenv("RESEND_API_KEY")

# # Khởi tạo dịch vụ vào session_state để tránh khởi tạo lại khi render
# if "rag_service" not in st.session_state:
#     st.session_state.rag_service = RAGCore()
# if "embed_model" not in st.session_state:
#     st.session_state.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # --- SIDEBAR ĐIỀU HƯỚNG ---
# with st.sidebar:
#     st.title("⚙️ Hệ thống RAG")
#     menu = st.radio("Chế độ:", ["Trò chuyện (Screen B)", "Quản lý tài liệu (Screen C)"])
#     if st.button("Xóa lịch sử trò chuyện"):
#         st.session_state.messages = []
#         st.rerun()

# # --- MÀN HÌNH B: CHAT DASHBOARD ---
# if menu == "Trò chuyện (Screen B)":
#     st.header("💬 Chat Dashboard")
#     category = st.selectbox("Lọc theo phòng ban:", ["All", "HR", "IT", "Sales"])
    
#     # Hiển thị lịch sử tin nhắn
#     for msg in st.session_state.messages:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])
#             if "citations" in msg and msg["citations"]:
#                 with st.expander("📚 Nguồn trích dẫn"):
#                     for cite in msg["citations"]:
#                         st.write(f"- {cite['file']} (Trang {cite['page']})")

#     # Ô nhập liệu Chat
#     if prompt := st.chat_input("Nhập câu hỏi của bạn tại đây..."):
#         st.session_state.messages.append({"role": "user", "content": prompt})
#         with st.chat_message("user"):
#             st.markdown(prompt)

#         with st.chat_message("assistant"):
#             with st.spinner("AI đang tìm câu trả lời..."):
#                 ans, cites = st.session_state.rag_service.generate_response(prompt, category)
#                 st.markdown(ans)
#                 if cites:
#                     with st.expander("📚 Nguồn trích dẫn"):
#                         for cite in cites:
#                             st.write(f"- {cite['file']} (Trang {cite['page']})")
#                 st.session_state.messages.append({"role": "assistant", "content": ans, "citations": cites})
    
#     # Trong phần MÀN HÌNH B: CHAT DASHBOARD [cite: 327, 343]
#     for i, msg in enumerate(st.session_state.messages):
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])
            
#             # Nếu là câu trả lời của AI, thêm nút Feedback [cite: 347, 352]
#             if msg["role"] == "assistant":
#                 col1, col2 = st.columns([0.1, 0.9])
#                 with col1:
#                     # Nút Thumbs Up [cite: 190, 352]
#                     if st.button("👍", key=f"up_{i}"):
#                         supabase.table("messages").insert({
#                             "content": msg["content"], 
#                             "role": "assistant", 
#                             "user_rating": True
#                         }).execute()
#                         st.toast("Cảm ơn bạn đã phản hồi tích cực!")
#                 with col2:
#                     # Nút Thumbs Down [cite: 190, 352]
#                     if st.button("👎", key=f"down_{i}"):
#                         supabase.table("messages").insert({
#                             "content": msg["content"], 
#                             "role": "assistant", 
#                             "user_rating": False
#                         }).execute()
#                         st.toast("Chúng tôi sẽ cải thiện câu trả lời.")

# # --- MÀN HÌNH C: KNOWLEDGE MANAGEMENT ---
# else:
#     st.header("📁 Quản lý tài liệu (Admin)")
    
#     with st.form("upload_form", clear_on_submit=True):
#         uploaded_file = st.file_uploader("Chọn tệp PDF", type="pdf")
#         dept = st.selectbox("Phòng ban sở hữu:", ["HR", "IT", "Sales"])
#         submit_button = st.form_submit_button("Nạp vào hệ thống")

#     if submit_button and uploaded_file:
#         progress_bar = st.progress(0)
#         status_text = st.empty()
        
#         try:
#             # 1. Đọc toàn bộ các trang PDF
#             reader = PdfReader(uploaded_file)
#             pages_content = []
#             for i, page in enumerate(reader.pages):
#                 text = page.extract_text()
#                 if text and text.strip():
#                     pages_content.append({"text": text, "page_num": i + 1})
            
#             if not pages_content:
#                 st.error("Tệp PDF trống hoặc không thể đọc được nội dung.")
#             else:
#                 # 2. TỐI ƯU: Batch Encoding (Tạo vector hàng loạt)
#                 status_text.text("Đang tạo vector kiến thức...")
#                 texts_only = [p["text"] for p in pages_content]
#                 embeddings = st.session_state.embed_model.encode(texts_only).tolist()
                
#                 # 3. TỐI ƯU: Bulk Insert (Đẩy dữ liệu theo lô lên Supabase)
#                 status_text.text("Đang lưu vào cơ sở dữ liệu...")
#                 data_to_insert = []
#                 for i, p in enumerate(pages_content):
#                     data_to_insert.append({
#                         "content": p["text"],
#                         "embedding": embeddings[i],
#                         "category": dept,
#                         "metadata": {"file": uploaded_file.name, "page": p["page_num"]}
#                     })
                
#                 # Thực thi chèn một lần duy nhất
#                 supabase.table("knowledge_embeddings").insert(data_to_insert).execute()
                
#                 progress_bar.progress(100)
#                 st.success(f"✅ Đã nạp xong {len(data_to_insert)} trang từ file {uploaded_file.name}")
#                 st.rerun()

#         except Exception as e:
#             st.error(f"Lỗi khi xử lý file: {str(e)}")

#     # Hiển thị danh sách tài liệu hiện có
#     st.subheader("📚 Danh sách tài liệu đã nạp")
#     try:
#         # Sử dụng select distinct đơn giản thông qua metadata
#         res = supabase.table("knowledge_embeddings").select("metadata, category").execute()
#         if res.data:
#             unique_docs = {}
#             for d in res.data:
#                 file_name = d['metadata'].get('file', 'Unknown')
#                 unique_docs[file_name] = d['category']
            
#             for file, cat in unique_docs.items():
#                 st.write(f"- 📄 **{file}** ({cat})")
#     except Exception as e:
#         st.warning(f"Lỗi hiển thị danh sách: {e}")
    
#     # Trong phần MÀN HÌNH C: KNOWLEDGE MANAGEMENT [cite: 355, 386]
#     st.subheader("📚 Danh sách tài liệu đã nạp")
#     res = supabase.table("knowledge_embeddings").select("metadata, category").execute()

#     if res.data:
#         unique_docs = {d['metadata']['file']: d['category'] for d in res.data}
#         for file_name, cat in unique_docs.items():
#             col_text, col_btn = st.columns([0.8, 0.2])
#             with col_text:
#                 st.write(f"📄 **{file_name}** ({cat})")
#             with col_btn:
#                 # Chức năng xóa tài liệu (FR3.4) [cite: 183, 392]
#                 if st.button("🗑️", key=f"del_{file_name}"):
#                     supabase.table("knowledge_embeddings").delete().eq("metadata->>file", file_name).execute()
#                     st.success(f"Đã xóa {file_name}")
#                     st.rerun()
                    
# # --- CẬP NHẬT SIDEBAR ---
# with st.sidebar:
#     st.title("🤖 RAG Assistant")
#     menu = st.radio("Chế độ:", [
#         "Trò chuyện (Screen B)", 
#         "Quản lý tài liệu (Screen C)", 
#         "Cài đặt (Screen D)"
#     ])

# # --- SCREEN D: SETTINGS (Trang 22 trong tài liệu PA3) ---
# if menu == "Cài đặt (Screen D)":
#     st.header("⚙️ Cài đặt hệ thống")
    
#     # Section: Profile Information (FR1.2)
#     with st.container(border=True):
#         st.subheader("👤 Thông tin cá nhân")
#         col1, col2 = st.columns([0.2, 0.8])
#         with col1:
#             # Avatar giả lập dựa trên tên (khớp Figure 5.5)
#             st.image("https://ui-avatars.com/api/?name=Pham+Ngoc+Dung&size=128&background=random", width=100)
#         with col2:
#             st.write("**Họ và tên:** Phạm Ngọc Dũng") 
#             st.write("**Email:** dung.p@company.com")
#             st.info("**Vai trò tài khoản:** Administrator")

#     st.divider()

#     # Section: Admin Actions - Screen E (FR1.4)
#     st.subheader("🛠️ Quản trị viên")
#     st.write("Với quyền Admin, bạn có thể mời thêm nhân viên vào hệ thống tra cứu nội bộ.")
    
#     if st.button("➕ Mời thành viên mới (Screen E)", use_container_width=True):
#         st.session_state.show_invite_modal = True

#     # --- SCREEN E: INVITE MEMBER MODAL (Trang 23 trong tài liệu) ---
#     if st.session_state.get('show_invite_modal', False):
#         with st.expander("✉️ Gửi lời mời tham gia qua Email", expanded=True):
#             invite_email = st.text_input("Nhập địa chỉ email người nhận:", placeholder="example@company.com")
            
#             c1, c2 = st.columns(2)
            
#             with c1:
#                 if st.button("Gửi lời mời", type="primary", use_container_width=True):
#                     if "@" in invite_email:
#                         try:
#                             with st.spinner("Đang gửi email thật qua Resend..."):
#                                 # 1. Gửi email thật
#                                 resend.Emails.send({
#                                     "from": "RAG Assistant <onboarding@resend.dev>",
#                                     "to": [invite_email],
#                                     "subject": "Lời mời tham gia Intelligent RAG Assistant",
#                                     "html": f"""
#                                         <h3>Chào mừng bạn đến với RAG Assistant!</h3>
#                                         <p>Bạn đã được <strong>Phạm Ngọc Dũng</strong> mời tham gia hệ thống tra cứu tài liệu thông minh.</p>
#                                         <p>Vui lòng đăng nhập bằng tài khoản Google tại địa chỉ:</p>
#                                         <a href='http://localhost:8501'>Truy cập Hệ thống RAG</a>
#                                         <br><br>
#                                         <p><em>Trân trọng,<br>Đội ngũ kỹ thuật.</em></p>
#                                     """
#                                 })

#                                 # 2. Lưu vào database invitations để theo dõi (Data Design Chapter 4)
#                                 supabase.table("invitations").insert({
#                                     "email": invite_email,
#                                     "status": "Sent"
#                                 }).execute()

#                                 st.toast(f"Đã gửi mail tới {invite_email}!", icon="✅")
#                                 st.success(f"Thành công! Email mời đã được gửi đi.")
#                                 st.session_state.show_invite_modal = False
#                                 # Tự động reload để đóng modal
#                                 st.rerun()
#                         except Exception as e:
#                             st.error(f"Lỗi khi gửi email: {str(e)}")
#                     else:
#                         st.error("Vui lòng nhập định dạng email hợp lệ!")
            
#             with c2:
#                 if st.button("Hủy bỏ", use_container_width=True):
#                     st.session_state.show_invite_modal = False
#                     st.rerun()

#     st.divider()

#     # Section: Sign Out (FR1.2) - Đặt ở dưới cùng trang Settings
#     if st.button("🚪 Đăng xuất (Sign Out)", type="secondary", use_container_width=True):
#         # Theo tài liệu: Xóa session và điều hướng về Screen A
#         st.session_state.messages = []
#         # Xóa các trạng thái modal
#         if 'show_invite_modal' in st.session_state:
#             del st.session_state.show_invite_modal
            
#         st.warning("Đang kết thúc phiên làm việc...")
#         # Trong thực tế PA3, chỗ này sẽ redirect về trang Login (Screen A)
#         st.rerun()