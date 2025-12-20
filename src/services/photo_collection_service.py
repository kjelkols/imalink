"""
Photo Collection service - Business logic layer
"""
from typing import List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.photo_collection import PhotoCollection
from src.models.photo import Photo
from src.repositories.photo_collection_repository import PhotoCollectionRepository
from src.repositories.photo_repository import PhotoRepository
from src.schemas.photo_collection import (
    PhotoCollectionCreate,
    PhotoCollectionUpdate,
    PhotoCollectionResponse,
    AddItemsRequest,
    ReorderItemsRequest,
    UpdateTextCardRequest,
    InsertItemsRequest,
    MoveItemsRequest,
    DeleteItemsRequest,
    PhotoManagementResponse,
    CollectionListResponse
)


class PhotoCollectionService:
    """Service for photo collection business logic"""
    
    def __init__(self, db: Session):
        self.db = db
        self.collection_repo = PhotoCollectionRepository(db)
        self.photo_repo = PhotoRepository(db)
    
    # CRUD operations
    
    def create_collection(self, user_id: int, collection_data: PhotoCollectionCreate) -> PhotoCollectionResponse:
        """
        Create new photo collection.
        Validates that initial photos exist and belong to user.
        """
        # Validate initial photos if provided
        if collection_data.hothashes:
            valid_hothashes = self._validate_user_photos(user_id, collection_data.hothashes)
            if len(valid_hothashes) < len(collection_data.hothashes):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Some photos not found or don't belong to user"
                )
        
        # Check for duplicate name
        existing = self.collection_repo.get_collection_by_name(user_id, collection_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Collection with name '{collection_data.name}' already exists"
            )
        
        collection = self.collection_repo.create(user_id, collection_data)
        return PhotoCollectionResponse.model_validate(collection)
    
    def get_collection(self, collection_id: int, user_id: int) -> PhotoCollectionResponse:
        """Get collection by ID"""
        from src.schemas.photo_collection import normalize_collection_items
        
        collection = self._get_collection_or_404(collection_id, user_id)
        response = PhotoCollectionResponse.model_validate(collection)
        
        # Normalize items to ensure visible field exists
        response.items = normalize_collection_items(response.items)
        
        return response
    
    def list_collections(self, user_id: int, skip: int = 0, limit: int = 100) -> CollectionListResponse:
        """List all collections for user"""
        from src.schemas.photo_collection import normalize_collection_items
        
        collections = self.collection_repo.get_all_for_user(user_id, skip, limit)
        total = self.collection_repo.count_for_user(user_id)
        
        collection_responses = []
        for c in collections:
            response = PhotoCollectionResponse.model_validate(c)
            response.items = normalize_collection_items(response.items)
            collection_responses.append(response)
        
        return CollectionListResponse(
            collections=collection_responses,
            total=total
        )
    
    def update_collection(
        self, 
        collection_id: int, 
        user_id: int, 
        update_data: PhotoCollectionUpdate
    ) -> PhotoCollectionResponse:
        """Update collection metadata"""
        collection = self._get_collection_or_404(collection_id, user_id)
        
        # Check for duplicate name if changing name
        if update_data.name and update_data.name != collection.name:
            existing = self.collection_repo.get_collection_by_name(user_id, update_data.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Collection with name '{update_data.name}' already exists"
                )
        
        updated_collection = self.collection_repo.update(collection, update_data)
        return PhotoCollectionResponse.model_validate(updated_collection)
    
    def delete_collection(self, collection_id: int, user_id: int) -> bool:
        """Delete collection"""
        collection = self._get_collection_or_404(collection_id, user_id)
        return self.collection_repo.delete(collection)
    
    def cleanup_collection(self, collection_id: int, user_id: int) -> int:
        """
        Remove invalid photos from collection items.
        Returns number of invalid photos removed.
        """
        collection = self._get_collection_or_404(collection_id, user_id)
        
        if not collection.items:
            return 0
        
        # Extract photo hothashes from items
        photo_hothashes = [
            item['photo_hothash']
            for item in collection.items
            if item.get('type') == 'photo'
        ]
        
        if not photo_hothashes:
            return 0
        
        # Get valid hothashes
        valid_hothashes = self._validate_user_photos(user_id, photo_hothashes)
        
        # Remove invalid photos from items
        original_count = len(collection.items)
        collection.items = [
            item for item in collection.items
            if item.get('type') != 'photo' or item.get('photo_hothash') in valid_hothashes
        ]
        
        removed_count = original_count - len(collection.items)
        
        if removed_count > 0:
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(collection, 'items')
            self.db.commit()
        
        return removed_count
    
    # Helper methods
    
    def _get_collection_or_404(self, collection_id: int, user_id: int) -> PhotoCollection:
        """Get collection or raise 404"""
        collection = self.collection_repo.get_by_id(collection_id, user_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_id} not found"
            )
        return collection
    
    def _validate_user_photos(self, user_id: int, hothashes: List[str]) -> Set[str]:
        """
        Validate that photos exist and belong to user.
        Returns set of valid hothashes.
        """
        photos = self.photo_repo.get_by_hothashes(hothashes, user_id)
        return {p.hothash for p in photos}
    
    # NEW: Item management operations (photos + text cards)
    
    def add_items(
        self,
        collection_id: int,
        user_id: int,
        request: AddItemsRequest
    ) -> PhotoManagementResponse:
        """
        Add items (photos and/or text cards) to collection.
        Validates photos exist and belong to user.
        """
        collection = self._get_collection_or_404(collection_id, user_id)
        
        # Validate photo items
        photo_hothashes = [
            item['photo_hothash']
            for item in request.items
            if item.get('type') == 'photo'
        ]
        
        if photo_hothashes:
            valid_hothashes = self._validate_user_photos(user_id, photo_hothashes)
            if len(valid_hothashes) < len(photo_hothashes):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some photos not found or don't belong to user"
                )
        
        # Add visible=true to all new items (default visibility)
        items_with_visibility = []
        for item in request.items:
            item_copy = dict(item)
            if "visible" not in item_copy:
                item_copy["visible"] = True
            items_with_visibility.append(item_copy)
        
        # Add items
        added_count = self.collection_repo.add_items(collection, items_with_visibility)
        
        # Refresh
        self.db.refresh(collection)
        
        return PhotoManagementResponse(
            collection_id=collection.id,
            item_count=collection.item_count,
            photo_count=collection.photo_count,
            affected_count=added_count,
            cover_photo_hothash=collection.cover_photo_hothash
        )
    
    def reorder_items(
        self,
        collection_id: int,
        user_id: int,
        request: ReorderItemsRequest
    ) -> PhotoManagementResponse:
        """
        Reorder all items in collection.
        Validates photos exist and belong to user.
        """
        collection = self._get_collection_or_404(collection_id, user_id)
        
        # Validate photo items
        photo_hothashes = [
            item['photo_hothash']
            for item in request.items
            if item.get('type') == 'photo'
        ]
        
        if photo_hothashes:
            valid_hothashes = self._validate_user_photos(user_id, photo_hothashes)
            if len(valid_hothashes) < len(photo_hothashes):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some photos not found or don't belong to user"
                )
        
        # Reorder items
        self.collection_repo.reorder_items(collection, request.items)
        
        # Refresh
        self.db.refresh(collection)
        
        return PhotoManagementResponse(
            collection_id=collection.id,
            item_count=collection.item_count,
            photo_count=collection.photo_count,
            affected_count=len(request.items),
            cover_photo_hothash=collection.cover_photo_hothash
        )
    
    def delete_item_at_position(
        self,
        collection_id: int,
        user_id: int,
        position: int
    ) -> PhotoManagementResponse:
        """Delete item at specific position"""
        collection = self._get_collection_or_404(collection_id, user_id)
        
        success = self.collection_repo.remove_item_at_position(collection, position)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid position: {position}"
            )
        
        # Refresh
        self.db.refresh(collection)
        
        return PhotoManagementResponse(
            collection_id=collection.id,
            item_count=collection.item_count,
            photo_count=collection.photo_count,
            affected_count=1,
            cover_photo_hothash=collection.cover_photo_hothash
        )
    
    def update_text_card(
        self,
        collection_id: int,
        user_id: int,
        position: int,
        request: UpdateTextCardRequest
    ) -> PhotoManagementResponse:
        """Update text card content at position"""
        collection = self._get_collection_or_404(collection_id, user_id)
        
        success = self.collection_repo.update_text_card(
            collection,
            position,
            request.title,
            request.body
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Position {position} is not a text card or is invalid"
            )
        
        # Refresh
        self.db.refresh(collection)
        
        return PhotoManagementResponse(
            collection_id=collection.id,
            item_count=collection.item_count,
            photo_count=collection.photo_count,
            affected_count=1,
            cover_photo_hothash=collection.cover_photo_hothash
        )
