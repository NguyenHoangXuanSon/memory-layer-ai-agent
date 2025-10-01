from typing import Optional, List, Dict
import uuid
from collections import deque
from src.config import settings
import google.genai as genai
from src.db_connection import get_connection

class MemoryConfig:
    max_messages: int = 5  
    summary_length: int = 200 

class AgentMemory:
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.session_id = uuid.uuid4()
        self.summary_cache = deque(maxlen=5)

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
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=summary_prompt
            )
            text = getattr(response, "text", None)
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


class MemoryAgent:
    def __init__(self, memory_config: Optional[MemoryConfig] = None):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.memory = AgentMemory(memory_config)


    def process_query(self, user_input: str) -> str:
        try:
            self.memory.check_and_summarize()
            context = self.memory.get_content_from_db()
            summary = self.memory.get_recent_summary()

            full_context = ""
            if summary:
                full_context += f"Previous summary:\n{summary}\n\n"
            if context:
                full_context += f"Recent conversation:\n{context}\n\n"

            prompt = f"""
            You are a helpful AI assistant.
            Use the conversation history and summary below (if any) to answer clearly.

            {full_context}

            Now the user says:
            {user_input}
            """

            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            if response.text:
                answer = response.text.strip()
            else:
                answer = ""

            self.memory.store_interaction(
                user_input=user_input,
                agent_response=answer,
            )

            return answer

        except Exception as e:
            error_message = f"Error processing query: {str(e)}"
            self.memory.store_interaction(
                user_input=user_input,
                agent_response=error_message,
            )
            return error_message
        

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
        
