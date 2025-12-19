import logging
from typing import List, Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from src.database.connection import SessionLocal
from src.database.models import hust_documents
from src.services.embedding import GenerateEmbedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMBED_MODEL = "BAAI/bge-m3"
DEVICE = "cuda"
ENCODE_KWARGS = {"normalize_embeddings": True}

class HustRetriever(BaseRetriever):
    top_k: int = 10          
    embedding_tool: Any = None 

    def __init__(self, top_k: int = 10, **kwargs):
        embed_tool = GenerateEmbedding(
            model_name=EMBED_MODEL,
            model_kwargs={"device": DEVICE},
            encode_kwargs=ENCODE_KWARGS
        )
        super().__init__(top_k=top_k, embedding_tool=embed_tool, **kwargs)

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        
        db: Session = SessionLocal()
        try:
            query_vector = self.embedding_tool.embed_query(query)
            
            stmt = select(hust_documents).order_by(
                hust_documents.embedding.cosine_distance(query_vector)
            ).limit(self.top_k)
            
            results = db.execute(stmt).scalars().all()
            
            final_docs = []
            for item in results:
                doc = Document(
                    page_content=item.content,
                    metadata={
                        "source": item.source_file,
                        "id": item.id,
                        **(item.metadata_info if item.metadata_info else {})
                    }
                )
                final_docs.append(doc)
                
            return final_docs

        except Exception as e:
            logger.error(f"Error: {e}")
            return []
        finally:
            db.close()