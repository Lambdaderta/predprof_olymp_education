"""фикс глупого алембика

Revision ID: 26df0b9a1569
Revises: ac13b93fce72
Create Date: 2026-01-29 01:20:35.505187

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "26df0b9a1569"
down_revision: Union[str, Sequence[str], None] = "ac13b93fce72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('lectures', sa.Column('lecture_name', sa.Text(), nullable=True))
    
    # Шаг 2: заполняем существующие записи
    op.execute("UPDATE lectures SET lecture_name = 'Без названия' WHERE lecture_name IS NULL")
    
    # Шаг 3: делаем NOT NULL
    op.alter_column('lectures', 'lecture_name', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('lectures', 'lecture_name')
