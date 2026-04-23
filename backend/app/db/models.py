from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from datetime import datetime
import uuid

# Note: pgvector requires 'pgvector' extension in Postgres
# and 'pgvector' python package.
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback for environments where pgvector isn't installed yet
    class Vector: 
        def __init__(self, *args, **kwargs): pass

class ScamEvent(Base):
    __tablename__ = "scam_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(String, nullable=False)
    source = Column(String)
    risk_score = Column(Float)
    decision = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    event_metadata = Column("metadata", JSON) # Store intent and extra details
    embedding = Column(Vector(384)) # matches sentence-transformers (e.g. all-MiniLM-L6-v2)

class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String) # "phone", "upi", "domain", "brand"
    value = Column(String, unique=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    reputation_score = Column(Float, default=0.0)

class EventEntity(Base):
    __tablename__ = "event_entities"
    event_id = Column(UUID(as_uuid=True), ForeignKey("scam_events.id"), primary_key=True)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), primary_key=True)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("scam_events.id"))
    is_scam = Column(Boolean)
    correct_category = Column(String)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
