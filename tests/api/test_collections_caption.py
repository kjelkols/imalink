"""
Test caption functionality for photo items in collections
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.photo import Photo
from src.models.photo_collection import PhotoCollection


@pytest.fixture
def test_photos(test_db_session: Session, test_user: User):
    """Create test photos"""
    photos = [
        Photo(user_id=test_user.id, hothash=f"chash{i}", width=100, height=100, hotpreview=b"x")
        for i in range(5)
    ]
    test_db_session.add_all(photos)
    test_db_session.commit()
    return photos


@pytest.fixture
def test_collection_with_photos(test_db_session: Session, test_user: User, test_photos):
    """Create collection with photo items for testing"""
    photos = test_photos
    
    collection = PhotoCollection(
        user_id=test_user.id,
        name="Caption Test Collection",
        description="Testing caption functionality",
        items=[
            {"type": "photo", "photo_hothash": photos[0].hothash, "visible": True},
            {"type": "photo", "photo_hothash": photos[1].hothash, "visible": True, "caption": "Existing caption"},
            {"type": "text", "text_card": {"title": "Title", "body": "Body"}, "visible": True},
            {"type": "photo", "photo_hothash": photos[2].hothash},  # Old format without caption
        ]
    )
    test_db_session.add(collection)
    test_db_session.commit()
    test_db_session.refresh(collection)
    
    return collection


class TestCaptionUpdate:
    """Test caption update endpoint"""
    
    def test_add_caption_to_photo(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test adding caption to photo without caption"""
        collection = test_collection_with_photos
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0/caption",
            json={"caption": "Beautiful sunset over the mountains"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["collection_id"] == collection.id
        assert data["position"] == 0
        assert data["caption"] == "Beautiful sunset over the mountains"
        assert data["item_count"] == 4
    
    def test_update_existing_caption(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test updating existing caption"""
        collection = test_collection_with_photos
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/1/caption",
            json={"caption": "Updated caption text"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["caption"] == "Updated caption text"
    
    def test_remove_caption(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test removing caption by setting to null"""
        collection = test_collection_with_photos
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/1/caption",
            json={"caption": None},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["caption"] is None
    
    def test_caption_with_whitespace_trimmed(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test that leading/trailing whitespace is trimmed"""
        collection = test_collection_with_photos
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0/caption",
            json={"caption": "  Caption with spaces  "},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["caption"] == "Caption with spaces"  # Trimmed
    
    def test_caption_max_length(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test caption max length validation (1000 chars)"""
        collection = test_collection_with_photos
        
        long_caption = "x" * 1001  # 1001 characters
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0/caption",
            json={"caption": long_caption},
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_caption_exactly_max_length(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test caption at exactly max length (1000 chars) - should succeed"""
        collection = test_collection_with_photos
        
        caption = "x" * 1000  # Exactly 1000 characters
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0/caption",
            json={"caption": caption},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["caption"]) == 1000


class TestCaptionValidation:
    """Test caption validation and error cases"""
    
    def test_caption_on_text_card_fails(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test that text cards cannot have captions"""
        collection = test_collection_with_photos
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/2/caption",  # Position 2 is text card
            json={"caption": "This should fail"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "not a photo" in response.json()["detail"].lower()
    
    def test_invalid_position_negative(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test invalid position (negative)"""
        collection = test_collection_with_photos
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/-1/caption",
            json={"caption": "Test"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid position" in response.json()["detail"]
    
    def test_invalid_position_too_large(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test invalid position (beyond items length)"""
        collection = test_collection_with_photos
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/999/caption",
            json={"caption": "Test"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid position" in response.json()["detail"]
    
    def test_missing_caption_field(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test request without caption field - should default to None"""
        collection = test_collection_with_photos
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0/caption",
            json={},
            headers=auth_headers
        )
        
        # Caption is optional with default None, so this should succeed
        assert response.status_code == 200
        data = response.json()
        assert data["caption"] is None


class TestCaptionPersistence:
    """Test that captions persist across operations"""
    
    def test_caption_persists_across_get(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test that caption changes persist when fetching collection"""
        collection = test_collection_with_photos
        
        # Add caption
        client.patch(
            f"/api/v1/collections/{collection.id}/items/0/caption",
            json={"caption": "Test caption"},
            headers=auth_headers
        )
        
        # Fetch collection
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["caption"] == "Test caption"
        assert data["items"][1]["caption"] == "Existing caption"  # Unchanged
        assert data["items"][3]["caption"] is None  # Normalized old item
    
    def test_caption_preserved_after_move(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test that caption is preserved when moving items"""
        collection = test_collection_with_photos
        
        # Add caption to first photo
        client.patch(
            f"/api/v1/collections/{collection.id}/items/0/caption",
            json={"caption": "Moving photo caption"},
            headers=auth_headers
        )
        
        # Move photo to end
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/move",
            json={"from_position": 0, "count": 1, "to_position": 3},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Fetch and verify caption preserved
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        
        data = response.json()
        # Photo that was at position 0 should now be at position 3 with caption intact
        assert data["items"][3]["caption"] == "Moving photo caption"
    
    def test_caption_removed_after_delete(self, client: TestClient, auth_headers: dict, test_collection_with_photos):
        """Test that deleting photo removes its caption"""
        collection = test_collection_with_photos
        
        # Add caption
        client.patch(
            f"/api/v1/collections/{collection.id}/items/0/caption",
            json={"caption": "Will be deleted"},
            headers=auth_headers
        )
        
        # Delete photo
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/delete",
            json={"position": 0, "count": 1},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify item is gone
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        
        data = response.json()
        assert data["item_count"] == 3  # One item deleted


class TestCaptionWithNewItems:
    """Test caption behavior when adding new items"""
    
    def test_new_items_get_caption_none(self, client: TestClient, auth_headers: dict, test_collection_with_photos, test_photos):
        """Test that new items added get caption=None by default"""
        collection = test_collection_with_photos
        photos = test_photos
        
        # Add new photo without caption
        response = client.post(
            f"/api/v1/collections/{collection.id}/items",
            json={
                "items": [
                    {"type": "photo", "photo_hothash": photos[3].hothash}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Fetch collection and check new item has caption=None
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        
        data = response.json()
        assert len(data["items"]) == 5
        assert data["items"][4]["caption"] is None  # New item
    
    def test_insert_with_caption(self, client: TestClient, auth_headers: dict, test_collection_with_photos, test_photos):
        """Test inserting item with caption specified"""
        collection = test_collection_with_photos
        photos = test_photos
        
        # Insert with caption
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/insert",
            json={
                "position": 1,
                "items": [
                    {"type": "photo", "photo_hothash": photos[3].hothash, "caption": "Inserted with caption"}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Fetch and verify caption was preserved
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        
        data = response.json()
        assert data["items"][1]["caption"] == "Inserted with caption"


class TestBackwardCompatibility:
    """Test backward compatibility with old items without caption field"""
    
    def test_get_collection_normalizes_caption(self, client: TestClient, auth_headers: dict, test_db_session: Session, test_user: User, test_photos):
        """Test that GET collection adds caption=None to old photo items"""
        photos = test_photos
        
        # Create collection with items WITHOUT caption field (simulating old data)
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Old Collection",
            items=[
                {"type": "photo", "photo_hothash": photos[0].hothash},  # No caption field
                {"type": "text", "text_card": {"title": "T", "body": "B"}},  # Text card
                {"type": "photo", "photo_hothash": photos[1].hothash, "visible": True},  # Has visible but no caption
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Fetch collection
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Photo items should have caption=None added
        assert data["items"][0]["caption"] is None
        assert data["items"][2]["caption"] is None
        # Text card should NOT have caption field
        assert "caption" not in data["items"][1]


class TestCollectionSpecificCaptions:
    """Test that captions are collection-specific"""
    
    def test_same_photo_different_captions_different_collections(
        self, 
        client: TestClient, 
        auth_headers: dict, 
        test_db_session: Session,
        test_user: User,
        test_photos
    ):
        """Test that same photo can have different captions in different collections"""
        photos = test_photos
        
        # Create two collections with same photo
        collection1 = PhotoCollection(
            user_id=test_user.id,
            name="Collection 1",
            items=[{"type": "photo", "photo_hothash": photos[0].hothash}]
        )
        collection2 = PhotoCollection(
            user_id=test_user.id,
            name="Collection 2",
            items=[{"type": "photo", "photo_hothash": photos[0].hothash}]
        )
        test_db_session.add_all([collection1, collection2])
        test_db_session.commit()
        
        # Set different captions in each collection
        client.patch(
            f"/api/v1/collections/{collection1.id}/items/0/caption",
            json={"caption": "Caption in collection 1"},
            headers=auth_headers
        )
        
        client.patch(
            f"/api/v1/collections/{collection2.id}/items/0/caption",
            json={"caption": "Caption in collection 2"},
            headers=auth_headers
        )
        
        # Verify captions are different
        response1 = client.get(f"/api/v1/collections/{collection1.id}", headers=auth_headers)
        response2 = client.get(f"/api/v1/collections/{collection2.id}", headers=auth_headers)
        
        assert response1.json()["items"][0]["caption"] == "Caption in collection 1"
        assert response2.json()["items"][0]["caption"] == "Caption in collection 2"
