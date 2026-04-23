import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ScamEvent, Entity, EventEntity
from app.schemas.response import AnalyzeResponse
from app.db.session import AsyncSessionLocal
from sqlalchemy import select, update
import uuid
from datetime import datetime

from app.services.scam_graph import scam_graph
from app.services.simulation_engine import simulation_engine

class MemoryService:
    async def save_event(self, response: AnalyzeResponse, metadata: dict, embedding: list = None):
        async with AsyncSessionLocal() as session:
            # 1. Save Event to Postgres
            event = ScamEvent(
                id=uuid.UUID(response.id),
                text=response.text,
                source=response.source,
                risk_score=response.risk_score,
                decision=response.decision,
                event_metadata={
                    "reasons": response.reasons,
                    "intent": response.intent.dict(),
                    "entities": response.entities.dict(),
                    **metadata
                },
                embedding=embedding
            )
            session.add(event)
            
            # 2. Add to Scam Journey Graph (Depth)
            graph_entities = {
                "phones": response.entities.phones,
                "upi_ids": response.entities.upi_ids,
                "links": response.entities.domains
            }
            # Normalize intent signals for graph
            signals = {
                "urgency": int(response.intent.urgency * 10),
                "impersonation": int(response.intent.impersonation * 10),
                "payment": int(response.intent.payment * 10)
            }
            scam_graph.add_event(response.source, graph_entities, signals)
            
            # 3. Optimization: Autonomous Security Drill
            if response.risk_score > 85:
                drill_scenario = f"The user has received this suspicious intake: '{response.text[:200]}...'. Simulation: What is the most likely social engineering escalation the scammer will try next?"
                # Trigger background simulation
                asyncio.create_task(simulation_engine.run_simulation(drill_scenario, {"source": response.source, "risk": response.risk_score}))

            # 4. Process Entities for relational mapping
            for phone in response.entities.phones:
                await self._upsert_entity(session, "phone", phone, event.id)
            for upi in response.entities.upi_ids:
                await self._upsert_entity(session, "upi", upi, event.id)
            for domain in response.entities.domains:
                await self._upsert_entity(session, "domain", domain, event.id)
                
            await session.commit()

    async def _upsert_entity(self, session: AsyncSession, e_type: str, value: str, event_id: uuid.UUID):
        stmt = select(Entity).where(Entity.type == e_type, Entity.value == value)
        result = await session.execute(stmt)
        entity = result.scalar_one_or_none()
        
        if not entity:
            entity = Entity(type=e_type, value=value)
            session.add(entity)
            await session.flush()
        else:
            entity.last_seen = datetime.utcnow()
            
        # Link to event
        link = EventEntity(event_id=event_id, entity_id=entity.id)
        session.add(link)

memory_service = MemoryService()
