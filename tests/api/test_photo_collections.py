"""
Tests for Photo Collections API endpoints with text cards support
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import User, Photo, PhotoCollection


class TestPhotoCollectionsAPI:
    """Test suite for Photo Collections API endpoints"""
    
    def test_create_collection_basic(self, client: TestClient, test_user: User, auth_headers: dict):
        """Test creating a basic empty collection"""
        response = client.post(
            "/api/v1/collections",
            json={
                "name": "Summer 2024",
                "description": "Best vacation photos"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Summer 2024"
        assert data["description"] == "Best vacation photos"
        assert data["user_id"] == test_user.id
        assert data["item_count"] == 0
        assert data["photo_count"] == 0
        assert data["text_card_count"] == 0
        assert data["items"] == []
    
    def test_create_collection_with_photos(
        self, 
        client: TestClient, 
        test_user: User, 
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test creating collection with initial photos"""
        # Create test photos
        photo1 = Photo(
            user_id=test_user.id,
            hothash="abc123",
            width=1000,
            height=800,
            hotpreview=b"fake_preview_1"
        )
        photo2 = Photo(
            user_id=test_user.id,
            hothash="def456",
            width=1000,
            height=800,
            hotpreview=b"fake_preview_2"
        )
        test_db_session.add_all([photo1, photo2])
        test_db_session.commit()
        
        response = client.post(
            "/api/v1/collections",
            json={
                "name": "My Photos",
                "hothashes": ["abc123", "def456"]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["item_count"] == 2
        assert data["photo_count"] == 2
        assert data["text_card_count"] == 0
        assert len(data["items"]) == 2
        assert data["items"][0]["type"] == "photo"
        assert data["items"][0]["photo_hothash"] == "abc123"
        assert data["items"][1]["type"] == "photo"
        assert data["items"][1]["photo_hothash"] == "def456"
    
    def test_add_items_photos_and_text(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test adding mixed items (photos + text cards) to collection"""
        # Create photo
        photo = Photo(
            user_id=test_user.id,
            hothash="abc123",
            width=1000,
            height=800,
            hotpreview=b"fake_preview"
        )
        test_db_session.add(photo)
        
        # Create collection
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test Collection"
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Add items
        response = client.post(
            f"/api/v1/collections/{collection.id}/items",
            json={
                "items": [
                    {
                        "type": "photo",
                        "photo_hothash": "abc123"
                    },
                    {
                        "type": "text",
                        "text_card": {
                            "title": "Summer Memories",
                            "body": "What a wonderful trip!"
                        }
                    }
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 2
        assert data["photo_count"] == 1
        assert data["affected_count"] == 2
        
        # Verify collection state
        get_response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        collection_data = get_response.json()
        
        assert len(collection_data["items"]) == 2
        assert collection_data["items"][0]["type"] == "photo"
        assert collection_data["items"][1]["type"] == "text"
        assert collection_data["items"][1]["text_card"]["title"] == "Summer Memories"
        assert collection_data["items"][1]["text_card"]["body"] == "What a wonderful trip!"
        assert collection_data["text_card_count"] == 1
    
    def test_add_items_skips_duplicate_photos(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test that adding duplicate photos is skipped"""
        # Create photo
        photo = Photo(
            user_id=test_user.id,
            hothash="abc123",
            width=1000,
            height=800,
            hotpreview=b"fake_preview"
        )
        test_db_session.add(photo)
        
        # Create collection with photo
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test Collection",
            items=[{"type": "photo", "photo_hothash": "abc123"}]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Try to add same photo again
        response = client.post(
            f"/api/v1/collections/{collection.id}/items",
            json={
                "items": [
                    {"type": "photo", "photo_hothash": "abc123"}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["affected_count"] == 0  # Duplicate skipped
        assert data["item_count"] == 1  # Still only 1 item
    
    def test_reorder_items(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test reordering items in collection"""
        # Create photos
        photo1 = Photo(user_id=test_user.id, hothash="abc", width=100, height=100, hotpreview=b"1")
        photo2 = Photo(user_id=test_user.id, hothash="def", width=100, height=100, hotpreview=b"2")
        test_db_session.add_all([photo1, photo2])
        
        # Create collection with items
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "photo", "photo_hothash": "abc"},
                {"type": "text", "text_card": {"title": "Text 1", "body": "Body"}},
                {"type": "photo", "photo_hothash": "def"}
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Reorder items
        response = client.put(
            f"/api/v1/collections/{collection.id}/items/reorder",
            json={
                "items": [
                    {"type": "photo", "photo_hothash": "def"},
                    {"type": "text", "text_card": {"title": "Text 1", "body": "Body"}},
                    {"type": "photo", "photo_hothash": "abc"}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 3
        
        # Verify order
        get_response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        items = get_response.json()["items"]
        assert items[0]["photo_hothash"] == "def"
        assert items[1]["type"] == "text"
        assert items[2]["photo_hothash"] == "abc"
    
    def test_delete_item_at_position(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test deleting item at specific position"""
        photo1 = Photo(user_id=test_user.id, hothash="abc", width=100, height=100, hotpreview=b"1")
        photo2 = Photo(user_id=test_user.id, hothash="def", width=100, height=100, hotpreview=b"2")
        test_db_session.add_all([photo1, photo2])
        
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "photo", "photo_hothash": "abc"},
                {"type": "text", "text_card": {"title": "Text", "body": "Body"}},
                {"type": "photo", "photo_hothash": "def"}
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Delete item at position 1 (text card)
        response = client.delete(
            f"/api/v1/collections/{collection.id}/items/1",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 2
        assert data["affected_count"] == 1
        
        # Verify text card removed
        get_response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        items = get_response.json()["items"]
        assert len(items) == 2
        assert items[0]["type"] == "photo"
        assert items[1]["type"] == "photo"
    
    def test_update_text_card(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test updating text card content"""
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "text", "text_card": {"title": "Old Title", "body": "Old Body"}}
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Update text card
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0",
            json={
                "title": "New Title",
                "body": "New Body"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify update
        get_response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        item = get_response.json()["items"][0]
        assert item["text_card"]["title"] == "New Title"
        assert item["text_card"]["body"] == "New Body"
    
    def test_update_text_card_fails_for_photo(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test that updating text card fails if item is a photo"""
        photo = Photo(user_id=test_user.id, hothash="abc", width=100, height=100, hotpreview=b"1")
        test_db_session.add(photo)
        
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[{"type": "photo", "photo_hothash": "abc"}]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Try to update photo as text card
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0",
            json={"title": "Should Fail"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "not a text card" in response.json()["detail"]
    
    def test_text_card_validation_max_length(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test text card title and body max length validation"""
        collection = PhotoCollection(user_id=test_user.id, name="Test")
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Title too long (max 200 chars)
        response = client.post(
            f"/api/v1/collections/{collection.id}/items",
            json={
                "items": [{
                    "type": "text",
                    "text_card": {
                        "title": "x" * 201,
                        "body": "Valid body"
                    }
                }]
            },
            headers=auth_headers
        )
        assert response.status_code == 422
        
        # Body too long (max 2000 chars)
        response = client.post(
            f"/api/v1/collections/{collection.id}/items",
            json={
                "items": [{
                    "type": "text",
                    "text_card": {
                        "title": "Valid title",
                        "body": "x" * 2001
                    }
                }]
            },
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_get_collection_extracts_photos_from_items(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test that photos can be extracted from items array"""
        photo1 = Photo(user_id=test_user.id, hothash="abc", width=100, height=100, hotpreview=b"1")
        photo2 = Photo(user_id=test_user.id, hothash="def", width=100, height=100, hotpreview=b"2")
        test_db_session.add_all([photo1, photo2])
        
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "photo", "photo_hothash": "abc"},
                {"type": "text", "text_card": {"title": "Text", "body": "Body"}},
                {"type": "photo", "photo_hothash": "def"}
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Get collection and extract photos from items
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["photo_count"] == 2
        assert data["text_card_count"] == 1
        
        # Extract photos from items (what frontend should do)
        photo_hothashes = [
            item["photo_hothash"]
            for item in data["items"]
            if item.get("type") == "photo"
        ]
        assert photo_hothashes == ["abc", "def"]
    
    def test_user_isolation(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test that users cannot access other users' collections"""
        # Create another user
        other_user = User(username="other", email="other@example.com", password_hash="fake")
        test_db_session.add(other_user)
        test_db_session.commit()  # Commit to get other_user.id
        
        # Create collection for other user
        collection = PhotoCollection(user_id=other_user.id, name="Other's Collection", items=[])
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Try to access other user's collection
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        assert response.status_code == 404
        
        # Try to add items to other user's collection
        response = client.post(
            f"/api/v1/collections/{collection.id}/items",
            json={"items": [{"type": "text", "text_card": {"title": "Test", "body": "Test"}}]},
            headers=auth_headers
        )
        assert response.status_code == 404
