from sqlalchemy import Column, String, Float, Text
from app.core.database import Base

class CircuitConfig(Base):
    __tablename__ = "circuit_config"

    circuit_key = Column(String, primary_key=True, index=True)
    pit_loss_estimate = Column(Float, nullable=False)  # Standard Green Flag loss
    sc_loss_factor = Column(Float, default=0.6)        # Multiplier for SC/VSC windows
    circuit_type = Column(String)                      # 'street', 'permanent', 'hybrid'
    notes = Column(Text, nullable=True)