"""remove_hothashes_column

Revision ID: e31abd270430
Revises: 3f8a9b2c4d5e
Create Date: 2025-12-18 16:56:48.007789

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e31abd270430'
down_revision: Union[str, Sequence[str], None] = '3f8a9b2c4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove hothashes column - data is in items array"""
    op.drop_column('photo_collections', 'hothashes')


def downgrade() -> None:
    """Restore hothashes column"""
    op.add_column('photo_collections', 
        sa.Column('hothashes', sa.JSON(), nullable=False, server_default='[]')
    )
    
    # Rebuild hothashes from items array
    connection = op.get_bind()
    
    if connection.dialect.name == 'postgresql':
        connection.execute(sa.text("""
            UPDATE photo_collections
            SET hothashes = COALESCE(
                (
                    SELECT json_agg(item->>'photo_hothash')
                    FROM json_array_elements(items::json) AS item
                    WHERE item->>'type' = 'photo'
                ),
                '[]'::json
            )
        """))
    else:
        # SQLite - row by row
        result = connection.execute(sa.text("SELECT id, items FROM photo_collections"))
        import json
        for row in result:
            collection_id = row[0]
            items = row[1] or []
            
            if isinstance(items, str):
                items = json.loads(items)
            
            hothashes = [
                item['photo_hothash']
                for item in items
                if item.get('type') == 'photo'
            ]
            
            connection.execute(
                sa.text("UPDATE photo_collections SET hothashes = :hothashes WHERE id = :id"),
                {"hothashes": json.dumps(hothashes), "id": collection_id}
            )
