"""
API endpoints for photo operations using Service Layer

ARCHITECTURAL NOTE (UPDATED):
Photos are created via POST /photos/create which receives pre-processed PhotoCreateSchema from imalink-core.
PhotoCreateSchema contains hotpreview (base64), metadata, and exif_dict - backend stores this data.
This ensures:
- Photo-centric API (100% of operations through /photos)
- Backend NEVER processes images - only stores metadata from PhotoCreateSchema
- Photo.hothash is derived from hotpreview (SHA256, content-based)
- JPEG/RAW pairs automatically share the same Photo (same hotpreview = same hash)

This API provides:
- CREATE: Upload photos via PhotoCreateSchema (POST /create)
- READ: List, search, and retrieve photo metadata
- UPDATE: Edit photo metadata (rating, visibility, tags, category, author)
- DELETE: Remove photo and all associated image files (cascade)
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Response, Query, File, UploadFile, Body
from fastapi.responses import StreamingResponse
import io
import logging
import httpx

from src.core.dependencies import get_photo_service, get_photo_stack_service
from src.services.photo_service import PhotoService
from src.services.photo_stack_service import PhotoStackService
from src.schemas.photo_schemas import (
    PhotoResponse, PhotoCreateRequest, PhotoUpdateRequest, 
    PhotoSearchRequest, TimeLocCorrectionRequest, ViewCorrectionRequest
)
from imalink_schemas import PhotoCreateSchema, ImageFileCreateSchema
from src.schemas.photo_create_schemas import PhotoCreateRequest as PhotoCreateReq, PhotoCreateResponse
from src.schemas.image_file_upload_schemas import (
    ImageFileNewPhotoRequest, ImageFileAddToPhotoRequest, ImageFileUploadResponse
)
from src.schemas.image_file_schemas import ImageFileResponse
from src.schemas.tag_schemas import AddTagsRequest, AddTagsResponse, RemoveTagResponse
from src.schemas.common import PaginatedResponse, create_success_response
from src.schemas.responses.photo_stack_responses import PhotoStackSummary
from src.core.exceptions import NotFoundError, ValidationError, DuplicateImageError
from src.api.dependencies import get_current_active_user, get_optional_current_user
from src.models.user import User
from pydantic import ValidationError as PydanticValidationError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=PaginatedResponse[PhotoResponse])
def list_photos(
    offset: int = Query(0, ge=0, description="Number of photos to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of photos to return"),
    author_id: Optional[int] = Query(None, description="Filter by author ID"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """Get paginated list of photos with metadata (supports anonymous access to public photos)"""
    try:
        user_id = getattr(current_user, 'id', None) if current_user else None
        return photo_service.get_photos(
            user_id=user_id,
            offset=offset,
            limit=limit,
            author_id=author_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve photos: {str(e)}")


@router.post("/search", response_model=PaginatedResponse[PhotoResponse])
def search_photos(
    search_request: PhotoSearchRequest,
    current_user: User = Depends(get_current_active_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """
    Search photos with advanced filtering (user-scoped)
    
    DEPRECATED: This endpoint is maintained for backwards compatibility.
    New code should use POST /api/v1/photo-searches/ad-hoc instead.
    
    This endpoint will be removed in a future version.
    """
    try:
        # Delegate to PhotoSearchService for consistency
        from src.services.photo_search_service import PhotoSearchService
        search_service = PhotoSearchService(photo_service.db)
        return search_service.execute_adhoc_search(search_request, getattr(current_user, 'id'))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search photos: {str(e)}")


# NOTE: /new-photo endpoint REMOVED - use POST /create instead
# PhotoCreateSchema endpoint is the single unified way to create photos


@router.get("/{hothash}/files", response_model=List[ImageFileResponse])
def get_photo_files(
    hothash: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """
    Get list of ImageFiles for a photo
    
    Returns all files associated with this photo (JPEG, RAW, etc.)
    """
    try:
        user_id = getattr(current_user, 'id', None) if current_user else None
        return photo_service.get_photo_files(hothash, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get photo files: {str(e)}")


@router.get("/{hothash}", response_model=PhotoResponse)
def get_photo(
    hothash: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """Get single photo by hash (supports anonymous access for public photos)"""
    try:
        user_id = getattr(current_user, 'id', None) if current_user else None
        return photo_service.get_photo_by_hash(hothash, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve photo: {str(e)}")


@router.put("/{hothash}", response_model=PhotoResponse)
def update_photo(
    hothash: str,
    photo_data: PhotoUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """Update existing photo (user-scoped)"""
    try:
        return photo_service.update_photo(hothash, photo_data, getattr(current_user, 'id'))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update photo: {str(e)}")


@router.delete("/{hothash}")
def delete_photo(
    hothash: str,
    current_user: User = Depends(get_current_active_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """Delete photo and all associated image files (user-scoped)"""
    try:
        photo_service.delete_photo(hothash, getattr(current_user, 'id'))
        return create_success_response(message="Photo deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete photo: {str(e)}")


@router.get("/{hothash}/hotpreview")
def get_hotpreview(
    hothash: str,
    photo_service: PhotoService = Depends(get_photo_service)
):
    """Get hotpreview image for photo"""
    try:
        hotpreview_data = photo_service.get_hotpreview(hothash)
        
        # Return as streaming response
        if hotpreview_data:
            return StreamingResponse(
                io.BytesIO(hotpreview_data),
                media_type="image/jpeg",
                headers={
                    "Content-Disposition": f"inline; filename=hotpreview_{hothash[:8]}.jpg",
                    "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
                }
            )
        else:
            raise HTTPException(status_code=404, detail="Hotpreview not found")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve hotpreview: {str(e)}")


@router.put("/{hothash}/coldpreview")
def upload_coldpreview(
    hothash: str,
    file: UploadFile = File(..., description="Coldpreview image file"),
    photo_service: PhotoService = Depends(get_photo_service),
    current_user: User = Depends(get_current_active_user)
):
    """Upload or update coldpreview for photo"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file content (sync)
        file_content = file.file.read()
        
        # Validate that content is not empty
        if not file_content:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Validate that it's a valid image by trying to open it
        from PIL import Image as PILImage
        import io
        try:
            test_img = PILImage.open(io.BytesIO(file_content))
            test_img.verify()  # Check if it's a valid image
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
        
        result = photo_service.upload_coldpreview(hothash, file_content, current_user.id)
        return create_success_response(
            message="Coldpreview uploaded successfully",
            data=result
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload coldpreview: {str(e)}")


@router.get("/{hothash}/coldpreview")
def get_coldpreview(
    hothash: str,
    width: Optional[int] = Query(None, ge=100, le=2000, description="Target width for dynamic resizing"),
    height: Optional[int] = Query(None, ge=100, le=2000, description="Target height for dynamic resizing"),
    photo_service: PhotoService = Depends(get_photo_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get coldpreview image for photo with optional resizing"""
    try:
        coldpreview_data = photo_service.get_coldpreview(hothash, current_user.id, width=width, height=height)
        
        if coldpreview_data:
            return StreamingResponse(
                io.BytesIO(coldpreview_data),
                media_type="image/jpeg",
                headers={
                    "Content-Disposition": f"inline; filename=coldpreview_{hothash[:8]}.jpg",
                    "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
                }
            )
        else:
            # Coldpreview not generated yet - return 404
            raise HTTPException(status_code=404, detail="Coldpreview not available")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions as-is (including our 404 above)
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving coldpreview for {hothash}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve coldpreview: {str(e)}")


@router.delete("/{hothash}/coldpreview")
def delete_coldpreview(
    hothash: str,
    photo_service: PhotoService = Depends(get_photo_service),
    current_user: User = Depends(get_current_active_user)
):
    """Delete coldpreview for photo"""
    try:
        photo_service.delete_coldpreview(hothash, current_user.id)
        return create_success_response(message="Coldpreview deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete coldpreview: {str(e)}")


# ===== PHOTO CORRECTIONS ENDPOINTS =====

@router.patch("/{hothash}/timeloc-correction", response_model=PhotoResponse)
def update_timeloc_correction(
    hothash: str,
    correction: Optional[TimeLocCorrectionRequest] = None,
    current_user: User = Depends(get_current_active_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """
    Apply non-destructive time/location correction to photo
    
    - Send correction data to override EXIF values
    - Send `null` to restore original EXIF values
    - Original EXIF data in Photo.exif_dict is never modified
    """
    try:
        updated_photo = photo_service.update_timeloc_correction(
            hothash=hothash,
            correction=correction,
            user_id=getattr(current_user, 'id')
        )
        return updated_photo
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update timeloc correction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update time/location correction: {str(e)}")


@router.patch("/{hothash}/view-correction", response_model=PhotoResponse)
def update_view_correction(
    hothash: str,
    correction: Optional[ViewCorrectionRequest] = None,
    current_user: User = Depends(get_current_active_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """
    Update view correction settings (frontend rendering hints only)
    
    - Send correction data to set rotation, crop, exposure adjustments
    - Send `null` to remove all view corrections
    - Backend only stores metadata - no image processing
    """
    try:
        updated_photo = photo_service.update_view_correction(
            hothash=hothash,
            correction=correction,
            user_id=getattr(current_user, 'id')
        )
        return updated_photo
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update view correction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update view correction: {str(e)}")


@router.put("/{hothash}/event", response_model=PhotoResponse)
def set_photo_event(
    hothash: str,
    event_id: Optional[int] = Body(None, description="Event ID (null to unset)"),
    current_user: User = Depends(get_current_active_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """
    Set or unset photo's event
    
    - Send event_id to assign photo to event
    - Send null to remove photo from event
    - Each photo can belong to at most ONE event (one-to-many)
    - For many-to-many relationships, use Collections or Tags
    """
    try:
        updated_photo = photo_service.set_event(
            hothash=hothash,
            event_id=event_id,
            user_id=getattr(current_user, 'id')
        )
        return updated_photo
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to set event: {str(e)}")


# Photo Tags Endpoints

@router.post("/{hothash}/tags", response_model=AddTagsResponse)
def add_tags_to_photo(
    hothash: str,
    request: AddTagsRequest,
    current_user: User = Depends(get_current_active_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """
    Add one or more tags to a photo.
    
    Tags are created automatically if they don't exist.
    Duplicate tags are silently skipped.
    
    **Request body:**
    ```json
    {
        "tags": ["landscape", "sunset", "norway"]
    }
    ```
    """
    from services.tag_service import TagService
    
    try:
        tag_service = TagService(photo_service.db)
        return tag_service.add_tags_to_photo(
            hothash=hothash,
            tag_names=request.tags,
            user_id=getattr(current_user, 'id')
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add tags to photo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add tags: {str(e)}")


@router.delete("/{hothash}/tags/{tag_name}", response_model=RemoveTagResponse)
def remove_tag_from_photo(
    hothash: str,
    tag_name: str,
    current_user: User = Depends(get_current_active_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """
    Remove a specific tag from a photo.
    
    The tag itself remains in the database for reuse.
    Returns 404 if photo or tag not found.
    """
    from services.tag_service import TagService
    
    try:
        tag_service = TagService(photo_service.db)
        return tag_service.remove_tag_from_photo(
            hothash=hothash,
            tag_name=tag_name,
            user_id=getattr(current_user, 'id')
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to remove tag from photo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove tag: {str(e)}")


# Additional utility endpoints

@router.get("/{hothash}/stack", response_model=Optional[PhotoStackSummary])
def get_photo_stack(
    hothash: str,
    current_user: User = Depends(get_current_active_user),
    photo_stack_service: PhotoStackService = Depends(get_photo_stack_service)
):
    """
    Get the stack containing this photo.
    
    Returns the stack if photo belongs to one, null otherwise.
    With one-to-many relationship, each photo can belong to at most one stack.
    """
    try:
        stack = photo_stack_service.get_photo_stack(
            photo_hothash=hothash,
            user_id=getattr(current_user, 'id')
        )
        
        return stack
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stack for photo: {str(e)}")


@router.post("/create", response_model=PhotoCreateResponse, status_code=201)
def create_photo(
    request: PhotoCreateReq,
    current_user: User = Depends(get_current_active_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """
    Create Photo from PhotoCreateSchema (New Architecture)
    
    PhotoCreateSchema is the complete JSON package from imalink-core server containing
    all image processing results. Frontend sends image to imalink-core server,
    receives PhotoCreateSchema, then sends it here with user organization metadata.
    
    Flow:
    1. Frontend → imalink-core server (POST /process) → PhotoCreateSchema
    2. Frontend → Backend (POST /photos/create) → Photo created
    
    This replaces the old POST /photos endpoint which did image processing.
    Backend now only stores metadata and previews from PhotoCreateSchema.
    """
    try:
        photo = photo_service.create_photo_from_photo_create_schema(
            photo_create_request=request,
            user_id=getattr(current_user, 'id')
        )
        
        return PhotoCreateResponse(
            id=photo.id,
            user_id=photo.user_id,
            hothash=photo.hothash,
            rating=photo.rating,
            visibility=photo.visibility,
            width=photo.width,
            height=photo.height,
            taken_at=photo.taken_at,
            created_at=photo.created_at,
            is_duplicate=False  # Will be set by service if hothash existed
        )
        
    except DuplicateImageError as e:
        # Photo with this hothash already exists - return existing
        existing_photo = photo_service.get_photo_by_hothash(
            hothash=request.photo_create_schema.hothash,
            user_id=getattr(current_user, 'id')
        )
        return PhotoCreateResponse(
            id=existing_photo.id,
            user_id=existing_photo.user_id,
            hothash=existing_photo.hothash,
            rating=existing_photo.rating,
            visibility=existing_photo.visibility,
            width=existing_photo.width,
            height=existing_photo.height,
            taken_at=existing_photo.taken_at,
            created_at=existing_photo.created_at,
            is_duplicate=True
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create photo from PhotoCreateSchema: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create photo: {str(e)}")


@router.post("/register-image", response_model=PhotoCreateResponse, status_code=201)
def register_image(
    file: UploadFile = File(..., description="Image file to register"),
    input_channel_id: Optional[int] = Query(None, description="Input channel ID (uses protected 'Quick Channel' if not provided)"),
    rating: int = Query(0, ge=0, le=5, description="Star rating 0-5"),
    visibility: str = Query("private", pattern="^(private|space|authenticated|public)$", description="Visibility level"),
    author_id: Optional[int] = Query(None, description="Author ID"),
    coldpreview_size: Optional[int] = Query(None, ge=150, description="Size for coldpreview (e.g., 2560)"),
    current_user: User = Depends(get_current_active_user),
    photo_service: PhotoService = Depends(get_photo_service)
):
    """
    Register image by sending to imalink-core for processing (Convenience endpoint)
    
    **Use case**: Quick web upload when user doesn't have desktop app available.
    **Not recommended for**: Batch imports (use desktop app with local imalink-core instead).
    
    Flow:
    1. Frontend uploads raw image file (multipart/form-data)
    2. Backend sends to imalink-core server (localhost:8001) for processing
    3. imalink-core returns PhotoCreateSchema (metadata + previews)
    4. Backend stores PhotoCreateSchema (same as POST /create endpoint)
    
    Note: Original image is NOT stored on server, only metadata and previews.
    
    Args:
        file: Image file (JPEG, PNG, etc.)
        input_channel_id: Optional input channel (defaults to protected 'Quick Channel')
        rating: Star rating 0-5
        visibility: Visibility level (private, space, authenticated, public)
        author_id: Optional photographer/author
        coldpreview_size: Optional size for larger preview (e.g., 2560px)
        
    Returns:
        PhotoCreateResponse: Created photo metadata
        
    Raises:
        400: If image processing fails or invalid image
        500: If imalink-core service unavailable
    """
    from src.utils.imalink_core_client import ImalinkCoreClient
    
    try:
        # Read uploaded file (sync)
        image_bytes = file.file.read()
        
        # Send to imalink-core for processing (sync)
        core_client = ImalinkCoreClient()
        photo_create_schema = core_client.process_image(
            image_bytes=image_bytes,
            filename=file.filename or "uploaded_image.jpg",
            coldpreview_size=coldpreview_size
        )
        
        # Set user organization fields (user_id will be set by service from authenticated user)
        photo_create_schema_dict = photo_create_schema.model_dump()
        photo_create_schema_dict["rating"] = rating
        photo_create_schema_dict["visibility"] = visibility
        photo_create_schema_dict["input_channel_id"] = input_channel_id
        photo_create_schema_dict["author_id"] = author_id
        photo_create_schema = PhotoCreateSchema(**photo_create_schema_dict)
        
        # Build PhotoCreateReq
        photo_create_request = PhotoCreateReq(
            photo_create_schema=photo_create_schema,
            tags=[],  # No tags for quick upload
        )
        
        # Create photo using existing PhotoCreateSchema logic
        photo = photo_service.create_photo_from_photo_create_schema(
            photo_create_request=photo_create_request,
            user_id=getattr(current_user, 'id')
        )
        
        return PhotoCreateResponse(
            id=photo.id,
            hothash=photo.hothash,
            rating=photo.rating,
            visibility=photo.visibility,
            width=photo.width,
            height=photo.height,
            taken_at=photo.taken_at,
            created_at=photo.created_at,
            user_id=photo.user_id,
            is_duplicate=False
        )
        
    except DuplicateImageError:
        # Photo already exists
        existing_photo = photo_service.get_photo_by_hothash(
            hothash=photo_create_schema.hothash,
            user_id=getattr(current_user, 'id')
        )
        return PhotoCreateResponse(
            id=existing_photo.id,
            hothash=existing_photo.hothash,
            rating=existing_photo.rating,
            visibility=existing_photo.visibility,
            width=existing_photo.width,
            height=existing_photo.height,
            taken_at=existing_photo.taken_at,
            created_at=existing_photo.created_at,
            user_id=existing_photo.user_id,
            is_duplicate=True
        )
    except httpx.HTTPStatusError as e:
        # imalink-core returned error (400, 500, etc.)
        logger.error(f"imalink-core error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Image processing failed: {e.response.json().get('detail', 'Unknown error')}"
        )
    except httpx.RequestError as e:
        # imalink-core service unavailable
        logger.error(f"Failed to connect to imalink-core: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Image processing service unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"Failed to register image: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register image: {str(e)}")

