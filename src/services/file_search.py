import os
from typing import List, Any, Optional, Tuple
from google import genai
from google.genai import types
import logging
from src.core.config import settings 
import time
import re
from src.core.prompt import PROMPT_FILE_SEARCH_INSTRUCTION

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GeminiRAGService:
    """
    Service to interact with Gemini API for RAG tasks, modified to use a single shared store.
    """
    def __init__(self):
        self.client =genai.Client(api_key=settings.GEMINI_API_KEY)

    def get_store_id_by_name(self, store_name: str) -> Optional[str]:
        try:
            for store in self.client.file_search_stores.list():
                if store.display_name == store_name:
                    return store.name
            return None
        except Exception as e:
            logging.error(f"Error finding store: {e}")
            return None
        
    def upload_file(self, 
                    file_path: str, 
                    file_name: str,
                    store_name: str = "rag-store")->str: 
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} does not exist")
        
        safe_file_name = re.sub(r'[^a-z0-9\-]', '-', file_name.lower()).strip('-')
        file_resource_name = f"files/{safe_file_name}" 
        
        # 1. Upload file lên Cloud
        try:
            self.client.files.upload(
                file=file_path,
                config={'name': safe_file_name, 'display_name': file_name}
            )
            logging.info(f"Uploaded file: {file_name}")

        except Exception as e:
            if "ALREADY_EXISTS" in str(e) or "409" in str(e):
                logging.info(f"File {file_name} already exists. Skipping upload.")
            else:
                raise e
        
        # 2. Tìm hoặc Tạo Store chung
        store_id = self.get_store_id_by_name(store_name)
        
        if store_id:
            logging.info(f"Found shared store: {store_name} ({store_id})")
        else:
            logging.info(f"Creating NEW shared store: {store_name}")
            new_store = self.client.file_search_stores.create(config={'display_name': store_name})
            store_id = new_store.name

        # 3. Add file vào Store
        if store_id is None:
            raise ValueError(f"Store ID for store '{store_name}' could not be determined.")
        
        operation = self.client.file_search_stores.import_file(
            file_search_store_name=store_id,
            file_name=file_resource_name, 
        )
        
        # Chờ operation xong
        while not operation.done:
            time.sleep(1)
            operation = self.client.operations.get(operation)
            
        logging.info(f"Added {file_name} to shared store: {store_name}")
        return store_id
    
    def response_document(self, question: str, store_name: str, history_context: str = "") -> Optional[str]:
        # Prompt chuẩn
        message = f"""
        {PROMPT_FILE_SEARCH_INSTRUCTION}

        [LỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY]:
        {history_context}
        (Sử dụng để hiểu ngữ cảnh, ví dụ 'file đó' là file nào)

        [YÊU CẦU HIỆN TẠI]:
        Use the following question to provide an answer based on the retrieved documents: "{question}"
        """

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", # Hoặc gemini-1.5-flash
                contents=message,
                config=types.GenerateContentConfig(
                    temperature=0.2, # Giữ ổn định
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store_name]
                            )
                        )
                    ],
                    # [QUAN TRỌNG] Thêm Safety Settings để không bị chặn
                    safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="BLOCK_NONE"
                        ),
                    ]
                )
            )

            if response.text:
                return response.text.strip()
            else:
                return "Xin lỗi, không tìm thấy thông tin trong file hoặc bị chặn bởi bộ lọc an toàn."

        except Exception as e:
            logging.error(f"Error in response_document: {e}")
            return f"Lỗi hệ thống: {e}"