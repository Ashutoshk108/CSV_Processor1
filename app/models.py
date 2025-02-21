from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(Integer, index=True)
    product_name = Column(String, index=True)
    input_image_urls = Column(JSONB, default=[])
    output_image_urls = Column(JSONB, default=[])
    request_id = Column(String, index=True)
    processed = Column(Boolean, default=False)

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, connect_args={"sslmode": "require"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
