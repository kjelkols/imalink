# Frontend Collections Guide (with Text Cards)

## Overview

Collections støtter nå **mixed content** - du kan kombinere photos og text cards i samme collection. Dette gjør det mulig å lage:
- Fotoalbum med captions mellom bildene
- Portfolios med beskrivelser
- Client deliverables med forklarende tekst

## Data Structure

### Collection Response

```typescript
interface Collection {
  id: number;
  name: string;
  description: string | null;
  items: CollectionItem[];
  item_count: number;           // Total items (photos + text cards)
  photo_count: number;          // Only photos
  text_card_count: number;      // Only text cards
  cover_photo_hothash: string | null;  // First photo in items
  created_at: string;
  updated_at: string;
}
```

### Item Types

```typescript
type CollectionItem = PhotoItem | TextCardItem;

interface PhotoItem {
  type: 'photo';
  photo_hothash: string;
}

interface TextCardItem {
  type: 'text';
  text_card: {
    title: string;      // Max 200 chars
    body: string;       // Max 2000 chars, plain text
  };
}
```

**Important:** Position is **implicit from array index** - no separate position field needed!

## Common Operations

### 1. Create Empty Collection

```typescript
const response = await fetch('/api/v1/collections', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Summer Vacation 2024',
    description: 'Photos from Italy'
  })
});

const collection: Collection = await response.json();
```

### 2. Create Collection with Initial Photos

```typescript
const response = await fetch('/api/v1/collections', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Best Photos',
    hothashes: ['abc123...', 'def456...']  // Optional initial photos
  })
});
```

### 3. Add Items (Photos + Text Cards)

```typescript
const response = await fetch(`/api/v1/collections/${collectionId}/items`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    items: [
      { type: 'photo', photo_hothash: 'abc123...' },
      { 
        type: 'text', 
        text_card: { 
          title: 'Summer Memories', 
          body: 'These photos were taken in Rome...' 
        } 
      },
      { type: 'photo', photo_hothash: 'def456...' }
    ]
  })
});

const result = await response.json();
// { collection_id: 1, item_count: 52, photo_count: 45, affected_count: 3 }
```

**Notes:**
- Items are appended to end of collection
- Duplicate photos are automatically skipped
- Text cards are always added (no duplicate detection)

### 4. Drag-and-Drop Reordering

```typescript
// User drags item from index 2 to index 0
const newItems = [...collection.items];
const [movedItem] = newItems.splice(2, 1);  // Remove from old position
newItems.splice(0, 0, movedItem);           // Insert at new position

// Send entire array in new order
const response = await fetch(`/api/v1/collections/${collectionId}/items/reorder`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ items: newItems })
});

const result = await response.json();
// { collection_id: 1, item_count: 52, photo_count: 45, affected_count: 52 }
```

**Important:** You MUST include ALL items you want to keep. Items not in the list are removed!

### 5. Delete Item at Position

```typescript
const position = 2;  // Delete third item (0-based index)

const response = await fetch(`/api/v1/collections/${collectionId}/items/${position}`, {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});

const result = await response.json();
// { collection_id: 1, item_count: 51, photo_count: 45, affected_count: 1 }
```

### 6. Update Text Card

```typescript
const position = 1;  // Update second item (must be a text card)

const response = await fetch(`/api/v1/collections/${collectionId}/items/${position}`, {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'Updated Title',
    body: 'Updated body text...'
  })
});

// Returns 400 if position is a photo (not a text card)
```

### 7. Get Photos Only (No Text Cards)

```typescript
// If you only need photo metadata (no text cards)
const response = await fetch(`/api/v1/collections/${collectionId}/photos`, {
  headers: { 'Authorization': `Bearer ${token}` }
});

const photos: Photo[] = await response.json();  // Simple array, no pagination
```

**Note:** Returns ALL photos in collection order. No pagination - you always need the complete list.

## Frontend Implementation Examples

