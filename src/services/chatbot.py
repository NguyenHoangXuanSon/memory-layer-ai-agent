import logging
from typing import List
from langchain_core.documents import Document
from groq import Groq
from src.core.config import settings
from src.services.hust_search import HustRetriever
from src.core.prompt import PROMPT_SYSTEM, PROMPT_COMBINE_RETRIEVAL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BKChatbot:
    def __init__(self, model_id: str = "llama-3.3-70b-versatile"):
        if not settings.GROQ_API_KEY:
            raise ValueError("Thiếu GROQ_API_KEY trong file .env")

        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_id = model_id
        self.retriever = HustRetriever(top_k=5) 

        self.system_instruction = PROMPT_SYSTEM

    def format_context(self, docs: List[Document]) -> str:
        formatted_str = ""
        for i, doc in enumerate(docs):
            source = doc.metadata.get('source', 'Unknown')
            content = doc.page_content.replace("\n", " ").strip()
            
            formatted_str += f"--- Document #{i+1} (Source: {source}) ---\n"
            formatted_str += f"Content: {content}\n\n"
            
        return formatted_str

    def chat(self, query: str, history_context: str) -> str:
        try:
            
            relevant_docs = self.retriever.invoke(query)
            
            if not relevant_docs:
                return "No relevant documents found in the system."

            context_str = self.format_context(relevant_docs)

            full_prompt = f"""
            [RECENT CONVERSATION HISTORY]:
            {history_context}
            (Use this history to understand context, e.g. what 'it' refers to, or to make the conversation more natural)
            [Reference Documents]:
            {context_str}

            [Question]: 
            {query}

            [Answer]:
            """
    
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=1000,
                temperature=0.2,
                top_p=0.9,
            )

            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            else:
                return "The answer was blocked due to safety policy."
        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return f"Error {e}"
