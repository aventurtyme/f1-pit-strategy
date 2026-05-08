from sqlalchemy import Column, String, Float, ForeignKey, UniqueConstraint
from app.core.database import Base

class CompoundDecayConfig(Base):
    __tablename__ = "compound_decay_config"

    id = Column(String, primary_key=True)  # UUID
    compound = Column(String, nullable=False) # SOFT, MEDIUM, HARD, INTERMEDIATE, WET
    
    # Nullable circuit_key allows for Global Defaults
    circuit_key = Column(String, ForeignKey("circuit_config.circuit_key"), nullable=True)
    decay_rate = Column(Float, nullable=False)

    __table_args__ = (UniqueConstraint('compound', 'circuit_key', name='_compound_circuit_uc'),)