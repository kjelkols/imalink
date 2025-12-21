"""
Photo Collections API endpoints
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.database.connection import get_db
from src.models.user import User
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
    ToggleVisibilityRequest,
    ToggleVisibilityResponse,
    UpdateCaptionRequest,
    UpdateCaptionResponse,
    PhotoManagementResponse,
    CollectionListResponse
)
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


# Item management endpoints (photos + text cards)

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


@router.post(
    "/{collection_id}/items/insert",
    response_model=PhotoManagementResponse,
    summary="Insert items at specific position"
)
def insert_items_at_position(
    collection_id: int,
    request: InsertItemsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Insert items at specific position (atomic operation).
    
    - **position**: 0 to len(items) (inclusive) - 0 = insert first, len(items) = append
    - **items**: Array of items to insert (photos and/or text cards)
    
    Items are inserted BEFORE the current item at position.
    Existing items from position onwards are shifted up.
    """
    service = PhotoCollectionService(db)
    return service.insert_items_at_position(collection_id, current_user.id, request)


@router.post(
    "/{collection_id}/items/move",
    response_model=PhotoManagementResponse,
    summary="Move items from one position to another"
)
def move_items(
    collection_id: int,
    request: MoveItemsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Move items from one position to another (atomic operation).
    
    - **from_position**: Start position to move from
    - **count**: Number of items to move
    - **to_position**: Target position to move to
    
    Items are removed from from_position and inserted at to_position.
    """
    service = PhotoCollectionService(db)
    return service.move_items(collection_id, current_user.id, request)


@router.post(
    "/{collection_id}/items/delete",
    response_model=PhotoManagementResponse,
    summary="Delete items at specific position"
)
def delete_items_at_position(
    collection_id: int,
    request: DeleteItemsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete items at specific position (atomic operation).
    
    - **position**: Start position to delete from
    - **count**: Number of items to delete
    
    Items from position to position+count-1 are deleted.
    Remaining items are shifted down.
    """
    service = PhotoCollectionService(db)
    return service.delete_items_at_position(collection_id, current_user.id, request)


@router.patch(
    "/{collection_id}/items/{position}/visibility",
    response_model=ToggleVisibilityResponse,
    summary="Toggle visibility of item at position"
)
def toggle_item_visibility(
    collection_id: int,
    position: int,
    request: ToggleVisibilityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Toggle visibility of item at specific position.
    
    - **position**: Index of item to toggle (0-based)
    - **visible**: True to show, False to hide
    
    Hidden items are preserved in collection but filtered in slideshow view.
    Returns total item count and visible item count.
    """
    service = PhotoCollectionService(db)
    return service.toggle_item_visibility(collection_id, current_user.id, position, request.visible)


@router.patch(
    "/{collection_id}/items/{position}/caption",
    response_model=UpdateCaptionResponse,
    summary="Update caption of photo item"
)
def update_item_caption(
    collection_id: int,
    position: int,
    request: UpdateCaptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update caption text for photo item at specific position.
    
    - **position**: Index of photo item (0-based)
    - **caption**: Caption text (max 1000 chars, null to remove)
    
    Captions are collection-specific. Same photo can have different captions
    in different collections. Only photo items can have captions (not text cards).
    """
    service = PhotoCollectionService(db)
    return service.update_item_caption(collection_id, current_user.id, position, request.caption)
