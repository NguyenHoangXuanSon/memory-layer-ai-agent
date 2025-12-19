from sqlalchemy import Column, Integer, Text, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
import uuid
from sqlalchemy.schema import UniqueConstraint
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    user_input = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class LongtermMemory(Base):
    __tablename__ = "longterm_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    info_type = Column(Text, nullable=False, unique=True) 
    info_value = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('info_type', name='_info_type_uc'),
    )

class hust_documents(Base):
    __tablename__ = "hust_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    source_file = Column(Text, nullable=True)
    embedding = Column(Vector(1024))
    metadata_info = Column(JSONB, nullable=True) 
    
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())