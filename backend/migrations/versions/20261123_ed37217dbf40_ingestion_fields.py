"""ingestion fields

Revision ID: ed37217dbf40
Revises: 4d3a2519d93a
Create Date: 2026-11-23 23:57:31.513997

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed37217dbf40'
down_revision: Union[str, Sequence[str], None] = '4d3a2519d93a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ingestion fields. Server defaults let this run on tables that already hold rows."""
    with op.batch_alter_table('import_batches', schema=None) as batch_op:
        batch_op.add_column(sa.Column('import_options', sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column('stored_filename', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('error_message', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('updated_rows', sa.Integer(), nullable=False, server_default='0'))

    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_url', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('source_url')

    with op.batch_alter_table('import_batches', schema=None) as batch_op:
        batch_op.drop_column('updated_rows')
        batch_op.drop_column('error_message')
        batch_op.drop_column('stored_filename')
        batch_op.drop_column('import_options')