### React Collection Editor

```tsx
interface CollectionEditorProps {
  collectionId: number;
}

function CollectionEditor({ collectionId }: CollectionEditorProps) {
  const [collection, setCollection] = useState<Collection | null>(null);
  const [isReordering, setIsReordering] = useState(false);

  // Load collection
  useEffect(() => {
    fetch(`/api/v1/collections/${collectionId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(setCollection);
  }, [collectionId]);

  // Add text card
  const addTextCard = async (title: string, body: string) => {
    const response = await fetch(`/api/v1/collections/${collectionId}/items`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        items: [{ type: 'text', text_card: { title, body } }]
      })
    });
    
    // Reload collection to get updated items
    const updated = await fetch(`/api/v1/collections/${collectionId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    }).then(r => r.json());
    
    setCollection(updated);
  };

  // Delete item
  const deleteItem = async (position: number) => {
    await fetch(`/api/v1/collections/${collectionId}/items/${position}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    // Update local state
    setCollection(prev => ({
      ...prev!,
      items: prev!.items.filter((_, i) => i !== position),
      item_count: prev!.item_count - 1
    }));
  };

  // Drag-and-drop reorder
  const reorderItems = async (newItems: CollectionItem[]) => {
    setIsReordering(true);
    
    await fetch(`/api/v1/collections/${collectionId}/items/reorder`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ items: newItems })
    });
    
    setCollection(prev => ({ ...prev!, items: newItems }));
    setIsReordering(false);
  };

  if (!collection) return <div>Loading...</div>;

  return (
    <div>
      <h1>{collection.name}</h1>
      <p>{collection.description}</p>
      
      <div className="stats">
        <span>{collection.photo_count} photos</span>
        <span>{collection.text_card_count} text cards</span>
        <span>{collection.item_count} total items</span>
      </div>

      <DragDropContext onDragEnd={handleDragEnd}>
        <Droppable droppableId="collection">
          {(provided) => (
            <div {...provided.droppableProps} ref={provided.innerRef}>
              {collection.items.map((item, index) => (
                <Draggable key={index} draggableId={`item-${index}`} index={index}>
                  {(provided) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.draggableProps}
                      {...provided.dragHandleProps}
                    >
                      {item.type === 'photo' ? (
                        <PhotoThumbnail hothash={item.photo_hothash} />
                      ) : (
                        <TextCard 
                          title={item.text_card.title}
                          body={item.text_card.body}
                          onEdit={(title, body) => updateTextCard(index, title, body)}
                        />
                      )}
                      <button onClick={() => deleteItem(index)}>Delete</button>
                    </div>
                  )}
                </Draggable>
              ))}
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </DragDropContext>

      <button onClick={() => addTextCard('', '')}>Add Text Card</button>
    </div>
  );
}
```

### Display Collection as Gallery

```tsx
function CollectionGallery({ collectionId }: { collectionId: number }) {
  const [items, setItems] = useState<CollectionItem[]>([]);

  useEffect(() => {
    fetch(`/api/v1/collections/${collectionId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => setItems(data.items));
  }, [collectionId]);

  return (
    <div className="gallery">
      {items.map((item, index) => (
        <div key={index} className={`gallery-item ${item.type}`}>
          {item.type === 'photo' ? (
            <img 
              src={`/api/v1/photos/${item.photo_hothash}/hotpreview`} 
              alt="" 
            />
          ) : (
            <div className="text-card">
              <h3>{item.text_card.title}</h3>
              <p>{item.text_card.body}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

## Validation Rules

### Text Cards

```typescript
const MAX_TITLE_LENGTH = 200;
const MAX_BODY_LENGTH = 2000;

function validateTextCard(title: string, body: string): string | null {
  if (title.length > MAX_TITLE_LENGTH) {
    return `Title must be ${MAX_TITLE_LENGTH} characters or less`;
  }
  if (body.length > MAX_BODY_LENGTH) {
    return `Body must be ${MAX_BODY_LENGTH} characters or less`;
  }
  return null;  // Valid
}
```

### Photos

- Photos must exist in database
- Photos must belong to current user
- Duplicate photos are automatically skipped when adding

## Best Practices

### 1. Optimistic Updates

```typescript
// Update UI immediately, then sync with server
const deleteItemOptimistic = (position: number) => {
  const newItems = collection.items.filter((_, i) => i !== position);
  setCollection(prev => ({ ...prev!, items: newItems }));
  
  // Sync with server in background
  fetch(`/api/v1/collections/${collectionId}/items/${position}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  }).catch(err => {
    // Revert on error
    setCollection(originalCollection);
    showError('Failed to delete item');
  });
};
```

### 2. Batch Operations

```typescript
// Add multiple items at once (more efficient than multiple API calls)
const addMultiplePhotos = async (hothashes: string[]) => {
  const items = hothashes.map(hothash => ({
    type: 'photo' as const,
    photo_hothash: hothash
  }));
  
  await fetch(`/api/v1/collections/${collectionId}/items`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ items })
  });
};
```

### 3. Loading States

```typescript
const [isLoading, setIsLoading] = useState(false);

const reorderWithLoading = async (newItems: CollectionItem[]) => {
  setIsLoading(true);
  try {
    await fetch(`/api/v1/collections/${collectionId}/items/reorder`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ items: newItems })
    });
    setCollection(prev => ({ ...prev!, items: newItems }));
  } catch (error) {
    showError('Failed to reorder items');
  } finally {
    setIsLoading(false);
  }
};
```

## Migration from Old API

### Old API (Photo-Only)

```typescript
// ❌ Deprecated - these endpoints no longer exist
POST /api/v1/collections/{id}/photos
DELETE /api/v1/collections/{id}/photos
PUT /api/v1/collections/{id}/photos/reorder
```

### New API (Mixed Content)

```typescript
// ✅ Use these instead
POST /api/v1/collections/{id}/items       // Add photos + text cards
PUT /api/v1/collections/{id}/items/reorder // Reorder everything
DELETE /api/v1/collections/{id}/items/{position}  // Delete at index
```

### Migration Example

```typescript
// Old way (photo-only)
await fetch(`/api/v1/collections/${id}/photos`, {
  method: 'POST',
  body: JSON.stringify({ hothashes: ['abc', 'def'] })
});

// New way (photos as items)
await fetch(`/api/v1/collections/${id}/items`, {
  method: 'POST',
  body: JSON.stringify({
    items: [
      { type: 'photo', photo_hothash: 'abc' },
      { type: 'photo', photo_hothash: 'def' }
    ]
  })
});
```

## Error Handling

```typescript
try {
  const response = await fetch(`/api/v1/collections/${id}/items`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ items })
  });

  if (!response.ok) {
    if (response.status === 400) {
      const error = await response.json();
      console.error('Validation error:', error.detail);
      // Handle: invalid text card length, photo not found, etc.
    } else if (response.status === 404) {
      console.error('Collection not found');
    } else if (response.status === 403) {
      console.error('Not authorized to modify this collection');
    }
    return;
  }

  const result = await response.json();
  console.log(`Added ${result.affected_count} items`);
} catch (error) {
  console.error('Network error:', error);
}
```

## Summary

**Key Differences from Old API:**
1. **Mixed content** - combine photos and text cards
2. **No pagination** on `/photos` endpoint - always returns complete list
3. **Array index is position** - no separate position field
4. **Reorder replaces entire array** - perfect for drag-and-drop
5. **Old photo-only endpoints removed** - use `/items` endpoints instead

**Frontend Benefits:**
- Simple drag-and-drop implementation (just reorder array and POST)
- Flexible content mixing (photos + captions)
- Clean data structure (position = array index)
- Batch operations (add multiple items at once)
