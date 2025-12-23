from typing import Optional, List, Dict
import uuid
from collections import deque
from src.core.config import settings
from groq import Groq
from src.database.connection import get_connection
import json
from src.core.utils import safe_json_loads

class MemoryConfig:
    max_messages: int = 5  
    summary_length: int = 200 

class AgentMemory:
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.session_id = uuid.uuid4()
        self.summary_cache = deque(maxlen=5)
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_id = "llama-3.3-70b-versatile"

    def store_interaction(self, user_input: str, agent_response: str):

        query = """
        INSERT INTO conversations (session_id, user_input, agent_response)
        VALUES (%s, %s, %s)
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(self.session_id), user_input, agent_response))


    def create_summary(self, messages: List[Dict]) -> str:
        summary_prompt = f"""
        Summarize the following conversation in less than {self.config.summary_length} words.
        Focus on key points, decisions, and important information discovered through tool usage.

        Conversation:
        {messages}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=300,
                temperature=0.3
            )
            text = response.choices[0].message.content if response.choices else None
            if text is None:
                return "Error: response text is None"
            
            return text.strip()
        except Exception as e:
            return f"Error generating summary: {str(e)}"
        

    def store_summary(self, summary: str):
        self.summary_cache.append(summary)


    def get_recent_summary(self):
        return self.summary_cache[-1] if self.summary_cache else None
    

    def get_content_from_db(self) -> str:
        query = """
        SELECT user_input, agent_response
        FROM conversations
        WHERE session_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(self.session_id), self.config.max_messages))
                rows = cur.fetchall()

        context_parts = []
        for user_input, agent_response in reversed(rows):
            context_parts.append(f"User: {user_input}")
            context_parts.append(f"Assistant: {agent_response}")

        return "\n".join(context_parts)
    

    def check_and_summarize(self)->None:
        """Check if we need to summarize and do it if necessary"""
        query = """
        SELECT COUNT(*)
        FROM conversations
        WHERE session_id = %s
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(self.session_id),))
                row = cur.fetchone()
                count = row[0] if row else 0

                if count >= self.config.max_messages:
                    cur.execute("""
                        SELECT user_input, agent_response, timestamp
                        FROM conversations
                        WHERE session_id = %s
                        ORDER BY timestamp ASC
                        LIMIT %s
                    """, (str(self.session_id), count))

                    messages = cur.fetchall()
                    if messages:
                        message_dicts = [
                        {"user_input": row[0], "agent_response": row[1], "timestamp": row[2]}
                        for row in messages
                        ]
                        summary = self.create_summary(message_dicts)
                        self.summary_cache.clear()
                        self.summary_cache.append(summary)


    def print_summary_from_cache(self):
        if self.summary_cache:
            print("Current Summary Cache:")
            for idx, summary in enumerate(self.summary_cache):
                print(f"{idx + 1}: {summary}")
        else:
            print("Summary cache is empty.")

    def is_stored_information(self, user_input: str, agent_response: str) -> bool:
        prompt = f"""
            Analyze the following conversation.  

            Your task is to decide if the USER has revealed any **personal information** 
            that should be stored in long-term memory.  

            Personal information is STRICTLY limited to these 15 categories:  
            - name
            - age
            - gender
            - birthday
            - location
            - email
            - phone_number
            - job
            - company
            - school
            - hobbies
            - preferences
            - relationship_status
            - family_info
            - health_info

            Rules:
            - Consider ONLY the USER's message, ignore the Assistant.  
            - If the user provides information in one or more of the categories above → return "YES".  
            - If no information matches those categories → return "NO".  
            - Answer ONLY "YES" or "NO".  

            User: {user_input}  
            Assistant: {agent_response}  
        """

        try: 
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )

            text = response.choices[0].message.content.strip().upper() if response.choices else ""
            print(f"Decision text: {text}")
            return text == "YES"

        except Exception as e:
            print(f"Error deciding to store info: {e}")
            return False


    def extract_key_information(self, user_input: str, agent_response: str) -> list[dict]:
        prompt = f"""
            You are an information extractor. 
            Extract **only the personal information that the user has provided** 
            from the following conversation.

            Valid info types (15 keys total): 
            name, age, gender, birthday, location, email, phone_number, job, company, 
            school, hobbies, preferences, relationship_status, family_info, health_info

            Return ONLY valid JSON as a list of objects. 
            Format example:
            [
            {{"info_type": "name", "info_value": "Son"}},
            {{"info_type": "school", "info_value": "THPT Chuyên Thái Nguyên"}}
            ]

            Rules:
            - Only include info that was explicitly given by the user.
            - If no personal info → return [].
            - Assistant messages should be ignored.

            User: {user_input}
            Assistant: {agent_response}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1
            )
            text = response.choices[0].message.content.strip() if response.choices else ""
            cleaned_text = safe_json_loads(text)
            json_text = json.dumps(cleaned_text) if cleaned_text else "[]"
            print(f"Extracted JSON text: {json_text}")
            return json.loads(json_text) if json_text else []
        except Exception as e:
            print(f"Error extracting key info: {e}")
            return []

        
    def store_user_information(self, user_input: str, agent_response: str):
        if self.is_stored_information(user_input, agent_response):
            key_info = self.extract_key_information(user_input, agent_response)
            if key_info:
                print(f"key_infor: {key_info}")
                query = """
                        INSERT INTO longterm_memory (info_type, info_value)
                        VALUES (%s, %s)
                        ON CONFLICT (info_type) DO UPDATE
                        SET info_value = EXCLUDED.info_value,
                            timestamp = NOW();
                        """
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        for info in key_info:
                            cur.execute(query, (info["info_type"], info["info_value"]))
            else: 
                print("No key information extracted to store.")
    
    def get_longterm_memory(self):

        query = """
        SELECT info_type, info_value
        FROM longterm_memory
        ORDER BY timestamp DESC
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        
        if not rows:
            return []
        
        return [{"info_type": row[0], "info_value": row[1]} for row in rows]

    def is_used_longterm(self, user_input: str, model_fallback: bool = True) -> bool:
        
        if not user_input:
            return False
        
        low = user_input.strip().lower()

        keywords = [
            "remember", "remind", "what is my", "who am i", "do you know",
            "my profile", "my preferences", "favorite", "preferences",
            "address", "email", "phone", "where do i live", "my name", "remind me",
            "previously", "last time", "did i", "am I", "who am I", "my age", "my birthday",
        ]

        if any(keyword in low for keyword in keywords):
            print("Long-term memory usage decision (keyword-based): YES")
            return True
        
        if not model_fallback:
            print("Long-term memory usage decision (keyword-based): NO")
            return False
        
        prompt = f"""
        You are a binary classifier. Decide ONLY YES or NO whether the assistant should consult the user's long-term memory
        (containing personal information) to answer the following user request. Return exactly one word: YES or NO.

        Long-term memory contains only these personal categories:
        name, age, gender, birthday, location, email, phone_number, job, company, school,
        hobbies, preferences, relationship_status, family_info, health_info

        Guidelines:
        - If the user asks about or implies something tied to the user's history, profile, preferences, or personal data → YES.
        - If the request is generic, ephemeral, or unrelated to user-specific data → NO.
        - If unsure, answer NO (prefer not to expose personal data).
        User request:
        {user_input}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            decision = response.choices[0].message.content.strip().upper() if response.choices else ""
            print(f"Long-term memory usage decision: {decision}")
            return decision == "YES"
        except Exception as e:
            print(f"Error: {e}")
            return False

    def update_longterm_memory(self, user_input: str, agent_response: str):
        if self.is_stored_information(user_input, agent_response):
            self.store_user_information(user_input, agent_response)
                

class MemoryAgent:
    def __init__(self, memory_config: Optional[MemoryConfig] = None):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_id = "llama-3.3-70b-versatile"
        self.memory = AgentMemory(memory_config)


    def process_query(self, user_input: str) -> str:
        answer = ""  
        try:
            # 1. Tổng hợp ký ức ngắn hạn (Short-term)
            self.memory.check_and_summarize()
            context = self.memory.get_content_from_db()
            summary = self.memory.get_recent_summary()

            full_context = ""
            if summary:
                full_context += f"Previous summary:\n{summary}\n\n"
            if context:
                full_context += f"Recent conversation:\n{context}\n\n"
            
            # 2. Lấy ký ức dài hạn (Long-term)
            try:
                # Nếu câu hỏi liên quan đến thông tin cá nhân thì mới lôi ra
                if self.memory.is_used_longterm(user_input, model_fallback=True):
                    longterm_memory = self.memory.get_longterm_memory()
                    if longterm_memory:
                        full_context += "User Info:\n"
                        for item in longterm_memory:
                            full_context += f"- {item['info_type']}: {item['info_value']}\n"
            except Exception as e:
                print(f"Error retrieving long-term memory: {e}")

            # 3. Tạo Prompt
            prompt = f"""
            You are a helpful AI assistant.
            Use the conversation history and summary below (if any) to answer clearly.

            {full_context}

            Now the user says:
            {user_input}
            """
            
            # 4. Gọi Groq trả lời
            try:
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000,
                    temperature=0.3
                )

                if response.choices and response.choices[0].message.content:
                    answer = response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Error generating response: {e}")
                return "Xin lỗi, tôi đang gặp sự cố khi suy nghĩ."

            # [QUAN TRỌNG] Phải trả về câu trả lời để bên agent.py nhận được
            return answer

        except Exception as e:
            print(f"Error in process_query: {e}")
            return "An error occurred while processing the query."

    def execute_tool(self, tool_call: dict) -> str:
        try:

            result = f"Executed {tool_call['tool']} with args {tool_call['arguments']}"
            if not hasattr(self, 'last_tool_calls'):
                self.last_tool_calls = []
            self.last_tool_calls.append({
                'tool': tool_call['tool'],
                'arguments': tool_call['arguments'],
                'result': result
            })

            return result
        except Exception as e:
            return f"Error executing tool: {str(e)}"
        