"""add_pit_stop_unique_constraint

Revision ID: 9b40b2d55cae
Revises: 170a880675cc
Create Date: 2026-05-09 23:51:11.217701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b40b2d55cae'
down_revision: Union[str, Sequence[str], None] = '170a880675cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_pit_stop_session_driver_lap',
        'pit_stops',
        ['session_id', 'driver_code', 'lap']
    )

def downgrade() -> None:
    op.drop_constraint('uq_pit_stop_session_driver_lap', 'pit_stops', type_='unique')