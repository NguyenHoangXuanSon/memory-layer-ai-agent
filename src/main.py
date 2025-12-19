"""Main FastAPI application for Memory Layer AI Agent."""

import logging
import os
from typing import List, cast

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.services.agent import graph
from src.services.file_search import GeminiRAGService
from src.services.state import AgentState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Memory Layer AI Agent",
    description="AI Agent with memory layer and RAG capabilities",
    version="0.1.0"
)

# Initialize services
rag_service = GeminiRAGService()

# Temporary file directory
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# ============================================================================
# Models
# ============================================================================

class HealthCheck(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    message: str = Field(..., description="Status message")


class UserInput(BaseModel):
    """User input model for chat queries."""
    query: str = Field(..., min_length=1, max_length=5000, description="User query")


class FileUploadResult(BaseModel):
    """Result of a single file upload."""
    filename: str
    status: str
    store_id: str | None = None
    error: str | None = None


class UploadResponse(BaseModel):
    """Response for file upload endpoint."""
    message: str
    results: List[FileUploadResult]


class ChatResponse(BaseModel):
    """Response for chat endpoint."""
    answer: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str | None = None


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get(
    "/health",
    response_model=HealthCheck,
    summary="Health check endpoint",
    tags=["Health"]
)
async def health_check() -> HealthCheck:
    """Check if the service is running properly."""
    return HealthCheck(
        status="successful",
        message="The service is running smoothly."
    )

# ============================================================================
# File Upload Endpoint
# ============================================================================

@app.post(
    "/upload_file",
    response_model=UploadResponse,
    summary="Upload files for RAG",
    tags=["Files"]
)
async def upload_file(
    files: List[UploadFile] = File(..., description="Files to upload")
) -> UploadResponse:
    """Upload one or more files to the RAG service.
    
    Args:
        files: List of files to upload
        
    Returns:
        UploadResponse with results for each file
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    uploaded_files_info: List[FileUploadResult] = []
    logger.info(f"Starting upload of {len(files)} file(s)")

    for file in files:
        if not file.filename:
            logger.warning("File without filename skipped")
            uploaded_files_info.append(FileUploadResult(
                filename="unknown",
                status="failed",
                error="Filename is required"
            ))
            continue
            
        temp_path = os.path.join(TEMP_DIR, f"temp_{file.filename}")
        
        try:
            # Save uploaded file
            with open(temp_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            logger.info(f"Processing file: {file.filename}")
            
            # Upload to RAG service
            store_id = rag_service.upload_file(temp_path, file.filename)
            
            uploaded_files_info.append(FileUploadResult(
                filename=file.filename,
                status="success",
                store_id=store_id
            ))
            
            logger.info(f"Successfully uploaded: {file.filename} (store_id: {store_id})")
            
        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {str(e)}", exc_info=True)
            uploaded_files_info.append(FileUploadResult(
                filename=file.filename,
                status="failed",
                error=str(e)
            ))
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {temp_path}: {str(e)}")

    successful_uploads = sum(1 for f in uploaded_files_info if f.status == "success")
    logger.info(f"Upload complete: {successful_uploads}/{len(files)} successful")
    
    return UploadResponse(
        message=f"Upload hoàn tất: {successful_uploads}/{len(files)} file thành công.",
        results=uploaded_files_info
    )
# ============================================================================
# Chat Endpoint
# ============================================================================

@app.post(
    "/ask",
    response_model=ChatResponse,
    responses={
        200: {"model": ChatResponse, "description": "Successful response"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Chat with AI agent",
    tags=["Chat"]
)
async def chat_with_agent(user_input: UserInput) -> ChatResponse | JSONResponse:
    """Send a query to the AI agent and get a response.
    
    Args:
        user_input: User query input
        
    Returns:
        ChatResponse with the agent's answer
        
    Raises:
        HTTPException: If the query processing fails
    """
    try:
        logger.info(f"Processing query: {user_input.query[:100]}...")
        
        # Prepare initial state
        initial_dict = {"messages": [HumanMessage(content=user_input.query)]}
        initial_state = cast(AgentState, initial_dict)

        # Invoke the agent graph
        result = graph.invoke(initial_state)
        
        # Extract final answer
        if not result.get("messages"):
            raise ValueError("No response from agent")
            
        final_answer = result["messages"][-1].content
        
        if not final_answer:
            raise ValueError("Empty response from agent")
        
        logger.info("Query processed successfully")
        return ChatResponse(answer=final_answer)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid request", "detail": str(e)}
        )
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Lỗi trong quá trình xử lý",
                "detail": str(e)
            }
        )


# ============================================================================
# Startup and Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Memory Layer AI Agent...")
    logger.info(f"Temporary directory: {TEMP_DIR}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Memory Layer AI Agent...")


