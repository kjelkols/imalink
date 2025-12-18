"""
Photo Collections API endpoints
"""
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.database.connection import get_db
from src.models.user import User
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
from src.schemas.photo_schemas import PhotoResponse
from src.schemas.common import PaginatedResponse
from src.services.photo_collection_service import PhotoCollectionService


router = APIRouter(prefix="/collections", tags=["Photo Collections"])


# CRUD endpoints

@router.post(
    "",
    response_model=PhotoCollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new photo collection"
)
def create_collection(
    collection_data: PhotoCollectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create new photo collection.
    
    - **name**: Collection name (required, 1-255 chars)
    - **description**: Optional description
    - **hothashes**: Optional initial photos (must exist and belong to user)
    """
    service = PhotoCollectionService(db)
    return service.create_collection(current_user.id, collection_data)


@router.get(
    "",
    response_model=CollectionListResponse,
    summary="List all collections"
)
def list_collections(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all photo collections for current user.
    
    - **skip**: Number of collections to skip (pagination)
    - **limit**: Maximum collections to return (max 100)
    """
    service = PhotoCollectionService(db)
    return service.list_collections(current_user.id, skip, limit)


@router.get(
    "/{collection_id}",
    response_model=PhotoCollectionResponse,
    summary="Get collection by ID"
)
def get_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific collection by ID"""
    service = PhotoCollectionService(db)
    return service.get_collection(collection_id, current_user.id)


@router.patch(
    "/{collection_id}",
    response_model=PhotoCollectionResponse,
    summary="Update collection metadata"
)
def update_collection(
    collection_id: int,
    update_data: PhotoCollectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update collection name and/or description.
    Does not affect photos in collection.
    
    - **name**: New name (optional)
    - **description**: New description (optional)
    """
    service = PhotoCollectionService(db)
    return service.update_collection(collection_id, current_user.id, update_data)


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete collection"
)
def delete_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete collection permanently.
    Photos themselves are not deleted, only the collection.
    """
    service = PhotoCollectionService(db)
    service.delete_collection(collection_id, current_user.id)


# Photo management endpoints

@router.post(
    "/{collection_id}/photos",
    response_model=PhotoManagementResponse,
    summary="Add photos to collection"
)
def add_photos_to_collection(
    collection_id: int,
    request: AddPhotosRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add photos to collection (appends to end).
    
    - **hothashes**: List of photo hothashes to add
    
    Duplicates are automatically skipped.
    Photos must exist and belong to user.
    """
    service = PhotoCollectionService(db)
    return service.add_photos(collection_id, current_user.id, request)


@router.delete(
    "/{collection_id}/photos",
    response_model=PhotoManagementResponse,
    summary="Remove photos from collection"
)
def remove_photos_from_collection(
    collection_id: int,
    request: RemovePhotosRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove photos from collection.
    
    - **hothashes**: List of photo hothashes to remove
    """
    service = PhotoCollectionService(db)
    return service.remove_photos(collection_id, current_user.id, request)


@router.put(
    "/{collection_id}/photos/reorder",
    response_model=PhotoManagementResponse,
    summary="Reorder photos in collection (backward compatibility)"
)
def reorder_collection_photos(
    collection_id: int,
    request: ReorderPhotosRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reorder photos in collection (legacy endpoint - photos only).
    
    **Deprecated**: Use PUT /collections/{id}/items/reorder for mixed content support.
    
    - **hothashes**: Complete list of hothashes in new order
    
    Must contain exactly the same hothashes as current collection,
    just in different order. First photo becomes cover photo.
    """
    service = PhotoCollectionService(db)
    return service.reorder_photos(collection_id, current_user.id, request)


# NEW: Item management endpoints (photos + text cards)

@router.post(
    "/{collection_id}/items",
    response_model=PhotoManagementResponse,
    summary="Add items to collection"
)
def add_items_to_collection(
    collection_id: int,
    request: AddItemsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add items (photos and/or text cards) to collection.
    
    Items are appended to end of collection. Duplicate photos are skipped.
    
    **Item types:**
    - Photo: `{"type": "photo", "photo_hothash": "abc123..."}`
    - Text card: `{"type": "text", "text_card": {"title": "...", "body": "..."}}`
    
    **Note:** Position is implicit from array index (no position field needed).
    
    **Validation:**
    - Text card title: max 200 characters
    - Text card body: max 2000 characters (plain text)
    - Photos must exist and belong to user
    """
    service = PhotoCollectionService(db)
    return service.add_items(collection_id, current_user.id, request)


@router.put(
    "/{collection_id}/items/reorder",
    response_model=PhotoManagementResponse,
    summary="Reorder all items in collection"
)
def reorder_collection_items(
    collection_id: int,
    request: ReorderItemsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reorder all items in collection (photos + text cards).
    
    Replaces entire items array with new order. Use for drag-and-drop reordering.
    
    **Important:** Must include ALL items you want to keep. Items not in list are removed.
    """
    service = PhotoCollectionService(db)
    return service.reorder_items(collection_id, current_user.id, request)


@router.delete(
    "/{collection_id}/items/{position}",
    response_model=PhotoManagementResponse,
    summary="Delete item at position"
)
def delete_collection_item(
    collection_id: int,
    position: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete item (photo or text card) at specific position (array index, 0-based).
    
    Remaining items shift down automatically (no gaps in array).
    """
    service = PhotoCollectionService(db)
    return service.delete_item_at_position(collection_id, current_user.id, position)


@router.patch(
    "/{collection_id}/items/{position}",
    response_model=PhotoManagementResponse,
    summary="Update text card content"
)
def update_text_card(
    collection_id: int,
    position: int,
    request: UpdateTextCardRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update text card content at position.
    
    Only works for text cards (returns 400 if position is a photo).
    Provide title and/or body to update.
    """
    service = PhotoCollectionService(db)
    return service.update_text_card(collection_id, current_user.id, position, request)


@router.get(
    "/{collection_id}/photos",
    response_model=PaginatedResponse[PhotoResponse],
    summary="Get photos in collection"
)
def get_collection_photos(
    collection_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get actual Photo objects in collection.
    
    - **skip**: Number of photos to skip
    - **limit**: Maximum photos to return
    
    Returns photos in collection order with total count.
    """
    service = PhotoCollectionService(db)
    photos = service.get_collection_photos(
        collection_id, 
        current_user.id, 
        skip, 
        limit
    )
    
    # Get total count from collection
    collection = service.get_collection(collection_id, current_user.id)
    total = len(collection.hothashes) if collection.hothashes else 0
    
    return PaginatedResponse(
        data=[PhotoResponse.model_validate(p) for p in photos],
        total=total,
        offset=skip,
        limit=limit
    )


@router.post(
    "/{collection_id}/cleanup",
    response_model=dict,
    summary="Clean up invalid photos"
)
def cleanup_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove photos that no longer exist in database.
    
    Returns number of invalid photos removed.
    """
    service = PhotoCollectionService(db)
    removed_count = service.cleanup_collection(collection_id, current_user.id)
    return {
        "collection_id": collection_id,
        "removed_count": removed_count
    }
