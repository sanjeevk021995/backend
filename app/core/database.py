# from sqlalchemy import create_engine, event
# from sqlalchemy.orm import sessionmaker
# from app.core.config import settings

# # 1. Configure SQLite connection arguments with a 30-second timeout to handle locked state gracefully
# is_sqlite = settings.database_url.startswith("sqlite")
# connect_args = {
#     "check_same_thread": False,
#     "timeout": 30  # Gives SQLite up to 30s to wait for write locks before raising OperationalError
# } if is_sqlite else {}

# engine = create_engine(
#     settings.database_url,
#     connect_args=connect_args,
#     pool_pre_ping=True,
# )

# # 2. Enable WAL (Write-Ahead Logging) mode and busy timeouts for SQLite
# if is_sqlite:
#     @event.listens_for(engine, "connect")
#     def set_sqlite_pragma(dbapi_connection, connection_record):
#         cursor = dbapi_connection.cursor()
#         cursor.execute("PRAGMA journal_mode=WAL")
#         cursor.execute("PRAGMA busy_timeout=30000")  # 30,000 ms timeout
#         cursor.close()

# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

is_sqlite = settings.sync_database_url.startswith("sqlite")

connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}

engine = create_engine(
    settings.sync_database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()