# Service methods

    def insert_items_at_position(
        self,
        collection_id: int,
        user_id: int,
        request: InsertItemsRequest
    ) -> PhotoManagementResponse:
        """Insert items at specific position (atomic operation)"""
        collection = self._get_collection_or_404(collection_id, user_id)
        
        if request.position < 0 or request.position > len(collection.items or []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid position: {request.position}. Must be 0 to {len(collection.items or [])}"
            )
        
        photo_hothashes = [
            item['photo_hothash']
            for item in request.items
            if item.get('type') == 'photo'
        ]
        
        if photo_hothashes:
            valid_hothashes = self._validate_user_photos(user_id, photo_hothashes)
            if len(valid_hothashes) < len(photo_hothashes):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Some photos not found or don't belong to user"
                )
        
        # Add visible=true to all new items (default visibility)
        items_with_visibility = []
        for item in request.items:
            item_copy = dict(item)
            if "visible" not in item_copy:
                item_copy["visible"] = True
            items_with_visibility.append(item_copy)
        
        success, affected_positions = collection.insert_items_at_position(request.position, items_with_visibility)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to insert items at position {request.position}"
            )
        
        self.db.commit()
        self.db.refresh(collection)
        
        return PhotoManagementResponse(
            collection_id=collection.id,
            item_count=collection.item_count,
            photo_count=collection.photo_count,
            affected_count=len(affected_positions),
            cover_photo_hothash=collection.cover_photo_hothash
        )
    
    def move_items(
        self,
        collection_id: int,
        user_id: int,
        request: MoveItemsRequest
    ) -> PhotoManagementResponse:
        """Move items from one position to another (atomic operation)"""
        collection = self._get_collection_or_404(collection_id, user_id)
        
        items_count = len(collection.items or [])
        
        if request.from_position < 0 or request.from_position + request.count > items_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid from_position/count: {request.from_position}/{request.count}"
            )
        
        if request.to_position < 0 or request.to_position > items_count - request.count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid to_position: {request.to_position}"
            )
        
        success, affected_range = collection.move_items(
            request.from_position,
            request.count,
            request.to_position
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to move items"
            )
        
        self.db.commit()
        self.db.refresh(collection)
        
        return PhotoManagementResponse(
            collection_id=collection.id,
            item_count=collection.item_count,
            photo_count=collection.photo_count,
            affected_count=request.count,
            cover_photo_hothash=collection.cover_photo_hothash
        )
    
    def delete_items_at_position(
        self,
        collection_id: int,
        user_id: int,
        request: DeleteItemsRequest
    ) -> PhotoManagementResponse:
        """Delete items at specific position (atomic operation)"""
        collection = self._get_collection_or_404(collection_id, user_id)
        
        items_count = len(collection.items or [])
        
        if request.position < 0 or request.position + request.count > items_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid position/count: {request.position}/{request.count}"
            )
        
        success = collection.delete_items_at_position(request.position, request.count)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete items"
            )
        
        self.db.commit()
        self.db.refresh(collection)
        
        return PhotoManagementResponse(
            collection_id=collection.id,
            item_count=collection.item_count,
            photo_count=collection.photo_count,
            affected_count=request.count,
            cover_photo_hothash=collection.cover_photo_hothash
        )
    
    def toggle_item_visibility(
        self,
        collection_id: int,
        user_id: int,
        position: int,
        visible: bool
    ) -> dict:
        """Toggle visibility of item at specific position"""
        from datetime import datetime
        from sqlalchemy.orm.attributes import flag_modified
        
        collection = self._get_collection_or_404(collection_id, user_id)
        
        items = collection.items or []
        if position < 0 or position >= len(items):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid position: {position}. Must be 0 to {len(items)-1}"
            )
        
        # Update visibility
        items = list(items)  # Make mutable copy
        items[position]["visible"] = visible
        
        # Save to database
        collection.items = items
        collection.updated_at = datetime.utcnow()
        flag_modified(collection, "items")
        self.db.commit()
        self.db.refresh(collection)
        
        # Count visible items
        visible_count = sum(1 for item in items if item.get("visible", True))
        
        return {
            "collection_id": collection_id,
            "position": position,
            "visible": visible,
            "item_count": len(items),
            "visible_count": visible_count
        }
