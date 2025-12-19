import operator
from typing import Annotated, Sequence, TypedDict, Literal, cast
from collections.abc import Hashable
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from src.core.config import settings
from src.services.state import AgentState
from src.services.file_search import GeminiRAGService
from src.services.memory import MemoryAgent, AgentMemory
from src.core.prompt import PROMPT_SUPERVISOR_ROUTER
import logging
from src.services.chatbot import BKChatbot 

STORE_NAME = "rag-store"
rag_service = GeminiRAGService()
memory_agent = MemoryAgent()
chatbot = BKChatbot()
SHARED_MEMORY = AgentMemory()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=settings.GEMINI_API_KEY
)

class RouteResponse(BaseModel):
    next: Literal["agent_response_document", "agent_response_general", "agent_response_BK_info", "FINISH"]

prompt = ChatPromptTemplate.from_messages([
    ("system", PROMPT_SUPERVISOR_ROUTER),
    MessagesPlaceholder(variable_name="messages"),
    ("system", "Bước tiếp theo là gì? Chọn agent hoặc FINISH."),
])

def node_supervisor(state: AgentState):

    input_data = {
        "messages": state["messages"] 
    }
    chain = prompt | llm.with_structured_output(RouteResponse)
    decision = cast(RouteResponse, chain.invoke(input_data))

    return {"next": decision.next}

def node_response_document(state: AgentState): 

    human_message = state["messages"][-1].content
    store_id = rag_service.get_store_id_by_name(STORE_NAME)
    
    if not store_id:
        error_message = "Hệ thống RAG chưa có dữ liệu (Store not found). Vui lòng upload tài liệu trước."
        return {"messages": [AIMessage(content=error_message, name="RAG_Agent")]}
    
    try:
        ###context = SHARED_MEMORY.get_content_from_db()
        response_text = rag_service.response_document(str(human_message), store_id)
        SHARED_MEMORY.store_interaction(human_message, response_text)
        if not response_text: 
            error_message = "Tôi đã tra cứu tài liệu nhưng không tìm thấy thông tin phù hợp."
           
        return {
            "messages": [AIMessage(content=f"Thông tin tra cứu: {response_text}", name="RAG_Agent")]
        }
    
    except Exception as e:
        error_message = f"Lỗi khi truy vấn RAG: {type(e).__name__}. Vui lòng kiểm tra API hoặc kết nối Store."
        return {"messages": [AIMessage(content=error_message, name="RAG_Agent")]}

def node_response_general(state: AgentState):
    user_query = state["messages"][-1].content
    try:
        response_text = memory_agent.process_query(str(user_query))
        SHARED_MEMORY.store_interaction(str(user_query), str(response_text))
        SHARED_MEMORY.update_longterm_memory(str(user_query), str(response_text))
        return {
            "messages": [AIMessage(content=response_text, name="General_Agent")]
        }
    except Exception as e:
         error_message = f"Lỗi xử lý bộ nhớ: {type(e).__name__}"
         return {"messages": [AIMessage(content=error_message, name="General_Agent")]}

def node_response_BK_info(state: AgentState):
    user_query = state["messages"][-1].content
    try:
        context = SHARED_MEMORY.get_content_from_db()
        response_text = chatbot.chat(user_query, context)
        SHARED_MEMORY.store_interaction(str(user_query), str(response_text))
        return {
            "messages": [AIMessage(content=response_text, name="BK_Agent")]
        }
    except Exception as e:
            error_message = f"Lỗi Chatbot BK: {type(e).__name__}"
            return {"messages": [AIMessage(content=error_message, name="BK_Agent")]}

graph = StateGraph(AgentState)

# Add nodes
graph.add_node("Supervisor", node_supervisor)
graph.add_node("agent_response_document", node_response_document)
graph.add_node("agent_response_general", node_response_general)
graph.add_node("agent_response_BK_info", node_response_BK_info)

# Add edges
graph.add_edge("agent_response_document", END) 
graph.add_edge("agent_response_general", END)
graph.add_edge("agent_response_BK_info", END)

conditional_map = {
    "agent_response_document": "agent_response_document",
    "agent_response_general": "agent_response_general",
    "agent_response_BK_info": "agent_response_BK_info", 
    "FINISH": END 
}

validated_map = cast(dict[Hashable, str], conditional_map)
graph.add_conditional_edges(
    "Supervisor", 
    lambda x: x.get("next"), 
    validated_map
)

graph.set_entry_point("Supervisor")

graph = graph.compile()

