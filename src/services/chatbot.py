import logging
from typing import List
from langchain_core.documents import Document
from google import genai 
from google.genai import types
from src.core.config import settings
from src.services.hust_search import HustRetriever
from src.core.prompt import PROMPT_COMBINE_RETRIEVAL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BKChatbot:
    def __init__(self, model_id: str = "gemini-2.5-flash"):
        if not settings.GEMINI_API_KEY:
            raise ValueError("Thiếu GEMINI_API_KEY trong file .env")

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = model_id
        self.retriever = HustRetriever(top_k=5) 

        self.system_instruction = PROMPT_COMBINE_RETRIEVAL

    def format_context(self, docs: List[Document]) -> str:
        formatted_str = ""
        for i, doc in enumerate(docs):
            source = doc.metadata.get('source', 'Unknown')
            content = doc.page_content.replace("\n", " ").strip()
            
            formatted_str += f"--- Tài liệu #{i+1} (Nguồn: {source}) ---\n"
            formatted_str += f"Nội dung: {content}\n\n"
            
        return formatted_str

    def chat(self, query: str, history_context: str) -> str:
        try:
            
            relevant_docs = self.retriever.invoke(query)
            
            if not relevant_docs:
                return "Không tìm thấy tài liệu liên quan trong hệ thống."

            context_str = self.format_context(relevant_docs)

            full_prompt = f"""
            [LỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY]:
            {history_context}
            (Hãy sử dụng lịch sử này để hiểu ngữ cảnh, ví dụ 'nó' là gì, hoặc để đối thoại tự nhiên hơn)
            [Tài liệu tham khảo]:
            {context_str}

            [Câu hỏi]: 
            {query}

            [Trả lời]:
            """
    
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    max_output_tokens=1000, 
                    temperature=0.2,
                    top_p=0.9,
                )
            )

            if response.text:
                return response.text.strip()
            else:
                return "Câu trả lời bị chặn do chính sách an toàn."
        except Exception as e:
            logger.error(f"Lỗi Chatbot: {e}")
            return f"Error {e}"
