

# Memory Layer AI Agent

## Overview
Memory Layer AI Agent is an advanced AI assistant platform that integrates a memory layer for enhanced context retention, information retrieval, and conversation summarization. The system leverages Retrieval-Augmented Generation (RAG) and modern Large Language Models (LLMs) to provide intelligent, context-aware responses and document processing capabilities.

## Features
- **AI Assistant for University Students:**
  - Answers academic and administrative questions
  - Provides guidance on university procedures
  - Supports general student inquiries and information lookup
- **Document Search and Summarization:**
  - Upload and process documents
  - Extract and summarize key information from files
- **Conversation Memory and Summarization:**
  - Stores and retrieves user interaction history
  - Generates concise conversation summaries for context continuity
- **Multi-Model Integration:**
  - Supports Gemini, Groq, Llama, and other LLMs for various tasks
- **Flexible Interfaces:**
  - REST API via FastAPI
  - Interactive chat UI via Chainlit

## Installation
### Prerequisites
- Python 3.11 or higher
- (Optional) Docker and Docker Compose

### Steps
1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd memory-layer-ai-agent
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   Or with Docker:
   ```bash
   docker-compose up --build
   ```
3. **Configure environment variables:**
   - Create a `.env` file in the project root.
   - Refer to `src/core/config.py` for required variables (API keys, database credentials, etc.).
4. **Apply database migrations (if needed):**
   ```bash
   alembic upgrade head
   ```
5. **Start the services:**
   - API server:
     ```bash
     uvicorn src.main:app --reload
     ```
   - Chainlit UI:
     ```bash
     chainlit run app.py -w
     ```

## Usage
- Access the REST API at `http://localhost:8000` (default)
- Access the Chainlit chat UI at the provided local URL after running the Chainlit command
- Upload documents, ask questions, and interact with the AI assistant via the UI or API

## Project Structure
```
├── app.py                  # Entry point for Chainlit UI
├── src/                    # Main project source code
│   ├── main.py             # FastAPI application (REST API)
│   ├── core/               # Configuration, utilities, prompts
│   ├── database/           # Database connection, models, migration
│   ├── services/           # Agent logic, memory, RAG, chatbot, file search, etc.
│   └── __init__.py         # Python package marker
├── data/                   # Sample documents for RAG, text files
├── migration/              # Database migration management (Alembic)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/           # Migration scripts
├── docker-compose.yml      # Docker orchestration
├── Dockerfile              # Application Docker image
├── pyproject.toml          # Python dependencies and project metadata
├── README.md               # Project documentation
```

### Directory Details
- **app.py**: Entry point for the Chainlit chat interface
- **src/main.py**: Main FastAPI REST API application
- **src/core/**: Configuration files, environment variables, prompts, and utility functions
- **src/database/**: Database models, connection logic, and migration scripts
- **src/services/**: Core logic for agent, memory, RAG, chatbot, and file search
- **data/**: Sample text files and documents for RAG retrieval
- **migration/**: Alembic migration scripts for database schema management
- **docker-compose.yml, Dockerfile**: Docker setup for application and database
- **pyproject.toml**: Python dependency and project configuration

## Contribution
Contributions, issues, and pull requests are welcome. Please open an issue or submit a pull request for any improvements or bug fixes.

## License
This project is licensed under the MIT License.