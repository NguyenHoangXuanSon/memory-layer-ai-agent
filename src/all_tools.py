import json
import google.genai as genai
from src.config import settings

client = genai.Client(api_key = settings.GEMINI_API_KEY)
model = "gemini-2.5-flash"

tools = [
    {
        "type": "function",
        "function": {
            "name": "general_response",
            "description": "Provide a general natural language response to any user question that does not require database access.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user question or prompt that needs a general answer."
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
]

def general_response(query: str) -> str:
    try:
        response = client.models.generate_content(
            model = model,
            contents = query
        )
        gemini_response = getattr(response, "text", None)
        if gemini_response: 
            gemini_response = gemini_response.strip()
        else:
            gemini_response = str(response)

        return json.dumps({
            "success": True,
            "message": gemini_response
        })
    except Exception as e:
        return json.dumps({
        "error": "Unexpected error",
        "message": str(e)
    })