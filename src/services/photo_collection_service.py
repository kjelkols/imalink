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
    AddPhotosRequest,
    RemovePhotosRequest,
    ReorderPhotosRequest,
    AddItemsRequest,
    ReorderItemsRequest,
    UpdateTextCardRequest,
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
        collection = self._get_collection_or_404(collection_id, user_id)
        return PhotoCollectionResponse.model_validate(collection)
    
    def list_collections(self, user_id: int, skip: int = 0, limit: int = 100) -> CollectionListResponse:
        """List all collections for user"""
        collections = self.collection_repo.get_all_for_user(user_id, skip, limit)
        total = self.collection_repo.count_for_user(user_id)
        
        return CollectionListResponse(
            collections=[PhotoCollectionResponse.model_validate(c) for c in collections],
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
    
    # Photo management operations
    
    def add_photos(
        self, 
        collection_id: int, 
        user_id: int, 
        request: AddPhotosRequest
    ) -> PhotoManagementResponse:
        """
        Add photos to collection.
        Validates photos exist and belong to user.
        """
        collection = self._get_collection_or_404(collection_id, user_id)
        
        # Validate photos
        valid_hothashes = self._validate_user_photos(user_id, request.hothashes)
        if len(valid_hothashes) < len(request.hothashes):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Some photos not found or don't belong to user"
            )
        
        # Add photos
        added_count = self.collection_repo.add_photos(collection, list(valid_hothashes))
        
        # Refresh to get updated data
        self.db.refresh(collection)
        
        return PhotoManagementResponse(
            collection_id=collection.id,
            item_count=collection.item_count,
            photo_count=collection.photo_count,
            affected_count=added_count,
            cover_photo_hothash=collection.cover_photo_hothash
        )
    
    def remove_photos(
        self, 
        collection_id: int, 
        user_id: int, 
        request: RemovePhotosRequest
    ) -> PhotoManagementResponse:
        """Remove photos from collection"""
        collection = self._get_collection_or_404(collection_id, user_id)
        
        # Remove photos
        removed_count = self.collection_repo.remove_photos(collection, request.hothashes)
        
        # Refresh to get updated data
        self.db.refresh(collection)
        
        return PhotoManagementResponse(
            collection_id=collection.id,
            item_count=collection.item_count,
            photo_count=collection.photo_count,
            affected_count=removed_count,
            cover_photo_hothash=collection.cover_photo_hothash
        )
    
    def reorder_photos(
        self, 
        collection_id: int, 
        user_id: int, 
        request: ReorderPhotosRequest
    ) -> PhotoManagementResponse:
        """
        Reorder photos in collection.
        New list must contain exactly the same hothashes.
        """
        collection = self._get_collection_or_404(collection_id, user_id)
        
        # Reorder photos
        success = self.collection_repo.reorder_photos(collection, request.hothashes)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provided hothashes don't match collection contents"
            )
        
        # Refresh to get updated data
        self.db.refresh(collection)
        
        return PhotoManagementResponse(
            collection_id=collection.id,
            item_count=collection.item_count,
            photo_count=collection.photo_count,
            affected_count=len(request.hothashes),
            cover_photo_hothash=collection.cover_photo_hothash
        )
    
    def get_collection_photos(
        self, 
        collection_id: int, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Photo]:
        """
        Get actual Photo objects for collection.
        Returns photos in collection order.
        """
        collection = self._get_collection_or_404(collection_id, user_id)
        
        if not collection.hothashes:
            return []
        
        # Get subset of hothashes based on pagination
        paginated_hothashes = collection.hothashes[skip:skip + limit]
        
        # Fetch photos
        photos = self.photo_repo.get_by_hothashes(paginated_hothashes, user_id)
        
        # Sort by collection order
        hothash_to_photo = {p.hothash: p for p in photos}
        ordered_photos = [
            hothash_to_photo[h] 
            for h in paginated_hothashes 
            if h in hothash_to_photo
        ]
        
        return ordered_photos
    
    def cleanup_collection(self, collection_id: int, user_id: int) -> int:
        """
        Remove invalid hothashes from collection.
        Returns number of invalid hothashes removed.
        """
        collection = self._get_collection_or_404(collection_id, user_id)
        
        if not collection.hothashes:
            return 0
        
        # Get valid hothashes
        valid_hothashes = self._validate_user_photos(user_id, collection.hothashes)
        
        # Cleanup
        removed_count = self.collection_repo.cleanup_invalid_hothashes(
            collection, 
            valid_hothashes
        )
        
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
        
        # Add items
        added_count = self.collection_repo.add_items(collection, request.items)
        
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
