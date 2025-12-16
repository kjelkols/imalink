"""
Photo Search API endpoints
Handles both ad-hoc searches and saved search CRUD operations
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
import logging

from src.services.photo_search_service import PhotoSearchService
from src.schemas.photo_search_schemas import (
    SavedPhotoSearchCreate, SavedPhotoSearchUpdate, SavedPhotoSearchResponse,
    SavedPhotoSearchListResponse
)
from src.schemas.photo_schemas import PhotoSearchRequest, PhotoResponse
from src.schemas.common import PaginatedResponse, create_success_response
from src.core.exceptions import NotFoundError, ValidationError
from src.api.dependencies import get_current_user
from src.models.user import User
from src.database.connection import get_db
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)


def get_photo_search_service(db: Session = Depends(get_db)) -> PhotoSearchService:
    """Dependency to get PhotoSearchService"""
    return PhotoSearchService(db)


# =============================================================================
# AD-HOC SEARCH
# =============================================================================

@router.post("/ad-hoc", response_model=PaginatedResponse[PhotoResponse])
def search_photos_adhoc(
    search_request: PhotoSearchRequest,
    current_user: User = Depends(get_current_user),
    service: PhotoSearchService = Depends(get_photo_search_service)
):
    """
    Execute an ad-hoc photo search without saving it
    
    This is the primary search endpoint - send PhotoSearchRequest and get results.
    Use this for one-time searches or before deciding to save a search.
    """
    try:
        return service.execute_adhoc_search(search_request, current_user.id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ad-hoc search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# =============================================================================
# SAVED SEARCHES - CRUD
# =============================================================================

@router.post("/", response_model=SavedPhotoSearchResponse, status_code=status.HTTP_201_CREATED)
def create_saved_search(
    data: SavedPhotoSearchCreate,
    current_user: User = Depends(get_current_user),
    service: PhotoSearchService = Depends(get_photo_search_service)
):
    """
    Create a new saved photo search
    
    Save a search for later reuse. The search_criteria should be a valid
    PhotoSearchRequest as a dict.
    """
    try:
        return service.create_saved_search(data, current_user.id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create saved search: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create saved search: {str(e)}")


@router.get("/", response_model=SavedPhotoSearchListResponse)
def list_saved_searches(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
    favorites_only: bool = Query(False, description="Show only favorite searches"),
    current_user: User = Depends(get_current_user),
    service: PhotoSearchService = Depends(get_photo_search_service)
):
    """List all saved searches for the current user"""
    try:
        return service.list_saved_searches(
            user_id=current_user.id,
            offset=offset,
            limit=limit,
            favorites_only=favorites_only
        )
    except Exception as e:
        logger.error(f"Failed to list saved searches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list saved searches: {str(e)}")


@router.get("/{search_id}", response_model=SavedPhotoSearchResponse)
def get_saved_search(
    search_id: int,
    current_user: User = Depends(get_current_user),
    service: PhotoSearchService = Depends(get_photo_search_service)
):
    """Get a specific saved search by ID"""
    try:
        return service.get_saved_search(search_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get saved search {search_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get saved search: {str(e)}")


@router.put("/{search_id}", response_model=SavedPhotoSearchResponse)
def update_saved_search(
    search_id: int,
    data: SavedPhotoSearchUpdate,
    current_user: User = Depends(get_current_user),
    service: PhotoSearchService = Depends(get_photo_search_service)
):
    """Update a saved search"""
    try:
        return service.update_saved_search(search_id, data, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update saved search {search_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update saved search: {str(e)}")


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_search(
    search_id: int,
    current_user: User = Depends(get_current_user),
    service: PhotoSearchService = Depends(get_photo_search_service)
):
    """Delete a saved search"""
    try:
        service.delete_saved_search(search_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete saved search {search_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete saved search: {str(e)}")


# =============================================================================
# EXECUTE SAVED SEARCH
# =============================================================================

@router.post("/{search_id}/execute", response_model=PaginatedResponse[PhotoResponse])
def execute_saved_search(
    search_id: int,
    override_offset: Optional[int] = Query(None, ge=0, description="Override pagination offset"),
    override_limit: Optional[int] = Query(None, ge=1, le=5000, description="Override pagination limit"),
    current_user: User = Depends(get_current_user),
    service: PhotoSearchService = Depends(get_photo_search_service)
):
    """
    Execute a saved search and return photo results
    
    This will run the saved search criteria and return matching photos.
    Updates the last_executed timestamp and result_count for the saved search.
    
    You can override the pagination parameters without modifying the saved search.
    """
    try:
        return service.execute_saved_search(
            search_id=search_id,
            user_id=current_user.id,
            override_offset=override_offset,
            override_limit=override_limit
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute saved search {search_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute search: {str(e)}")
