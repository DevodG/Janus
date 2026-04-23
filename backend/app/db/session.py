import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("POSTGRES_URL", "postgresql+asyncpg://user:pass@localhost/scam_db")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

from sqlalchemy import text

async def init_db():
    async with engine.begin() as conn:
        # Create pgvector extension if it exists (requires superuser or permission)
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgvector"))
        except Exception as e:
            print(f"Warning: Could not create pgvector extension: {e}")
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()
