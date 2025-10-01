from sqlalchemy import Column, Integer, Text, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
import uuid

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
    session_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    user_info = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())