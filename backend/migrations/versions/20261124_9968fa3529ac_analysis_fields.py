"""analysis fields

Revision ID: 9968fa3529ac
Revises: ed37217dbf40
Create Date: 2026-11-24 00:29:32.701003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9968fa3529ac'
down_revision: Union[str, Sequence[str], None] = 'ed37217dbf40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('analysis_status', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('analysed_run_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_reviews_analysis_status'), ['analysis_status'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_reviews_analysed_run_id_analysis_runs'), 'analysis_runs', ['analysed_run_id'], ['id'], ondelete='SET NULL')
        # Autogenerate does not detect CHECK constraints, so this one is added by hand.
        batch_op.create_check_constraint(
            batch_op.f('ck_reviews_analysis_status_allowed'),
            "analysis_status IN ('analysed', 'no_text', 'non_english')",
        )



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('ck_reviews_analysis_status_allowed'), type_='check')
        batch_op.drop_constraint(batch_op.f('fk_reviews_analysed_run_id_analysis_runs'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_reviews_analysis_status'))
        batch_op.drop_column('analysed_run_id')
        batch_op.drop_column('analysis_status')
