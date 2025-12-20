"""
Test visibility toggle feature for collection items
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
        Photo(user_id=test_user.id, hothash=f"vhash{i}", width=100, height=100, hotpreview=b"x")
        for i in range(5)
    ]
    test_db_session.add_all(photos)
    test_db_session.commit()
    return photos


@pytest.fixture
def test_collection_with_items(test_db_session: Session, test_user: User, test_photos):
    """Create collection with mixed items for testing"""
    photos = test_photos
    
    collection = PhotoCollection(
        user_id=test_user.id,
        name="Visibility Test Collection",
        description="Testing visibility toggles",
        items=[
            {"type": "photo", "photo_hothash": photos[0].hothash, "visible": True},
            {"type": "photo", "photo_hothash": photos[1].hothash, "visible": True},
            {"type": "text", "text_card": {"title": "Title", "body": "Body"}, "visible": True},
            {"type": "photo", "photo_hothash": photos[2].hothash},  # No visible field (backward compat)
        ]
    )
    test_db_session.add(collection)
    test_db_session.commit()
    test_db_session.refresh(collection)
    
    return collection


class TestVisibilityToggle:
    """Test visibility toggle endpoint"""
    
    def test_toggle_item_to_invisible(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test hiding an item"""
        collection = test_collection_with_items
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0/visibility",
            json={"visible": False},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["collection_id"] == collection.id
        assert data["position"] == 0
        assert data["visible"] is False
        assert data["item_count"] == 4
        assert data["visible_count"] == 3  # 3 out of 4 visible
    
    def test_toggle_item_to_visible(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test showing a hidden item"""
        collection = test_collection_with_items
        
        # First hide it
        client.patch(
            f"/api/v1/collections/{collection.id}/items/1/visibility",
            json={"visible": False},
            headers=auth_headers
        )
        
        # Then show it again
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/1/visibility",
            json={"visible": True},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["visible"] is True
        assert data["visible_count"] == 4  # All visible again
    
    def test_toggle_text_card_visibility(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test hiding a text card"""
        collection = test_collection_with_items
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/2/visibility",
            json={"visible": False},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["position"] == 2
        assert data["visible"] is False
        assert data["visible_count"] == 3
    
    def test_invalid_position_negative(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test invalid position (negative)"""
        collection = test_collection_with_items
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/-1/visibility",
            json={"visible": False},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid position" in response.json()["detail"]
    
    def test_invalid_position_too_large(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test invalid position (beyond items length)"""
        collection = test_collection_with_items
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/999/visibility",
            json={"visible": False},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid position" in response.json()["detail"]
    
    def test_missing_visible_field(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test request without visible field"""
        collection = test_collection_with_items
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0/visibility",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_visible_type(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test invalid visible value (not boolean) - Pydantic coerces strings, so test with invalid type"""
        collection = test_collection_with_items
        
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0/visibility",
            json={"visible": 123},  # Integer instead of boolean
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_toggle_multiple_items(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test hiding multiple items sequentially"""
        collection = test_collection_with_items
        
        # Hide first three items
        for pos in [0, 1, 2]:
            response = client.patch(
                f"/api/v1/collections/{collection.id}/items/{pos}/visibility",
                json={"visible": False},
                headers=auth_headers
            )
            assert response.status_code == 200
        
        # Check final state
        response = client.patch(
            f"/api/v1/collections/{collection.id}/items/0/visibility",
            json={"visible": False},  # Already hidden, but that's ok
            headers=auth_headers
        )
        data = response.json()
        assert data["visible_count"] == 1  # Only last item visible
    
    def test_visibility_persists_across_get(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test that visibility changes persist when fetching collection"""
        collection = test_collection_with_items
        
        # Hide first item
        client.patch(
            f"/api/v1/collections/{collection.id}/items/0/visibility",
            json={"visible": False},
            headers=auth_headers
        )
        
        # Fetch collection
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["visible"] is False  # First item hidden
        assert data["items"][1]["visible"] is True   # Second item visible
        assert data["items"][3]["visible"] is True   # Fourth item normalized to visible


class TestBackwardCompatibility:
    """Test that old items without visible field work correctly"""
    
    def test_get_collection_normalizes_items(self, client: TestClient, auth_headers: dict, test_db_session: Session, test_user: User, test_photos):
        """Test that GET collection adds visible=true to old items"""
        photos = test_photos
        
        # Create collection with items WITHOUT visible field (simulating old data)
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Old Collection",
            items=[
                {"type": "photo", "photo_hothash": photos[0].hothash},  # No visible field
                {"type": "text", "text_card": {"title": "T", "body": "B"}},  # No visible field
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
        
        # All items should have visible=true added
        assert data["items"][0]["visible"] is True
        assert data["items"][1]["visible"] is True
    
    def test_new_items_get_visible_true(self, client: TestClient, auth_headers: dict, test_collection_with_items, test_photos):
        """Test that new items added get visible=true by default"""
        collection = test_collection_with_items
        photos = test_photos
        
        # Add new item without visible field
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
        
        # Fetch collection and check new item has visible=true
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        
        data = response.json()
        assert len(data["items"]) == 5
        assert data["items"][4]["visible"] is True  # New item


class TestVisibilityWithOtherOperations:
    """Test that visibility field is preserved across other operations"""
    
    def test_visibility_preserved_after_move(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test that visibility is preserved when moving items"""
        collection = test_collection_with_items
        
        # Hide first item
        client.patch(
            f"/api/v1/collections/{collection.id}/items/0/visibility",
            json={"visible": False},
            headers=auth_headers
        )
        
        # Move hidden item to end
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/move",
            json={"from_position": 0, "count": 1, "to_position": 3},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Fetch and verify visibility preserved
        response = client.get(
            f"/api/v1/collections/{collection.id}",
            headers=auth_headers
        )
        
        data = response.json()
        # Item that was at position 0 should now be at position 3 and still hidden
        assert data["items"][3]["visible"] is False
    
    def test_visibility_removed_after_delete(self, client: TestClient, auth_headers: dict, test_collection_with_items):
        """Test that deleting hidden item removes it completely"""
        collection = test_collection_with_items
        
        # Hide first item
        client.patch(
            f"/api/v1/collections/{collection.id}/items/0/visibility",
            json={"visible": False},
            headers=auth_headers
        )
        
        # Delete first item
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
