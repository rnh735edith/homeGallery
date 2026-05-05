from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool, QueuePool
from app.config import get_settings

settings = get_settings()


def create_engine_from_url(database_url: str, db_type: str):
    """Create SQLAlchemy engine configured for the specific database type."""
    common_kwargs = {
        "pool_pre_ping": True,
    }

    if db_type == "sqlite":
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            **common_kwargs,
        )
    elif db_type == "postgresql":
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            **common_kwargs,
        )
        return engine
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


engine = create_engine_from_url(settings.DATABASE_URL, settings.db_type)

SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import app.models
    Base.metadata.create_all(bind=engine)
