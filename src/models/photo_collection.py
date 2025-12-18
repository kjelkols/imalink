"""
Photo Collection model - Static lists of photos organized by user
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.orm.attributes import flag_modified

from .base import Base
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .user import User


class PhotoCollection(Base, TimestampMixin):
    """
    User-defined static collection of photos.
    
    Unlike SavedPhotoSearch (dynamic, criteria-based), PhotoCollection is a
    static list of specific photos identified by their hothashes.
    
    Features:
    - Flat organization (no hierarchy)
    - User-owned (no sharing yet)
    - Ordered array (order matters)
    - Auto cover photo (first in list)
    """
    __tablename__ = "photo_collections"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Ownership
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Collection metadata
    name = Column(String(255), nullable=False)          # "Best of Italy 2024"
    description = Column(Text)                          # Optional notes
    
    # Items - Mixed content (photos + text cards) in display order
    # Example: [
    #   {"type": "photo", "photo_hothash": "abc123..."},
    #   {"type": "text", "text_card": {"title": "Summer", "body": "..."}},
    #   {"type": "photo", "photo_hothash": "def456..."}
    # ]
    # Position is implicit from array index
    items = Column(JSON, nullable=False, default=list)
    
    # Timestamps via TimestampMixin (created_at, updated_at)
    
    # Relationships
    user = relationship("User", back_populates="photo_collections")
    
    @property
    def item_count(self) -> int:
        """Total number of items (photos + text cards)"""
        return len(self.items) if self.items else 0
    
    @property
    def photo_count(self) -> int:
        """Number of photo items in collection"""
        if not self.items:
            return 0
        return sum(1 for item in self.items if item.get('type') == 'photo')
    
    @property
    def text_card_count(self) -> int:
        """Number of text card items in collection"""
        if not self.items:
            return 0
        return sum(1 for item in self.items if item.get('type') == 'text')
    
    @property
    def cover_photo_hothash(self) -> Optional[str]:
        """First photo serves as cover photo (skips text cards)"""
        if not self.items:
            return None
        for item in self.items:
            if item.get('type') == 'photo':
                return item.get('photo_hothash')
        return None
    
    @property
    def hothashes(self) -> List[str]:
        """List of photo hothashes (computed from items array)"""
        if not self.items:
            return []
        return [
            item['photo_hothash'] 
            for item in self.items 
            if item.get('type') == 'photo' and item.get('photo_hothash')
        ]
    
    def add_items(self, new_items: List[dict]) -> int:
        """
        Add items to collection (append to end).
        Returns number of items added (skips duplicate photos).
        
        new_items format:
        - Photo: {"type": "photo", "photo_hothash": "abc123..."}
        - Text: {"type": "text", "text_card": {"title": "...", "body": "..."}}
        """
        if not self.items:
            self.items = []
        
        existing_hothashes = {
            item['photo_hothash'] 
            for item in self.items 
            if item.get('type') == 'photo'
        }
        
        added = 0
        
        for item in new_items:
            # Skip duplicate photos
            if item.get('type') == 'photo':
                hothash = item.get('photo_hothash')
                if hothash in existing_hothashes:
                    continue
                existing_hothashes.add(hothash)
            
            # Strip position field if present (not needed - array index is position)
            item_copy = {k: v for k, v in item.items() if k != 'position'}
            self.items.append(item_copy)
            added += 1
        
        # Flag the column as modified for SQLAlchemy
        flag_modified(self, 'items')
        return added
    
    def remove_item_at_position(self, position: int) -> bool:
        """
        Remove item at specific position (array index).
        Returns True if removed, False if position invalid.
        """
        if not self.items or position < 0 or position >= len(self.items):
            return False
        
        del self.items[position]
        flag_modified(self, 'items')
        return True
    
    def reorder_items(self, items: List[dict]) -> bool:
        """
        Reorder all items in collection.
        Replaces entire items array (position is implicit from array index).
        Returns True if successful.
        """
        # Strip position fields if present
        self.items = [{k: v for k, v in item.items() if k != 'position'} for item in items]
        flag_modified(self, 'items')
        return True
    
    def update_text_card(self, position: int, title: Optional[str] = None, body: Optional[str] = None) -> bool:
        """
        Update text card content at position.
        Returns True if updated, False if position invalid or not a text card.
        """
        if not self.items or position < 0 or position >= len(self.items):
            return False
        
        item = self.items[position]
        if item.get('type') != 'text' or 'text_card' not in item:
            return False
        
        if title is not None:
            item['text_card']['title'] = title
        if body is not None:
            item['text_card']['body'] = body
        
        # Flag the column as modified for SQLAlchemy
        flag_modified(self, 'items')
        return True
    
    def __repr__(self):
        return f"<PhotoCollection(id={self.id}, name='{self.name}', photos={self.photo_count})>"
