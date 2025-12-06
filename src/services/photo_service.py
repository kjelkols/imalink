"""
Photo Service - Business logic for photo operations

ARCHITECTURAL NOTE (UPDATED):
Photos are created via POST /photos/new-photo which creates both Photo + ImageFile.
- Hotpreview and exif_dict stored in Photo (visual data)
- ImageFile stores only file metadata
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from pathlib import Path
import io
import hashlib

from src.repositories.photo_repository import PhotoRepository
from src.repositories.image_file_repository import ImageFileRepository
from src.schemas.photo_schemas import (
    PhotoResponse, PhotoCreateRequest, PhotoUpdateRequest, PhotoSearchRequest,
    AuthorSummary, ImageFileSummary, TimeLocCorrectionRequest, ViewCorrectionRequest
)
from src.schemas.tag_schemas import TagSummary
from src.schemas.image_file_upload_schemas import (
    ImageFileNewPhotoRequest, ImageFileAddToPhotoRequest, ImageFileUploadResponse
)
from src.schemas.common import PaginatedResponse, create_paginated_response
from src.core.exceptions import NotFoundError, DuplicatePhotoError, DuplicateImageError, ValidationError
from src.models import Photo, ImageFile

import logging
logger = logging.getLogger(__name__)


class PhotoService:
    """Service layer for Photo operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.photo_repo = PhotoRepository(db)
        self.image_file_repo = ImageFileRepository(db)
    
    def get_photos(
        self,
        user_id: Optional[int],
        offset: int = 0,
        limit: int = 100,
        author_id: Optional[int] = None,
        search_params: Optional[PhotoSearchRequest] = None
    ) -> PaginatedResponse[PhotoResponse]:
        """Get paginated list of photos (supports anonymous access for public photos)"""
        
        # Get photos from repository
        photos = self.photo_repo.get_photos(
            user_id=user_id,
            offset=offset,
            limit=limit,
            author_id=author_id,
            search_params=search_params
        )
        
        # Count total photos
        total = self.photo_repo.count_photos(
            user_id=user_id,
            author_id=author_id,
            search_params=search_params
        )
        
        # Convert to response models
        photo_responses = [self._convert_to_response(photo) for photo in photos]
        
        return create_paginated_response(
            data=photo_responses,
            total=total,
            offset=offset,
            limit=limit
        )
    
    def get_photo_by_hash(self, hothash: str, user_id: Optional[int]) -> PhotoResponse:
        """Get single photo by hash (supports anonymous access for public photos)"""
        photo = self.photo_repo.get_by_hash(hothash, user_id)
        if not photo:
            raise NotFoundError("Photo", hothash)
        
        return self._convert_to_response(photo)
    
    def create_photo_with_file(self, image_data: ImageFileNewPhotoRequest, user_id: int) -> ImageFileUploadResponse:
        """
        Create new Photo with initial ImageFile
        
        ARCHITECTURE:
        - Photo stores VISUAL data: hotpreview (150x150px thumbnail), exif_dict, dimensions, GPS
        - ImageFile stores FILE metadata: filename, size, storage locations
        - Photo is content-based (same visual content = same hothash, shared by JPEG/RAW)
        - ImageFile is file-based (each physical file = unique ImageFile entry)
        
        WORKFLOW:
        1. Pydantic validator has already converted Base64 hotpreview → bytes
        2. Generate SHA256 hothash from hotpreview bytes (content-based identifier)
        3. Check for duplicates - return 409 if Photo with same visual content exists
        4. Create Photo with visual/metadata (hotpreview, exif_dict, GPS, dimensions)
        5. Create ImageFile with file info (filename, size, storage locations)
        6. Return success response with photo_created=True
        """
        # 1. Pydantic validator guarantees hotpreview is bytes after Base64 decoding
        # Type annotation for mypy (type system sees Union[bytes, str] but validator ensures bytes)
        hotpreview_bytes: bytes = image_data.hotpreview  # type: ignore[assignment]
        
        # 2. Generate content-based hash from hotpreview (SHA256)
        hothash = self._generate_hothash_from_hotpreview(hotpreview_bytes)
        
        # 3. Check if Photo with same visual content already exists (user-scoped)
        # If duplicate found, client should use POST /photos/{hothash}/files instead
        existing_photo = self.photo_repo.get_by_hash(hothash, user_id)
        if existing_photo:
            raise DuplicateImageError(f"Photo with this image already exists (hothash: {hothash[:8]}...)")
        
        # 4. Create new Photo with visual data + ImageFile with file metadata
        image_file = self._create_new_photo_with_image_file(
            image_data, hothash, hotpreview_bytes, user_id
        )
        
        # 5. Commit transaction
        self.db.commit()
        self.db.refresh(image_file)
        
        # 6. Return success response
        return ImageFileUploadResponse(
            image_file_id=getattr(image_file, 'id'),
            filename=getattr(image_file, 'filename'),
            file_size=getattr(image_file, 'file_size', None),
            photo_hothash=hothash,
            photo_created=True,
            success=True,
            message="New photo created successfully"
        )
    
    def add_file_to_photo(self, hothash: str, image_data: ImageFileAddToPhotoRequest, user_id: int) -> ImageFileUploadResponse:
        """
        Add new ImageFile to an existing Photo
        
        USE CASE: Adding companion files (RAW, different resolution, etc.)
        - Photo already exists with visual data
        - ImageFile stores only file metadata (no hotpreview/exif)
        
        WORKFLOW:
        1. Validate that Photo exists and belongs to user
        2. Create ImageFile with only file metadata
        3. Return success response
        """
        # 1. Validate that Photo exists and belongs to user
        existing_photo = self.photo_repo.get_by_hash(hothash, user_id)
        if not existing_photo:
            raise NotFoundError("Photo", hothash)
        
        # 2. Create ImageFile for existing Photo (no visual data)
        image_file = self._create_image_file_for_existing_photo(image_data, existing_photo.id, user_id)
        
        # 3. Commit transaction
        self.db.commit()
        self.db.refresh(image_file)
        
        # 4. Return success response
        return ImageFileUploadResponse(
            image_file_id=getattr(image_file, 'id'),
            filename=getattr(image_file, 'filename'),
            file_size=getattr(image_file, 'file_size', None),
            photo_hothash=hothash,
            photo_created=False,
            success=True,
            message="Image file added to existing photo successfully"
        )
    
    # NOTE: Photo creation removed - Photos are now created automatically via ImageFile service
    # When an ImageFile is created without hothash, a new Photo is auto-generated
    # This architecture change makes ImageFile the entry point for photo management
    
    def update_photo(self, hothash: str, photo_data: PhotoUpdateRequest, user_id: int) -> PhotoResponse:
        """Update existing photo (user-scoped)"""
        
        # Update photo
        photo = self.photo_repo.update(hothash, photo_data, user_id)
        if not photo:
            raise NotFoundError("Photo", hothash)
        
        self.db.commit()
        return self._convert_to_response(photo)
    
    def delete_photo(self, hothash: str, user_id: int) -> bool:
        """Delete photo (user-scoped)"""
        success = self.photo_repo.delete(hothash, user_id)
        if not success:
            raise NotFoundError("Photo", hothash)
        
        self.db.commit()
        return True
    
    def get_hotpreview(self, hothash: str) -> Optional[bytes]:
        """Get hotpreview data for photo"""
        hotpreview_data = self.photo_repo.get_hotpreview(hothash)
        if not hotpreview_data:
            raise NotFoundError("Hotpreview", hothash)
        
        return hotpreview_data
    
    def upload_coldpreview(self, hothash: str, file_content: bytes, user_id: int) -> Dict[str, Any]:
        """Upload or update coldpreview for a photo (user-scoped)"""
        # Get photo to ensure it exists and user has access
        photo = self.photo_repo.get_by_hash(hothash, user_id)
        if not photo:
            raise NotFoundError("Photo", hothash)
        
        # Use coldpreview repository utility
        from src.utils.coldpreview_repository import ColdpreviewRepository
        repository = ColdpreviewRepository()
        
        # Save coldpreview and get metadata (returns tuple)
        relative_path, width, height, file_size = repository.save_coldpreview(hothash, file_content)
        
        # SIMPLIFIED: Only store path, dimensions/size will be read dynamically
        setattr(photo, 'coldpreview_path', relative_path)
        
        # Commit changes
        self.db.commit()
        self.db.refresh(photo)
        
        return {
            'hothash': hothash,
            'width': width,
            'height': height,
            'size': file_size,
            'path': relative_path
        }
    
    def get_coldpreview(self, hothash: str, user_id: int, width: Optional[int] = None, height: Optional[int] = None) -> Optional[bytes]:
        """Get coldpreview image for photo with optional resizing (user-scoped)"""
        # Get photo and verify user has access
        photo = self.photo_repo.get_by_hash(hothash, user_id)
        if not photo:
            raise NotFoundError("Photo", hothash)
        
        # Check if coldpreview exists
        if not getattr(photo, 'coldpreview_path', None):
            return None
        
        # Use coldpreview repository utility
        from src.utils.coldpreview_repository import ColdpreviewRepository
        repository = ColdpreviewRepository()
        
        # Load coldpreview with optional resizing
        if width or height:
            # First load the original image
            original_data = repository.load_coldpreview_by_hash(hothash)
            if not original_data:
                return None
            # Then resize it
            return repository.resize_coldpreview(original_data, target_width=width, target_height=height)
        else:
            return repository.load_coldpreview_by_hash(hothash)
    
    def delete_coldpreview(self, hothash: str, user_id: int) -> None:
        """Delete coldpreview for photo (user-scoped)"""
        # Get photo and verify user has access
        photo = self.photo_repo.get_by_hash(hothash, user_id)
        if not photo:
            raise NotFoundError("Photo", hothash)
        
        # Check if coldpreview exists
        if not getattr(photo, 'coldpreview_path', None):
            raise NotFoundError("Coldpreview", hothash)
        
        # Use coldpreview repository utility
        from src.utils.coldpreview_repository import ColdpreviewRepository
        repository = ColdpreviewRepository()
        
        # Delete from filesystem (need to construct full path from relative path)
        # We need to pass the hothash since that's what the delete method expects
        try:
            repository.delete_coldpreview_by_hash(hothash)
        except Exception:
            pass  # File might already be deleted, continue with database cleanup
        
        # Clear path in database
        setattr(photo, 'coldpreview_path', None)
        self.db.commit()
    
    def search_photos(self, search_params: PhotoSearchRequest, user_id: int) -> PaginatedResponse[PhotoResponse]:
        """Search photos with advanced filtering (user-scoped)"""
        return self.get_photos(
            offset=search_params.offset,
            limit=search_params.limit,
            search_params=search_params,
            user_id=user_id
        )
    
    def update_timeloc_correction(
        self, 
        hothash: str, 
        correction: Optional[TimeLocCorrectionRequest], 
        user_id: int
    ) -> PhotoResponse:
        """
        Update time/location correction for photo (non-destructive)
        
        Args:
            hothash: Photo identifier
            correction: Correction data or None to restore from EXIF
            user_id: Current user ID
        
        Returns:
            Updated PhotoResponse
        
        Behavior:
            - If correction is None: Restore taken_at/GPS from Photo.exif_dict, clear timeloc_correction
            - If correction has data: Update timeloc_correction JSON and Photo display fields
        """
        from src.utils.exif_utils import parse_exif_datetime, parse_exif_gps_latitude, parse_exif_gps_longitude
        
        # Get photo (user-scoped)
        photo = self.photo_repo.get_by_hash(hothash, user_id)
        if not photo:
            raise NotFoundError("Photo", hothash)
        
        # Case 1: NULL request - Restore from EXIF
        if correction is None:
            # Clear correction
            setattr(photo, 'timeloc_correction', None)
            
            # Restore from EXIF (stored in Photo.exif_dict)
            exif_dict = getattr(photo, 'exif_dict', None)
            setattr(photo, 'taken_at', parse_exif_datetime(exif_dict))
            setattr(photo, 'gps_latitude', parse_exif_gps_latitude(exif_dict) or 0.0)
            setattr(photo, 'gps_longitude', parse_exif_gps_longitude(exif_dict) or 0.0)
        
        # Case 2: Update/create correction
        else:
            # Get existing correction or create new dict
            timeloc_correction = getattr(photo, 'timeloc_correction', None) or {}
            
            # Update correction fields and Photo display fields
            if correction.taken_at is not None:
                timeloc_correction['taken_at'] = correction.taken_at.isoformat()
                setattr(photo, 'taken_at', correction.taken_at)
            
            if correction.gps_latitude is not None:
                timeloc_correction['gps_latitude'] = correction.gps_latitude
                setattr(photo, 'gps_latitude', correction.gps_latitude)
            
            if correction.gps_longitude is not None:
                timeloc_correction['gps_longitude'] = correction.gps_longitude
                setattr(photo, 'gps_longitude', correction.gps_longitude)
            
            if correction.correction_reason:
                timeloc_correction['correction_reason'] = correction.correction_reason
            
            # Add metadata
            timeloc_correction['corrected_at'] = datetime.utcnow().isoformat()
            timeloc_correction['corrected_by'] = user_id
            
            setattr(photo, 'timeloc_correction', timeloc_correction)
        
        # Commit changes
        self.db.commit()
        self.db.refresh(photo)
        
        return self._convert_to_response(photo)
    
    def update_view_correction(
        self, 
        hothash: str, 
        correction: Optional[ViewCorrectionRequest], 
        user_id: int
    ) -> PhotoResponse:
        """
        Update view correction for photo (frontend rendering hints only)
        
        Args:
            hothash: Photo identifier
            correction: View correction settings or None to reset
            user_id: Current user ID
        
        Returns:
            Updated PhotoResponse
        
        Behavior:
            - If correction is None: Remove all view corrections
            - If correction has data: Update view_correction JSON (no image processing)
        """
        # Get photo (user-scoped)
        photo = self.photo_repo.get_by_hash(hothash, user_id)
        if not photo:
            raise NotFoundError("Photo", hothash)
        
        # Case 1: NULL request - Remove all corrections
        if correction is None:
            setattr(photo, 'view_correction', None)
        
        # Case 2: Update/create correction
        else:
            # Get existing correction or create new dict
            view_correction = getattr(photo, 'view_correction', None) or {}
            
            # Update correction fields
            if correction.rotation is not None:
                view_correction['rotation'] = correction.rotation
            
            if correction.relative_crop is not None:
                view_correction['relative_crop'] = {
                    'x': correction.relative_crop.x,
                    'y': correction.relative_crop.y,
                    'width': correction.relative_crop.width,
                    'height': correction.relative_crop.height
                }
            
            if correction.exposure_adjust is not None:
                view_correction['exposure_adjust'] = correction.exposure_adjust
            
            # Add metadata
            view_correction['corrected_at'] = datetime.utcnow().isoformat()
            view_correction['corrected_by'] = user_id
            
            setattr(photo, 'view_correction', view_correction)
        
        # Commit changes
        self.db.commit()
        self.db.refresh(photo)
        
        return self._convert_to_response(photo)
    
    def _convert_to_response(self, photo: Photo) -> PhotoResponse:
        """Convert Photo model to PhotoResponse"""
        
        # Convert author if present
        author = None
        if photo.author:
            author = AuthorSummary(
                id=photo.author.id,
                name=photo.author.name
            )
        
        # Convert associated image files
        files = []
        if photo.image_files:
            for image_file in photo.image_files:
                file_format = self._get_file_format(image_file.filename)
                files.append(ImageFileSummary(
                    id=image_file.id,
                    filename=image_file.filename,
                    file_format=file_format,
                    file_size=image_file.file_size
                ))
        
        # Compute derived properties
        has_gps = photo.has_gps
        has_raw_companion = photo.has_raw_companion
        primary_filename = photo.primary_filename
        
        # Get coldpreview metadata dynamically from file
        coldpreview_path = getattr(photo, 'coldpreview_path', None)
        coldpreview_metadata = None
        if coldpreview_path:
            from src.utils.coldpreview_repository import ColdpreviewRepository
            repository = ColdpreviewRepository()
            coldpreview_metadata = repository.get_coldpreview_metadata(coldpreview_path)
        
        return PhotoResponse(
            hothash=getattr(photo, 'hothash'),
            width=getattr(photo, 'width', None),
            height=getattr(photo, 'height', None),
            coldpreview_path=coldpreview_path,
            coldpreview_width=coldpreview_metadata["width"] if coldpreview_metadata else None,
            coldpreview_height=coldpreview_metadata["height"] if coldpreview_metadata else None,
            coldpreview_size=coldpreview_metadata["size"] if coldpreview_metadata else None,
            taken_at=getattr(photo, 'taken_at', None),
            gps_latitude=getattr(photo, 'gps_latitude', None),
            gps_longitude=getattr(photo, 'gps_longitude', None),
            exif_dict=getattr(photo, 'exif_dict', None),
            rating=getattr(photo, 'rating', 0),
            visibility=getattr(photo, 'visibility', 'private'),  # Phase 1: Include visibility
            category=getattr(photo, 'category', None),
            created_at=getattr(photo, 'created_at'),
            updated_at=getattr(photo, 'updated_at'),
            author=author,
            author_id=getattr(photo, 'author_id', None),
            event_id=getattr(photo, 'event_id', None),
            input_channel_id=getattr(photo, 'input_channel_id', None),
            first_imported=photo.first_imported,
            last_imported=photo.last_imported,
            has_gps=has_gps,
            has_raw_companion=has_raw_companion,
            primary_filename=primary_filename,
            files=files,
            timeloc_correction=getattr(photo, 'timeloc_correction', None),
            view_correction=getattr(photo, 'view_correction', None),
            tags=[TagSummary(id=tag.id, name=tag.name) for tag in getattr(photo, 'tags', [])]
        )
    

    
    def _get_file_format(self, filename: str) -> str:
        """Determine file format from filename"""
        if not filename:
            return "unknown"
        
        ext = Path(filename).suffix.lower()
        
        # Map extensions to formats
        format_map = {
            ".jpg": "jpeg",
            ".jpeg": "jpeg",
            ".png": "png",
            ".gif": "gif",
            ".bmp": "bmp",
            ".tiff": "tiff",
            ".tif": "tiff",
            ".webp": "webp",
            ".cr2": "raw",
            ".nef": "raw", 
            ".arw": "raw",
            ".dng": "raw",
            ".orf": "raw",
            ".rw2": "raw",
            ".raw": "raw"
        }
        
        return format_map.get(ext, "unknown")
    
    # ========== Private Helper Methods for Photo+ImageFile Creation ==========
    
    def _create_new_photo_with_image_file(
        self, 
        image_data: ImageFileNewPhotoRequest, 
        hothash: str, 
        hotpreview_bytes: bytes, 
        user_id: int
    ) -> ImageFile:
        """
        Create new Photo with visual data + ImageFile with file metadata
        
        DATA SEPARATION ARCHITECTURE:
        - Photo gets: hotpreview (visual), exif_dict, GPS, dimensions, rating, author
        - ImageFile gets: filename, file_size, import info, storage locations
        
        WHY: Photo is about CONTENT (what you see), ImageFile is about FILES (where it is)
        This allows JPEG/RAW pairs to share same Photo (same content, different files)
        """
        # 1. Create Photo with visual and content metadata
        photo_data_dict = {
            'hothash': hothash,
            'hotpreview': hotpreview_bytes,
            'exif_dict': image_data.exif_dict,
            'taken_at': image_data.taken_at,
            'gps_latitude': image_data.gps_latitude,
            'gps_longitude': image_data.gps_longitude,
            'visibility': image_data.visibility,  # Visibility control
            'import_session_id': image_data.import_session_id,  # Track which import session created this Photo
            # Try to extract dimensions from EXIF metadata
            # Common EXIF fields: ImageWidth, ImageHeight, ExifImageWidth, ExifImageHeight
            'width': (image_data.exif_dict.get('ImageWidth') or 
                     image_data.exif_dict.get('ExifImageWidth')) if image_data.exif_dict else None,
            'height': (image_data.exif_dict.get('ImageHeight') or 
                      image_data.exif_dict.get('ExifImageHeight')) if image_data.exif_dict else None,
        }
        photo_data = PhotoCreateRequest(**photo_data_dict)
        photo = self.photo_repo.create(photo_data, user_id=user_id)
        
        # 2. Create ImageFile with only file metadata (no visual data, no import_session_id)
        image_data_dict = {
            'filename': image_data.filename,
            'file_size': image_data.file_size,
            'photo_id': photo.id,  # Link via integer ID for performance
            'imported_time': datetime.utcnow(),
            'imported_info': image_data.imported_info,
            'local_storage_info': image_data.local_storage_info,
            'cloud_storage_info': image_data.cloud_storage_info,
        }
        
        image_file = self.image_file_repo.create(image_data_dict, user_id)
        
        return image_file
    
    def _create_image_file_for_existing_photo(
        self, 
        image_data: ImageFileAddToPhotoRequest, 
        photo_id: int,
        user_id: int
    ) -> ImageFile:
        """
        Create ImageFile for existing Photo (file metadata only)
        Note: import_session_id is NOT set here - it's already on the Photo
        
        Args:
            image_data: File metadata
            photo_id: Photo's integer ID (not hothash)
            user_id: User ID
        """
        image_data_dict = {
            'filename': image_data.filename,
            'file_size': image_data.file_size,
            'photo_id': photo_id,  # Link via integer ID for performance
            'imported_time': datetime.utcnow(),
            'imported_info': image_data.imported_info,
            'local_storage_info': image_data.local_storage_info,
            'cloud_storage_info': image_data.cloud_storage_info,
        }
        
        image_file = self.image_file_repo.create(image_data_dict, user_id)
        
        return image_file
    
    def _generate_hothash_from_hotpreview(self, hotpreview_bytes: bytes) -> str:
        """Generate SHA256 hash from hotpreview bytes"""
        return hashlib.sha256(hotpreview_bytes).hexdigest()

    def create_photo_from_photo_create_schema(self, photo_create_request, user_id: int) -> Photo:
        """
        Create Photo from PhotoCreateSchema (matches MY_OVERVIEW.md)
        
        PhotoCreateSchema comes from imalink-core and contains:
        - hothash, hotpreview (base64)
        - exif_dict with ALL EXIF (camera_make, iso, etc.)
        - width, height, taken_at, gps_latitude, gps_longitude
        - user_id, rating, category, visibility, etc.
        - image_file_list (one or more source files)
        
        Args:
            photo_create_request: PhotoCreateRequest with photo_create_schema and tags
            user_id: Owner user ID (overrides photo_create_schema.user_id for security)
            
        Returns:
            Created Photo with associated ImageFile records
            
        Raises:
            DuplicateImageError: If photo with same hothash already exists for this user
            ValueError: If required fields missing
        """
        import base64
        from src.repositories.input_channel_repository import InputChannelRepository
        from src.models.image_file import ImageFile
        
        schema = photo_create_request.photo_create_schema
        
        # Security: user_id is set from authenticated user (NOT from schema)
        # PhotoCreateSchema does NOT contain user_id - backend adds it
        
        # Resolve input_channel_id - use protected default if not provided
        input_channel_id = schema.input_channel_id
        channel_repo = InputChannelRepository(self.db)
        
        # Validate input_channel_id if provided
        if input_channel_id is not None:
            channel = channel_repo.get_channel_by_id(input_channel_id, user_id)
            if not channel:
                logger.warning(
                    f"Invalid input_channel_id={input_channel_id} for user {user_id} "
                    f"(channel does not exist or belongs to another user). "
                    f"Falling back to protected Quick Channel."
                )
                input_channel_id = None  # Fall back to Quick Channel
        
        if input_channel_id is None:
            default_channel = channel_repo.get_protected_channel(user_id)
            
            if not default_channel:
                raise ValueError(
                    "No input_channel_id provided and no protected default channel found. "
                    "This should not happen - contact administrator."
                )
            
            input_channel_id = default_channel.id
        
        # Resolve author_id - use user's default self-author if not provided
        author_id = schema.author_id
        if author_id is None:
            from src.repositories.user_repository import UserRepository
            user_repo = UserRepository(self.db)
            user = user_repo.get_by_id(user_id)
            
            if not user or not user.default_author_id:
                raise ValueError(
                    "No author_id provided and user has no default author. "
                    "This should not happen - contact administrator."
                )
            
            author_id = user.default_author_id
        
        # Check for duplicate
        existing = self.photo_repo.get_by_hash(schema.hothash, user_id)
        if existing:
            raise DuplicateImageError(f"Photo with hothash {schema.hothash} already exists")
        
        # Decode base64 hotpreview
        hotpreview_bytes = base64.b64decode(schema.hotpreview_base64)
        
        # exif_dict already contains ALL EXIF metadata from imalink-core
        # (camera_make, iso, aperture, etc. are IN exif_dict, not at root)
        exif_dict = schema.exif_dict or {}
        
        # Create Photo matching MY_OVERVIEW.md structure
        photo = Photo(
            user_id=user_id,
            hothash=schema.hothash,
            hotpreview=hotpreview_bytes,
            width=schema.width,
            height=schema.height,
            
            # Time & location (indexed copies from exif_dict for fast queries)
            taken_at=schema.taken_at,
            gps_latitude=schema.gps_latitude,
            gps_longitude=schema.gps_longitude,
            
            # Complete EXIF metadata (all camera/lens data stored here)
            exif_dict=exif_dict,
            
            # User organization fields
            rating=schema.rating,
            category=schema.category,
            visibility=schema.visibility,
            input_channel_id=input_channel_id,
            author_id=author_id,
            stack_id=schema.stack_id,
            
            # Corrections (usually null initially)
            timeloc_correction=schema.timeloc_correction,
            view_correction=schema.view_correction,
        )
        
        # Handle coldpreview (optional larger preview)
        if schema.coldpreview_base64:
            from src.utils.coldpreview_repository import ColdpreviewRepository
            repository = ColdpreviewRepository()
            
            # Decode and save to filesystem
            coldpreview_bytes = base64.b64decode(schema.coldpreview_base64)
            relative_path, _, _, _ = repository.save_coldpreview(schema.hothash, coldpreview_bytes)
            photo.coldpreview_path = relative_path
        
        # Save Photo first
        self.db.add(photo)
        self.db.flush()  # Get photo.id without committing yet
        
        # Create ImageFile records for each source file
        for image_file_schema in schema.image_file_list:
            image_file = ImageFile(
                photo_id=photo.id,
                filename=image_file_schema.filename,
                file_size=image_file_schema.file_size,
                imported_time=image_file_schema.imported_time,
                imported_info=image_file_schema.imported_info,
                local_storage_info=image_file_schema.local_storage_info,
                cloud_storage_info=image_file_schema.cloud_storage_info,
            )
            self.db.add(image_file)
        
        # Commit everything (Photo + ImageFiles)
        self.db.commit()
        self.db.refresh(photo)
        
        # TODO: Add tags if provided
        # if photo_create_request.tags:
        #     for tag_name in photo_create_request.tags:
        #         # Associate tag with photo
        #         pass
        
        return photo
    
    def get_photo_by_hothash(self, hothash: str, user_id: int) -> Photo:
        """
        Get photo by hothash for specific user
        
        Args:
            hothash: Photo hothash
            user_id: Owner user ID
            
        Returns:
            Photo
            
        Raises:
            NotFoundError: If photo not found
        """
        photo = self.photo_repo.get_by_hash(hothash, user_id)
        if not photo:
            raise NotFoundError("Photo", hothash)
        return photo
    
    def set_event(self, hothash: str, event_id: Optional[int], user_id: int) -> PhotoResponse:
        """
        Set or unset photo's event
        
        Args:
            hothash: Photo identifier
            event_id: Event ID (None to unset)
            user_id: User ID for ownership
            
        Returns:
            Updated photo response
            
        Raises:
            NotFoundError: If photo or event not found
            ValidationError: If validation fails
        """
        try:
            photo = self.photo_repo.set_event(hothash, event_id, user_id)
            return self._convert_to_response(photo)
        except ValueError as e:
            if "not found" in str(e).lower():
                raise NotFoundError("Photo or Event", hothash)
            raise ValidationError(str(e))
