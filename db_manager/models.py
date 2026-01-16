from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column,
    TIMESTAMP,
    String,
    Integer,
)
from datetime import datetime

Base = declarative_base()

class Images(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String)
    bucket = Column(String)
    uploaded_at = Column(TIMESTAMP, default=datetime.now())