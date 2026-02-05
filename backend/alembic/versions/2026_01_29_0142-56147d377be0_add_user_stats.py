"""add user stats

Revision ID: 56147d377be0
Revises: 26df0b9a1569
Create Date: 2026-01-29 01:42:01.854179

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "56147d377be0"
down_revision: Union[str, Sequence[str], None] = "26df0b9a1569"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
