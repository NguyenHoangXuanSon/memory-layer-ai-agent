from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List, cast
from src.services.memory import MemoryAgent, MemoryConfig
from src.services.file_search import GeminiRAGService
import shutil
import os
from src.services.agent import graph
from langchain_core.messages import HumanMessage
from src.services.state import AgentState
app = FastAPI()
rag_service = GeminiRAGService()

class HealthCheck(BaseModel):
    status: str
    message: str

@app.get("/health")
async def health_check() -> HealthCheck:
    return HealthCheck(status="sucessful", message="The service is running smoothly.")

class UserInput(BaseModel):
    query: str

@app.post("/upload_file")
async def upload_file(files: List[UploadFile] = File(...)):
    
    uploaded_files_info = []

    for file in files:
        temp_path = f"temp_{file.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            store_id = rag_service.upload_file(temp_path, file.filename if file.filename else "") 
            
            uploaded_files_info.append({
                "filename": file.filename, 
                "status": "success", 
                "store_id": store_id
            })
        except Exception as e:
            uploaded_files_info.append({
                "filename": file.filename, 
                "status": "failed", 
                "error": str(e)
            })
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return {"message": "Quá trình upload hoàn tất.", "results": uploaded_files_info}
@app.post("/ask")
def chat_with_agent(user_input: UserInput):
    try:
        initial_dict = {"messages": [HumanMessage(content=user_input.query)]}
        initial_state = cast(AgentState, initial_dict)

        result = graph.invoke(initial_state)
        final_answer = result["messages"][-1].content
        
        return {"answer": final_answer}
    except Exception as e:
        return {"error": f"Lỗi trong quá trình xử lý Graph: {str(e)}"}


