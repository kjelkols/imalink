# PhotoCollection System Documentation

> **⚠️ DEPRECATED DOCUMENTATION**  
> This document describes the original photo-only Collections architecture.  
> **Current Version:** Collections now support mixed content (photos + text cards) via `items` array.  
> **See:** `docs/API_REFERENCE.md` section "Photo Collections (Curated Photo Sets with Text Cards)"  
> **Date Archived:** December 18, 2025

## Overview

PhotoCollection is a static photo organization system that allows users to create named collections of photos identified by their hothashes. Unlike SavedPhotoSearch (dynamic, criteria-based), PhotoCollection maintains explicit lists of specific photos.

## Design Decisions

Based on user requirements:

1. **Flat Organization**: No hierarchy or folders - all collections are at the same level
2. **No Sharing Yet**: Collections are private to each user (sharing deferred to future)
3. **Array Order Matters**: Photos are stored in a JSON array with significant ordering
4. **Auto Cover Photo**: First photo in the array automatically serves as cover photo

## Architecture

### Database Schema

```python
class PhotoCollection:
    id: Integer (PK)
    user_id: Integer (FK to users)
    name: String(255)              # "Best of Italy 2024"
    description: Text              # Optional notes
    hothashes: JSON                # ["abc123...", "def456..."]
    created_at: DateTime
    updated_at: DateTime
```

Key points:
- **JSON Column**: hothashes stored as JSON array for flexibility and ordering
- **No Foreign Keys to Photos**: Independent list - photos can be deleted without breaking collection
- **User Ownership**: Each collection belongs to one user (user_id FK)
- **Timestamps**: Automatic tracking via TimestampMixin

### Relationships

```
User 1---* PhotoCollection
PhotoCollection *---0 Photo (via hothash lookup, no FK)
```

No direct FK to Photo table - this makes collections resilient to photo deletion.

## API Endpoints

### Collection CRUD

#### Create Collection
```http
POST /api/v1/collections
Content-Type: application/json

{
  "name": "Best of Italy 2024",
  "description": "Favorite shots from our Italy trip",
  "hothashes": ["abc123...", "def456..."]  // optional initial photos
}

Response: 201 Created
{
  "id": 1,
  "user_id": 42,
  "name": "Best of Italy 2024",
  "description": "Favorite shots from our Italy trip",
  "hothashes": ["abc123...", "def456..."],
  "photo_count": 2,
  "cover_photo_hothash": "abc123...",
  "created_at": "2024-11-02T10:30:00Z",
  "updated_at": "2024-11-02T10:30:00Z"
}
```

#### List Collections
```http
GET /api/v1/collections?skip=0&limit=100

Response: 200 OK
{
  "collections": [...],
  "total": 15
}
```

#### Get Collection
```http
GET /api/v1/collections/{collection_id}

Response: 200 OK (same as create response)
```

#### Update Collection
```http
PATCH /api/v1/collections/{collection_id}
Content-Type: application/json

{
  "name": "Italy Highlights 2024",      // optional
  "description": "Updated description"  // optional
}

Response: 200 OK (updated collection)
```

#### Delete Collection
```http
DELETE /api/v1/collections/{collection_id}

Response: 204 No Content
```

### Photo Management

#### Add Photos
```http
POST /api/v1/collections/{collection_id}/photos
Content-Type: application/json

{
  "hothashes": ["ghi789...", "jkl012..."]
}

Response: 200 OK
{
  "collection_id": 1,
  "photo_count": 4,           // new count after addition
  "affected_count": 2,        // number actually added
  "cover_photo_hothash": "abc123..."
}
```

Notes:
- Photos appended to end of array
- Duplicates automatically skipped
- Photos must exist and belong to user

#### Remove Photos
```http
DELETE /api/v1/collections/{collection_id}/photos
Content-Type: application/json

{
  "hothashes": ["def456..."]
}

Response: 200 OK
{
  "collection_id": 1,
  "photo_count": 3,
  "affected_count": 1,
  "cover_photo_hothash": "abc123..."
}
```

#### Reorder Photos
```http
PUT /api/v1/collections/{collection_id}/photos/reorder
Content-Type: application/json

{
  "hothashes": ["ghi789...", "abc123...", "jkl012..."]
}

Response: 200 OK
{
  "collection_id": 1,
  "photo_count": 3,
  "affected_count": 3,
  "cover_photo_hothash": "ghi789..."  // new first photo
}
```

Requirements:
- Must contain exactly same hothashes as current collection
- Only order changes, no additions/removals
- First photo becomes new cover photo

#### Get Collection Photos
```http
GET /api/v1/collections/{collection_id}/photos?skip=0&limit=100

Response: 200 OK
[
  {PhotoResponse},
  {PhotoResponse},
  ...
]
```

Returns full Photo objects in collection order.

#### Cleanup Invalid Photos
```http
POST /api/v1/collections/{collection_id}/cleanup

Response: 200 OK
{
  "collection_id": 1,
  "removed_count": 2
}
```

Removes hothashes that no longer exist in database.

## Business Logic

### PhotoCollectionService

Key methods:

1. **create_collection()**: Validates initial photos, checks for duplicate names
2. **add_photos()**: Validates photos exist and belong to user, skips duplicates
3. **remove_photos()**: Removes specified hothashes from array
4. **reorder_photos()**: Validates complete match of hothashes, updates order
5. **get_collection_photos()**: Fetches Photo objects, returns in collection order
6. **cleanup_collection()**: Removes invalid hothashes

### Validation Rules

