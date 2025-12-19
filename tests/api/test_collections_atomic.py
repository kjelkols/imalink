"""
Tests for atomic Collections API operations (insert, move, delete)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.photo import Photo
from src.models.photo_collection import PhotoCollection


class TestAtomicCollectionsAPI:
    """Test atomic operations: insert, move, delete"""
    
    def test_insert_items_at_beginning(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test inserting items at position 0 (beginning)"""
        # Create photos
        photos = [
            Photo(user_id=test_user.id, hothash=f"hash{i}", width=100, height=100, hotpreview=b"x")
            for i in range(3)
        ]
        test_db_session.add_all(photos)
        
        # Create collection with initial items
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "photo", "photo_hothash": "hash0"},
                {"type": "photo", "photo_hothash": "hash1"},
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Insert at beginning
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/insert",
            json={
                "position": 0,
                "items": [
                    {"type": "photo", "photo_hothash": "hash2"}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 3
        assert data["affected_count"] == 1
        
        # Verify order
        test_db_session.refresh(collection)
        hothashes = [item["photo_hothash"] for item in collection.items]
        assert hothashes == ["hash2", "hash0", "hash1"]
    
    def test_insert_items_at_end(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test inserting items at end (append)"""
        photos = [
            Photo(user_id=test_user.id, hothash=f"hash{i}", width=100, height=100, hotpreview=b"x")
            for i in range(3)
        ]
        test_db_session.add_all(photos)
        
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "photo", "photo_hothash": "hash0"},
                {"type": "photo", "photo_hothash": "hash1"},
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Insert at end (position = len(items))
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/insert",
            json={
                "position": 2,
                "items": [
                    {"type": "photo", "photo_hothash": "hash2"}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        test_db_session.refresh(collection)
        hothashes = [item["photo_hothash"] for item in collection.items]
        assert hothashes == ["hash0", "hash1", "hash2"]
    
    def test_insert_items_middle(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test inserting items in middle"""
        photos = [
            Photo(user_id=test_user.id, hothash=f"hash{i}", width=100, height=100, hotpreview=b"x")
            for i in range(4)
        ]
        test_db_session.add_all(photos)
        
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "photo", "photo_hothash": "hash0"},
                {"type": "photo", "photo_hothash": "hash1"},
                {"type": "photo", "photo_hothash": "hash3"},
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Insert at position 2 (before hash3)
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/insert",
            json={
                "position": 2,
                "items": [
                    {"type": "photo", "photo_hothash": "hash2"}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        test_db_session.refresh(collection)
        hothashes = [item["photo_hothash"] for item in collection.items]
        assert hothashes == ["hash0", "hash1", "hash2", "hash3"]
    
    def test_insert_invalid_position(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test insert with invalid position returns 400"""
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "text", "text_card": {"title": "Test", "body": "Test"}}
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Try position beyond end
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/insert",
            json={
                "position": 5,
                "items": [
                    {"type": "text", "text_card": {"title": "New", "body": "New"}}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    def test_move_items_forward(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test moving items forward in collection"""
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "text", "text_card": {"title": "A", "body": "A"}},
                {"type": "text", "text_card": {"title": "B", "body": "B"}},
                {"type": "text", "text_card": {"title": "C", "body": "C"}},
                {"type": "text", "text_card": {"title": "D", "body": "D"}},
                {"type": "text", "text_card": {"title": "E", "body": "E"}},
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Move items at position 0-1 (A, B) to position 3
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/move",
            json={
                "from_position": 0,
                "count": 2,
                "to_position": 3
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        test_db_session.refresh(collection)
        titles = [item["text_card"]["title"] for item in collection.items]
        assert titles == ["C", "D", "E", "A", "B"]
    
    def test_move_items_backward(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test moving items backward in collection"""
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "text", "text_card": {"title": "A", "body": "A"}},
                {"type": "text", "text_card": {"title": "B", "body": "B"}},
                {"type": "text", "text_card": {"title": "C", "body": "C"}},
                {"type": "text", "text_card": {"title": "D", "body": "D"}},
                {"type": "text", "text_card": {"title": "E", "body": "E"}},
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Move items at position 3-4 (D, E) to position 1
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/move",
            json={
                "from_position": 3,
                "count": 2,
                "to_position": 1
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        test_db_session.refresh(collection)
        titles = [item["text_card"]["title"] for item in collection.items]
        assert titles == ["A", "D", "E", "B", "C"]
    
    def test_delete_items_range(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test deleting range of items"""
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "text", "text_card": {"title": "A", "body": "A"}},
                {"type": "text", "text_card": {"title": "B", "body": "B"}},
                {"type": "text", "text_card": {"title": "C", "body": "C"}},
                {"type": "text", "text_card": {"title": "D", "body": "D"}},
                {"type": "text", "text_card": {"title": "E", "body": "E"}},
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        # Delete items at position 1-2 (B, C)
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/delete",
            json={
                "position": 1,
                "count": 2
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 3
        assert data["affected_count"] == 2
        
        test_db_session.refresh(collection)
        titles = [item["text_card"]["title"] for item in collection.items]
        assert titles == ["A", "D", "E"]
    
    def test_delete_first_item(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test deleting first item"""
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "text", "text_card": {"title": "A", "body": "A"}},
                {"type": "text", "text_card": {"title": "B", "body": "B"}},
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/delete",
            json={"position": 0, "count": 1},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        test_db_session.refresh(collection)
        assert len(collection.items) == 1
        assert collection.items[0]["text_card"]["title"] == "B"
    
    def test_delete_last_item(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        test_db_session: Session
    ):
        """Test deleting last item"""
        collection = PhotoCollection(
            user_id=test_user.id,
            name="Test",
            items=[
                {"type": "text", "text_card": {"title": "A", "body": "A"}},
                {"type": "text", "text_card": {"title": "B", "body": "B"}},
            ]
        )
        test_db_session.add(collection)
        test_db_session.commit()
        
        response = client.post(
            f"/api/v1/collections/{collection.id}/items/delete",
            json={"position": 1, "count": 1},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        test_db_session.refresh(collection)
        assert len(collection.items) == 1
        assert collection.items[0]["text_card"]["title"] == "A"
