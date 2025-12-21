import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv() 

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

print(f"DEBUG: URL found: {url is not None}")

if not url or not key:
    raise ValueError("Thiếu SUPABASE_URL hoặc SUPABASE_SERVICE_KEY trong tệp cấu hình")

supabase = create_client(url, key)