- **Name**: Required, 1-255 characters, unique per user
- **Hothashes**: Must exist in Photo table
- **User Ownership**: Photos must belong to requesting user
- **Reorder**: Must contain exactly same hothashes (no more, no less)

## Model Methods

PhotoCollection provides convenience methods:

```python
# Properties
collection.photo_count            # Number of photos
collection.cover_photo_hothash    # First photo (or None)

# Photo management
collection.add_photos(hothashes)           # Returns count added
collection.remove_photos(hothashes)        # Returns count removed
collection.reorder_photos(hothashes)       # Returns success bool
collection.cleanup_invalid_hothashes(valid_set)  # Returns count removed
```

## Frontend Integration

### Saving Selection as Collection

Typical workflow:

```javascript
// User has selection in memory
const selection = {
  name: "My Selection",
  hothashes: ["abc...", "def...", "ghi..."]
};

// Convert to permanent collection
const response = await fetch('/api/v1/collections', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    name: selection.name,
    description: "Saved from selection",
    hothashes: selection.hothashes
  })
});

const collection = await response.json();
console.log(`Collection ${collection.id} created with ${collection.photo_count} photos`);
```

### Displaying Collection

```javascript
// Get collection metadata
const collection = await fetch(`/api/v1/collections/${collectionId}`).then(r => r.json());

// Display cover photo
const coverUrl = `/api/v1/photos/${collection.cover_photo_hothash}/hotpreview`;

// Get all photos in collection
const photos = await fetch(`/api/v1/collections/${collectionId}/photos`).then(r => r.json());
```

### Drag-and-Drop Reordering

```javascript
// User drags photos to new positions
const newOrder = updatedHothashes; // from UI state

await fetch(`/api/v1/collections/${collectionId}/photos/reorder`, {
  method: 'PUT',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({ hothashes: newOrder })
});
```

## Comparison with Other Systems

### PhotoCollection vs SavedPhotoSearch

| Feature | PhotoCollection | SavedPhotoSearch |
|---------|----------------|------------------|
| Type | Static list | Dynamic query |
| Content | Specific hothashes | Search criteria |
| Updates | Manual only | Auto-updates |
| Order | User-defined | Sort-based |
| Use Case | Albums, portfolios | Smart folders |

### PhotoCollection vs ImportSession

| Feature | PhotoCollection | ImportSession |
|---------|----------------|---------------|
| Purpose | User organization | Import tracking |
| Content | User-curated | Import history |
| Timing | Anytime | Import-time only |
| Photos | Cross-sessions | Single session |

### PhotoCollection vs Selection (temporary)

| Feature | PhotoCollection | Selection |
|---------|----------------|-----------|
| Storage | Database | Memory/UI state |
| Lifetime | Permanent | Session-based |
| Sharing | Future feature | N/A |
| Purpose | Albums | Working set |

## Database Cleanup

Since PhotoCollection stores hothashes without FK constraints:

```python
# Manual cleanup of invalid hothashes
service.cleanup_collection(collection_id, user_id)

# Or check which collections contain deleted photo
collections = repo.find_collections_containing_photo(user_id, hothash)
for collection in collections:
    collection.remove_photos([hothash])
```

## Future Enhancements (Not Implemented)

1. **Hierarchical Organization**: parent_id for nested folders
2. **Sharing**: share_mode, shared_with_user_ids
3. **Permissions**: read-only vs edit access
4. **User-Selectable Cover**: cover_photo_hothash column (nullable)
5. **Batch Operations**: merge collections, duplicate collection
6. **Smart Collections**: hybrid of static + dynamic (base criteria + manual additions)

## Performance Considerations

- **JSON Array**: SQLite JSON functions allow efficient querying
- **No JOINs**: Hothash lookup is fast (indexed primary key)
- **Pagination**: get_collection_photos() supports skip/limit
- **Eager Loading**: Can fetch photos in bulk via get_by_hothashes()

## Error Handling

Common errors:

- **409 Conflict**: Collection name already exists
- **404 Not Found**: Collection doesn't exist or doesn't belong to user
- **400 Bad Request**: 
  - Invalid hothashes (don't exist or don't belong to user)
  - Reorder hothashes don't match existing
  - Empty name or hothashes

## Testing Workflow

```bash
# 1. Create database
rm /mnt/c/temp/00imalink_data/imalink.db
export DISABLE_AUTH=True
uv run uvicorn src.main:app --reload

# 2. Import some photos
# (use frontend or API)

# 3. Create collection
curl -X POST http://localhost:8000/api/v1/collections \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Collection", "hothashes": ["hash1", "hash2"]}'

# 4. Add more photos
curl -X POST http://localhost:8000/api/v1/collections/1/photos \
  -H "Content-Type: application/json" \
  -d '{"hothashes": ["hash3"]}'

# 5. Reorder
curl -X PUT http://localhost:8000/api/v1/collections/1/photos/reorder \
  -H "Content-Type: application/json" \
  -d '{"hothashes": ["hash3", "hash1", "hash2"]}'

# 6. Get photos
curl http://localhost:8000/api/v1/collections/1/photos
```

## Summary

PhotoCollection provides a simple, robust system for static photo organization with:

- ✅ Flat organization (no hierarchy)
- ✅ User-private (no sharing yet)
- ✅ Ordered arrays (drag-and-drop ready)
- ✅ Auto cover photos (first in list)
- ✅ No FK constraints (resilient to photo deletion)
- ✅ Full CRUD + photo management API
- ✅ Validation and error handling
- ✅ Ready for frontend integration
