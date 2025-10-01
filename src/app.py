from fastapi import FastAPI
from pydantic import BaseModel
from src.agent_memory import MemoryAgent, MemoryConfig

app = FastAPI()

class HealthCheckResponse(BaseModel):
    status: str
    message: str

class UserInput(BaseModel):
    prompt: str

config = MemoryConfig()
agent = MemoryAgent(memory_config=config)

@app.get("/health")
def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="Successful", 
        message="Connecting succesful to FastAPI"
        )

@app.post("/ask")
def chat_with_agent(user_input: UserInput):
    try:
        agent.memory.check_and_summarize()
        agent.memory.print_summary_from_cache()
        answer = agent.process_query(user_input.prompt)
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}