import os
import sqlite3
from sqlalchemy import event, Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.base import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite+aiosqlite:///./neurovault.db"

def load_sqlite_vec(dbapi_connection, connection_record):
    """Load sqlite-vec extension for every connection."""
    print("Attempting to load sqlite-vec...")
    
    obj = dbapi_connection
    # Traverse down to find the raw sqlite3 connection
    # Possible wrappers: SQLAlchemy Adapter, aiosqlite Connection
    # We look for the method 'enable_load_extension'
    
    # Manual unwrap chain based on known libraries
    if hasattr(obj, "driver_connection"):
        obj = obj.driver_connection
    if hasattr(obj, "_conn"):
        obj = obj._conn
        
    # Check if we found it
    if hasattr(obj, "enable_load_extension"):
        try:
            obj.enable_load_extension(True)
            import sqlite_vec
            sqlite_vec.load(obj)
            obj.enable_load_extension(False)
        except Exception as e:
            logger.error(f"Failed to load sqlite-vec: {e}")
            print(f"CRITICAL ERROR LOADING SQLITE-VEC: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.warning("Deep unwrap failed to find enable_load_extension.")
        print("WARNING: Could not find enable_load_extension method on connection object.")

engine = create_async_engine(DATABASE_URL, echo=True)

# We need to listen to the 'connect' event to load the extension
# Since aiosqlite wraps the sqlite3 connection, we need to dig a bit or use the sync driver for init.
# But for async engine, we can hook into 'connect'.
@event.listens_for(engine.sync_engine, "connect")
def connect(dbapi_connection, connection_record):
    load_sqlite_vec(dbapi_connection, connection_record)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

from sqlalchemy import text

def init_db_sync(connection):
    # Ensure extension is loaded on this specific connection
    load_sqlite_vec(connection.connection, None)

    # Create the virtual table using SQLAlchemy execute
    connection.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_notes USING vec0(
            rowid INTEGER PRIMARY KEY,
            embedding FLOAT[768]
        );
    """))

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Run vector init synchronously
        await conn.run_sync(init_db_sync)

async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
