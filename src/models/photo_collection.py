"""
Photo Collection model - Static lists of photos organized by user
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

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
    #   {"type": "photo", "position": 0, "photo_hothash": "abc123..."},
    #   {"type": "text", "position": 1, "text_card": {"title": "Summer", "body": "..."}},
    #   {"type": "photo", "position": 2, "photo_hothash": "def456..."}
    # ]
    items = Column(JSON, nullable=False, default=list)
    
    # Legacy: Photo list - JSON array of hothashes (kept for backward compatibility)
    # Will be auto-synced from items array
    hothashes = Column(JSON, nullable=False, default=list)
    
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
    
    def _sync_hothashes(self):
        """Sync legacy hothashes field from items array"""
        if not self.items:
            self.hothashes = []
        else:
            self.hothashes = [
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
        next_position = len(self.items)
        
        for item in new_items:
            # Skip duplicate photos
            if item.get('type') == 'photo':
                hothash = item.get('photo_hothash')
                if hothash in existing_hothashes:
                    continue
                existing_hothashes.add(hothash)
            
            # Add position
            item['position'] = next_position
            self.items.append(item)
            next_position += 1
            added += 1
        
        self._sync_hothashes()
        return added
    
    def add_photos(self, hothashes: List[str]) -> int:
        """
        Add photos to collection (backward compatibility).
        Returns number of photos added (skips duplicates).
        """
        items = [{"type": "photo", "photo_hothash": h} for h in hothashes]
        return self.add_items(items)
    
    def remove_item_at_position(self, position: int) -> bool:
        """
        Remove item at specific position.
        Recalculates positions for remaining items.
        Returns True if removed, False if position invalid.
        """
        if not self.items or position < 0 or position >= len(self.items):
            return False
        
        del self.items[position]
        
        # Recalculate positions
        for i, item in enumerate(self.items):
            item['position'] = i
        
        self._sync_hothashes()
        return True
    
    def remove_photos(self, hothashes: List[str]) -> int:
        """
        Remove photos from collection (backward compatibility).
        Returns number of photos removed.
        """
        if not self.items:
            return 0
        
        to_remove = set(hothashes)
        original_count = len(self.items)
        
        self.items = [
            item for item in self.items
            if not (item.get('type') == 'photo' and item.get('photo_hothash') in to_remove)
        ]
        
        # Recalculate positions
        for i, item in enumerate(self.items):
            item['position'] = i
        
        self._sync_hothashes()
        return original_count - len(self.items)
    
    def reorder_items(self, items: List[dict]) -> bool:
        """
        Reorder all items in collection.
        Replaces entire items array and recalculates positions.
        Returns True if successful.
        """
        # Assign positions
        for i, item in enumerate(items):
            item['position'] = i
        
        self.items = items
        self._sync_hothashes()
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
        
        return True
    
    def reorder_photos(self, hothashes: List[str]) -> bool:
        """
        Reorder photos in collection (backward compatibility).
        New list must contain exactly the same hothashes (just reordered).
        Returns True if successful, False if hothashes don't match.
        """
        if not self.items:
            return False
        
        current_hothashes = set(self.hothashes)
        if set(hothashes) != current_hothashes:
            return False
        
        # Rebuild items array with new photo order, preserving text cards
        new_items = []
        position = 0
        hothash_to_item = {
            item['photo_hothash']: item 
            for item in self.items 
            if item.get('type') == 'photo'
        }
        
        for hothash in hothashes:
            item = hothash_to_item[hothash].copy()
            item['position'] = position
            new_items.append(item)
            position += 1
        
        self.items = new_items
        self._sync_hothashes()
        return True
    
    def cleanup_invalid_hothashes(self, valid_hothashes: set) -> int:
        """
        Remove hothashes that no longer exist in database.
        Returns number of invalid hothashes removed.
        """
        if not self.hothashes:
            return 0
        
        original_count = len(self.hothashes)
        self.hothashes = [h for h in self.hothashes if h in valid_hothashes]
        
        return original_count - len(self.hothashes)
    
    def __repr__(self):
        return f"<PhotoCollection(id={self.id}, name='{self.name}', photos={self.photo_count})>"
