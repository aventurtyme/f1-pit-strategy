from sqlalchemy import Column, String, Integer, Float, ForeignKey, Boolean, UniqueConstraint
from app.core.database import Base


class PitStop(Base):
    __tablename__ = "pit_stops"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    driver_code = Column(String(3))
    team = Column(String)
    lap = Column(Integer)

    # Tire Data
    tire_age_self = Column(Integer)
    compound_self = Column(String)

    # Timing Data
    gap_behind = Column(Float)

    # Analytical Outputs
    ptl = Column(Float)             # Pre-Pit Threat Level
    ppd = Column(Integer)           # Post-Pit Position Delta
    uts = Column(Float)             # Undercut Threat Score
    strategy_type = Column(String)  # 'proactive', 'reactive', 'neutral'

    # Environmental Context
    race_flag = Column(String)      # 'green', 'sc', 'vsc', 'red'
    pit_loss_used = Column(Float)   # The actual loss value used in PTL math
    is_opportunistic = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint(
            "session_id", "driver_code", "lap",
            name="uq_pit_stop_session_driver_lap",
        ),
    )