from sqlalchemy import Column, String, Integer, Float, ForeignKey, UniqueConstraint
from app.core.database import Base


class CompoundDecayConfig(Base):
    __tablename__ = "compound_decay_config"

    id = Column(String, primary_key=True)  # UUID
    compound = Column(String, nullable=False)  # SOFT, MEDIUM, HARD, INTERMEDIATE, WET
    season = Column(Integer, nullable=False)    # e.g. 2024, 2025

    # Nullable circuit_key = global default for that season
    circuit_key = Column(String, ForeignKey("circuit_config.circuit_key"), nullable=True)
    decay_rate = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "compound", "circuit_key", "season",
            name="_compound_circuit_season_uc",
        ),
    )