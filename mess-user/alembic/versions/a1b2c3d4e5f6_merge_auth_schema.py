"""merge auth schema: rename id to user_id, add hashed_password, create refresh_tokens

Revision ID: a1b2c3d4e5f6
Revises: 870624ffa6a7
Create Date: 2026-02-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '870624ffa6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename primary key column from 'id' to 'user_id'
    op.alter_column('users', 'id', new_column_name='user_id')

    # Add hashed_password column
    op.add_column('users', sa.Column('hashed_password', sa.String(72), nullable=False))

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.String(32), nullable=False),
        sa.Column('token', sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table('refresh_tokens')
    op.drop_column('users', 'hashed_password')
    op.alter_column('users', 'user_id', new_column_name='id')
