"""add items to collections

Revision ID: 3f8a9b2c4d5e
Revises: 2ad05d562f3b
Create Date: 2025-12-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3f8a9b2c4d5e'
down_revision: Union[str, None] = '2ad05d562f3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add items column and migrate existing hothashes to items format"""
    
    # Add items column (default empty array)
    op.add_column('photo_collections', 
        sa.Column('items', sa.JSON(), nullable=False, server_default='[]')
    )
    
    # Migrate existing hothashes to items format
    # This needs to be done in SQL to handle JSON properly
    connection = op.get_bind()
    
    # For PostgreSQL
    if connection.dialect.name == 'postgresql':
        connection.execute(sa.text("""
            UPDATE photo_collections
            SET items = (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'type', 'photo',
                        'position', position - 1,
                        'photo_hothash', hothash
                    )
                )
                FROM unnest(hothashes) WITH ORDINALITY AS t(hothash, position)
            )
            WHERE hothashes IS NOT NULL AND jsonb_array_length(hothashes) > 0
        """))
    else:
        # For SQLite - fetch and update row by row
        result = connection.execute(sa.text("SELECT id, hothashes FROM photo_collections WHERE hothashes IS NOT NULL"))
        
        for row in result:
            collection_id = row[0]
            hothashes = row[1]
            
            if hothashes and len(hothashes) > 0:
                import json
                items = [
                    {
                        "type": "photo",
                        "position": i,
                        "photo_hothash": hothash
                    }
                    for i, hothash in enumerate(hothashes)
                ]
                
                connection.execute(
                    sa.text("UPDATE photo_collections SET items = :items WHERE id = :id"),
                    {"items": json.dumps(items), "id": collection_id}
                )


def downgrade() -> None:
    """Remove items column (data loss)"""
    op.drop_column('photo_collections', 'items')
