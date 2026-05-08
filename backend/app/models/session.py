from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True) # UUID
    season = Column(Integer, index=True)
    round = Column(Integer)
    circuit_key = Column(String, ForeignKey("circuit_config.circuit_key"))
    circuit_name = Column(String)
    race_date = Column(Date)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())