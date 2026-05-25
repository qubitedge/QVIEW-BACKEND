import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class StorageService:
    def __init__(self):
        url: str = os.getenv("SUPABASE_URL", "")
        key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
        if url and key and "YOUR_SERVICE_ROLE_KEY" not in key and "your_supabase" not in key:
            try:
                self.supabase: Client = create_client(url, key)
            except Exception as e:
                print(f"Error initializing Supabase client: {e}")
                self.supabase = None
        else:
            self.supabase = None

    def upload_resume(self, file_bytes: bytes, filename: str, candidate_id: str) -> str:
        if not self.supabase:
            return "http://localhost/mock_resume_url"
        
        try:
            ext = filename.split('.')[-1]
            file_path = f"resumes/{candidate_id}/{uuid.uuid4()}.{ext}"
            
            res = self.supabase.storage.from_("candidates").upload(file_path, file_bytes)
            return self.supabase.storage.from_("candidates").get_public_url(file_path)
        except Exception as e:
            print(f"Error uploading resume to Supabase: {e}. Falling back to mock URL.")
            return "http://localhost/mock_resume_url"

    def upload_screenshot(self, image_bytes: bytes, interview_id: str) -> str:
        if not self.supabase:
            return "http://localhost/mock_screenshot_url"
            
        try:
            file_path = f"violations/{interview_id}/{uuid.uuid4()}.jpg"
            
            res = self.supabase.storage.from_("proctoring").upload(file_path, image_bytes)
            return self.supabase.storage.from_("proctoring").get_public_url(file_path)
        except Exception as e:
            print(f"Error uploading screenshot to Supabase: {e}. Falling back to mock URL.")
            return "http://localhost/mock_screenshot_url"

storage_service = StorageService()

