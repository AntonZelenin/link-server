"""create users table

Revision ID: 1fd17328e23e
Revises: 
Create Date: 2024-01-21 14:28:57.578013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1fd17328e23e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(32), primary_key=True),
        sa.Column('username', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(72), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('users')
