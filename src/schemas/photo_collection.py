"""
Photo Collection schemas - Pydantic models for API operations
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, field_validator


# Collection item schemas
class TextCardContent(BaseModel):
    """Text card content"""
    title: str = Field(..., max_length=200, description="Card title")
    body: str = Field(..., max_length=2000, description="Card body (plain text)")
    
    @field_validator('title', 'body')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class CollectionItemPhoto(BaseModel):
    """Photo item in collection (position is implicit from array index)"""
    type: Literal['photo'] = 'photo'
    photo_hothash: str = Field(..., min_length=1)


class CollectionItemText(BaseModel):
    """Text card item in collection (position is implicit from array index)"""
    type: Literal['text'] = 'text'
    text_card: TextCardContent


# Union type for items
CollectionItem = CollectionItemPhoto | CollectionItemText


# Base schemas
class PhotoCollectionBase(BaseModel):
    """Base schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    description: Optional[str] = Field(None, description="Optional description")


class PhotoCollectionCreate(PhotoCollectionBase):
    """Schema for creating new collection"""
    hothashes: List[str] = Field(default_factory=list, description="Initial photos (optional)")
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Collection name cannot be empty or whitespace only')
        return v.strip()


class PhotoCollectionUpdate(BaseModel):
    """Schema for updating collection metadata (not photos)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError('Collection name cannot be empty or whitespace only')
        return v.strip() if v else None


class PhotoCollectionResponse(PhotoCollectionBase):
    """Schema for collection in API responses"""
    id: int
    user_id: int
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Ordered items (photos + text cards)")
    item_count: int = Field(..., description="Total number of items")
    photo_count: int = Field(..., description="Number of photo items")
    text_card_count: int = Field(..., description="Number of text card items")
    hothashes: List[str] = Field(default_factory=list, description="Legacy: photo hothashes only")
    cover_photo_hothash: Optional[str] = Field(None, description="First photo (cover)")
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# Photo management schemas
class AddPhotosRequest(BaseModel):
    """Request to add photos to collection"""
    hothashes: List[str] = Field(..., min_length=1, description="Photos to add")
    
    @field_validator('hothashes')
    @classmethod
    def validate_hothashes(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('Must provide at least one hothash')
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for h in v:
            if h not in seen:
                seen.add(h)
                unique.append(h)
        return unique


class RemovePhotosRequest(BaseModel):
    """Request to remove photos from collection"""
    hothashes: List[str] = Field(..., min_length=1, description="Photos to remove")
    
    @field_validator('hothashes')
    @classmethod
    def validate_hothashes(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('Must provide at least one hothash')
        return list(set(v))  # Remove duplicates


class ReorderPhotosRequest(BaseModel):
    """Request to reorder photos in collection"""
    hothashes: List[str] = Field(..., min_length=1, description="All photos in new order")
    
    @field_validator('hothashes')
    @classmethod
    def validate_hothashes(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('Must provide at least one hothash')
        if len(v) != len(set(v)):
            raise ValueError('Duplicate hothashes not allowed in reorder')
        return v


class AddItemsRequest(BaseModel):
    """Request to add items to collection"""
    items: List[Dict[str, Any]] = Field(..., min_length=1, description="Items to add")
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not v:
            raise ValueError('Must provide at least one item')
        
        for item in v:
            item_type = item.get('type')
            if item_type == 'photo':
                if 'photo_hothash' not in item or not item['photo_hothash']:
                    raise ValueError('Photo items must have photo_hothash')
            elif item_type == 'text':
                if 'text_card' not in item:
                    raise ValueError('Text items must have text_card')
                card = item['text_card']
                if not isinstance(card, dict) or 'title' not in card or 'body' not in card:
                    raise ValueError('text_card must have title and body')
                if len(card['title']) > 200:
                    raise ValueError('Text card title max 200 characters')
                if len(card['body']) > 2000:
                    raise ValueError('Text card body max 2000 characters')
            else:
                raise ValueError(f'Invalid item type: {item_type}. Must be "photo" or "text"')
        
        return v


class ReorderItemsRequest(BaseModel):
    """Request to reorder all items in collection"""
    items: List[Dict[str, Any]] = Field(..., min_length=1, description="All items in new order")
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not v:
            raise ValueError('Must provide at least one item')
        
        # Validate structure (same as AddItemsRequest)
        for item in v:
            item_type = item.get('type')
            if item_type == 'photo':
                if 'photo_hothash' not in item or not item['photo_hothash']:
                    raise ValueError('Photo items must have photo_hothash')
            elif item_type == 'text':
                if 'text_card' not in item:
                    raise ValueError('Text items must have text_card')
            else:
                raise ValueError(f'Invalid item type: {item_type}')
        
        return v


class UpdateTextCardRequest(BaseModel):
    """Request to update text card content"""
    title: Optional[str] = Field(None, max_length=200)
    body: Optional[str] = Field(None, max_length=2000)
    
    @field_validator('title', 'body')
    @classmethod
    def strip_if_provided(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v is not None else None


class PhotoManagementResponse(BaseModel):
    """Response for photo add/remove/reorder operations"""
    collection_id: int
    item_count: int = Field(..., description="New item count after operation")
    photo_count: int = Field(..., description="New photo count after operation")
    affected_count: int = Field(..., description="Number of items added/removed")
    cover_photo_hothash: Optional[str] = Field(None, description="New cover photo")


class CollectionListResponse(BaseModel):
    """Response for listing collections"""
    collections: List[PhotoCollectionResponse]
    total: int = Field(..., description="Total number of collections")
