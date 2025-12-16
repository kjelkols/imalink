"""
Input Channel API - Simple CRUD for user's reference metadata

InputChannel is NOT a file processor - it's a metadata container for:
- User's notes about an input channel
- When photos were imported  
- Who took the photos
- Where the client stored the files

All file operations are handled by the client application.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.dependencies import get_input_channel_service
from src.api.dependencies import get_current_user
from src.services.input_channel_service import InputChannelService
from src.models.user import User
from src.schemas.requests.input_channel_requests import (
    InputChannelCreateRequest, 
    InputChannelUpdateRequest
)
from src.schemas.responses.input_channel_responses import (
    InputChannelResponse,
    InputChannelListResponse
)
from src.schemas.common import create_success_response
from src.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=InputChannelResponse, status_code=201)
def create_input_channel(
    request: InputChannelCreateRequest,
    service: InputChannelService = Depends(get_input_channel_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new input channel (user's reference metadata).
    
    Client has already imported the images - this just records metadata.
    """
    try:
        response = service.create_simple_channel(
            user_id=current_user.id,
            title=request.title,
            description=request.description,
            default_author_id=request.default_author_id
        )
        
        logger.info(f"Created input channel: {request.title}")
        return response
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating input channel: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create input channel: {str(e)}")


@router.get("/{channel_id}", response_model=InputChannelResponse)
def get_input_channel(
    channel_id: int,
    service: InputChannelService = Depends(get_input_channel_service),
    current_user: User = Depends(get_current_user)
):
    """Get a specific input channel by ID"""
    try:
        return service.get_channel_by_id(channel_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving input channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve input channel: {str(e)}")


@router.get("/", response_model=InputChannelListResponse)
def list_input_channels(
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    service: InputChannelService = Depends(get_input_channel_service),
    current_user: User = Depends(get_current_user)
):
    """List all input channels with pagination"""
    try:
        return service.list_simple_channels(user_id=current_user.id, limit=limit, offset=offset)
    except Exception as e:
        logger.error(f"Error listing input channels: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list input channels: {str(e)}")


@router.patch("/{channel_id}", response_model=InputChannelResponse)
def update_input_channel(
    channel_id: int,
    request: InputChannelUpdateRequest,
    service: InputChannelService = Depends(get_input_channel_service),
    current_user: User = Depends(get_current_user)
):
    """Update input channel metadata"""
    try:
        response = service.update_simple_channel(
            channel_id=channel_id,
            user_id=current_user.id,
            title=request.title,
            description=request.description,
            default_author_id=request.default_author_id
        )
        
        logger.info(f"Updated input channel {channel_id}")
        return response
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating input channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update input channel: {str(e)}")


@router.delete("/{channel_id}")
def delete_input_channel(
    channel_id: int,
    service: InputChannelService = Depends(get_input_channel_service),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an input channel.
    
    WARNING: This will also delete all images associated with this input channel
    due to cascade delete. Use with caution.
    """
    try:
        service.delete_channel(channel_id, current_user.id)
        logger.info(f"Deleted input channel {channel_id}")
        return create_success_response(message="Input channel deleted successfully")
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting input channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete input channel: {str(e)}")
