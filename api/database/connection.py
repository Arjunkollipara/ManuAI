"""Handles database connection pooling and sessions."""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import make_url

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./manufacturing.db')
connect_args = {}
if DATABASE_URL.startswith('sqlite'):
    connect_args = {'check_same_thread': False}
    engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
else:
    engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger = logging.getLogger('api.database.connection')
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

masked_url = DATABASE_URL
if '://' in DATABASE_URL and '@' in DATABASE_URL:
    prefix, rest = DATABASE_URL.split('://', 1)
    creds, host = rest.split('@', 1)
    if ':' in creds:
        user, _ = creds.split(':', 1)
        masked_url = f'{prefix}://{user}:*****@{host}'

logger.info('Database connection established with URL: %s', masked_url)


def get_database_url() -> str:
    """Return the configured database URL."""
    return DATABASE_URL


def get_database_dialect() -> str:
    """Return the active SQLAlchemy dialect name."""
    try:
        return make_url(DATABASE_URL).get_backend_name()
    except Exception:
        return 'unknown'


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
