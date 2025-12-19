import os
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from langchain_core.embeddings import Embeddings 
from langchain_huggingface import HuggingFaceEmbeddings
from src.database.connection import SessionLocal 
from src.database.models import hust_documents

MODEL_NAME = "BAAI/bge-m3"
MODEL_KWARGS = {"device": "cuda"} 
ENCODE_KWARGS = {"normalize_embeddings": True}

file_path = "data/hust_info/BHYT.txt" 
file_name = os.path.basename(file_path)

class GenerateEmbedding:
    def __init__(self, 
                 model_name: str, 
                 model_kwargs: Dict[str, Any], 
                 encode_kwargs: Dict[str, Any]): 

        self.model_name = model_name
        self.model_kwargs = model_kwargs
        self.encode_kwargs = encode_kwargs
        
        self.model: Embeddings = self._initialize_model()

    def _initialize_model(self) -> Embeddings: 
        return HuggingFaceEmbeddings(
            model_name=self.model_name,
            model_kwargs=self.model_kwargs,
            encode_kwargs=self.encode_kwargs
        )

    def embed_query(self, query: str) -> List[float]:
        return self.model.embed_query(query)

    def embed_documents(self, chunks: List[str]) -> List[List[float]]:
        return self.model.embed_documents(chunks)

def load_chunks_from_file() -> List[str]:

    if not os.path.exists(file_path):
        logging.warning(f"File path not exists {file_path}")
        return []

    with open(file_path, 'r', encoding="utf-8") as f:
        chunks = [line.strip() for line in f if line.strip()]

    return chunks

def save_embeddings():
    db: Session = SessionLocal()
    
    try:
        embedding_tool = GenerateEmbedding(
            model_name=MODEL_NAME,
            model_kwargs=MODEL_KWARGS,
            encode_kwargs=ENCODE_KWARGS
        )

        chunks = load_chunks_from_file() 
        if not chunks:
            logging.warning(f"No chunks are created in {file_name}")
            return
        
        print(f"Đang xử lý file: {file_name} ({len(chunks)} dòng)")

        print("Đang tạo Embedding (vui lòng chờ)...")
        embedding_vectors = embedding_tool.embed_documents(chunks)
        
        print("Đang lưu vào Database...")
        db_objects = []
        
        for i, (chunk_text, vector) in enumerate(zip(chunks, embedding_vectors)):
            doc = hust_documents( 
                content=chunk_text,
                source_file=file_name,
                embedding=vector,
                metadata_info={"chunk_index": i}
            )
            db_objects.append(doc)

        db.add_all(db_objects)
        db.commit() 
        
        logging.info(f"Successfully saved {len(db_objects)} vectors for {file_name}")
        print("DONE!")

    except Exception as e:
        db.rollback() 
        logging.error(f"Error while processing and saving embeddings: {e}")

    finally:
        db.close() 
        
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    save_embeddings()