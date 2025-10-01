from typing import List, Optional, TypedDict
import json
import google.genai as genai
from src.config import settings
from src.all_tools import general_response

class Message(TypedDict):
    role: str
    content: str

class Agent:
    MAX_ITERATIONS = 5
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, system_prompt: Optional[str] = None, model: str = DEFAULT_MODEL):

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.messages: List[Message] = []
        self.model = model

        default_prompt = """You are a helpful AI assistant.
        You have access to 2 tools:
        1. query_database → when the user asks about internal data
        2. general_response → when the user only greets or asks casual/general questions
        
        Always respond with JSON in the format:
        {
          "tool": "tool_name",
          "arguments": {...}
        }
        """
        
        self.messages.append({
            "role": "system",
            "content": system_prompt or default_prompt
        })
        
    def execute_tool(self, tool_name: str, args: dict) -> str:
        """Execute a specific tool with given arguments."""
        try:
            if tool_name == "general_response":
                return general_response(args["query"])
            else:
                return json.dumps({"error": f"Unknown tool {tool_name}"})
        except KeyError as e:
            return json.dumps({
                "error": f"Missing argument: {str(e)}"
            })
        except Exception as e:
            return json.dumps({
                "error": f"Tool execution failed: {str(e)}"
            })
        
    def process_query(self, user_input: str) -> str:
     
        if not user_input.strip():
            return json.dumps({"error": "Empty input"})

        self.messages.append({
            "role": "user",
            "content": user_input
        })

        try:
            current_iteration = 0
            last_response = None

            while current_iteration < self.MAX_ITERATIONS:
                current_iteration += 1

                contents = [
                    {"role": msg["role"], "parts": [msg["content"]]}
                    for msg in self.messages
                ]

                completion = self.client.models.generate_content(
                    model=self.model,
                    contents=contents
                )

                response_text = getattr(completion, "text", "").strip()
                last_response = response_text

                if not response_text:
                    continue

                try:
                    response_json = json.loads(response_text)
                    tool_name = response_json.get("tool")
                    arguments = response_json.get("arguments", {})

                    if tool_name:
                        tool_result = self.execute_tool(tool_name, arguments)
                        self.messages.append({
                            "role": "assistant",
                            "content": tool_result
                        })
                        
                        try:
                            result_json = json.loads(tool_result)
                            if "error" not in result_json:
                                return tool_result
                        except json.JSONDecodeError:
                            return tool_result
                    else:
                        return json.dumps({
                            "error": "No tool specified in response"
                        })

                except json.JSONDecodeError:
                    return json.dumps({
                        "error": "Failed to parse model response as JSON"
                    })

            max_iterations_message: Message = {
                "role": "assistant",
                "content": f"Reached maximum iterations ({self.MAX_ITERATIONS}) without success. Last response: {last_response}"
            }
            self.messages.append(max_iterations_message)
            return json.dumps(max_iterations_message)

        except Exception as e:
            error_message: Message = {
                "role": "assistant",
                "content": f"Error processing query: {str(e)}"
            }
            self.messages.append(error_message)
            return json.dumps(error_message)


    def get_conversation_history(self) -> List[Message]:
        return self.messages