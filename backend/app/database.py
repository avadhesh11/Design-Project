from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Please ensure you have a .env or .env.local file in the backend directory containing DATABASE_URL."
    )

# Use NullPool for Supabase (cloud, SSL, connection-limited) or
# QueuePool for local Postgres (load testing, no SSL overhead, no cap).
_is_local = "localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL

if _is_local:
    # Local Postgres — use a real connection pool so load tests don't pay
    # a TCP+SSL handshake cost on every single request.
    engine = create_engine(
        DATABASE_URL,
        pool_size=30,            # keep 30 warm connections
        max_overflow=20,         # allow up to 20 more under burst
        pool_timeout=30,         # wait up to 30s for a free connection
        pool_recycle=1800,       # recycle connections after 30 min
        pool_pre_ping=True,      # verify connection alive before use
    )
else:
    # Cloud Supabase — NullPool avoids keeping idle SSL connections open
    # against the free-tier connection cap (25 max).
    from sqlalchemy.pool import NullPool
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()