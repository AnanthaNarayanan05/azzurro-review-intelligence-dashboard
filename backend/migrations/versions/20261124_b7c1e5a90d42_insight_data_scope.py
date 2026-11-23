"""insight data scope

Revision ID: b7c1e5a90d42
Revises: 9968fa3529ac
Create Date: 2026-11-24 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1e5a90d42'
down_revision: Union[str, Sequence[str], None] = '9968fa3529ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('insights', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('data_scope', sa.String(length=16), server_default='genuine', nullable=False)
        )
        batch_op.create_index(batch_op.f('ix_insights_data_scope'), ['data_scope'], unique=False)
        # Autogenerate does not detect CHECK constraints, so this one is added by hand.
        batch_op.create_check_constraint(
            batch_op.f('ck_insights_data_scope_allowed'),
            "data_scope IN ('genuine', 'synthetic', 'all')",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('insights', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('ck_insights_data_scope_allowed'), type_='check')
        batch_op.drop_index(batch_op.f('ix_insights_data_scope'))
        batch_op.drop_column('data_scope')
