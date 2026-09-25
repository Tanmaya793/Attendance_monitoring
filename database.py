import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_URL = f"sqlite:///{BASE_DIR / 'attendance.db'}"

database_url = os.getenv("DATABASE_URL", "").strip() or DEFAULT_DATABASE_URL

# Some platforms historically supplied postgres:// URLs.
# SQLAlchemy expects postgresql:// / postgresql+psycopg2://.
if database_url.startswith("postgres://"):
    database_url = "postgresql+psycopg2://" + database_url[len("postgres://") :]
elif database_url.startswith("postgresql://"):
    database_url = "postgresql+psycopg2://" + database_url[len("postgresql://") :]

DATABASE_URL = database_url

engine_kwargs = {
    "future": True,
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)


if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
