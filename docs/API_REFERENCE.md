# ImaLink API Reference v2.4 (PhotoCreateSchema Architecture)

**Base URL**: `http://localhost:8000/api/v1`  
**Authentication**: JWT Bearer tokens required for most endpoints (see individual endpoints for details)

**What's New in v2.4:**
- **PhotoCreateSchema Architecture**: All photo creation now uses PhotoCreateSchema from imalink-schemas package
- **Desktop App Flow**: Process images locally with imalink-core → Send PhotoCreateSchema to backend (fast, no upload)
- **Web Upload Flow**: Upload image → Backend forwards to imalink-core server → PhotoCreateSchema stored
- **Backend Never Processes Images**: All image processing delegated to imalink-core service
- **Security Enhancement**: user_id is NEVER in PhotoCreateSchema - backend sets it from JWT token
- **Shared Schema Package**: PhotoCreateSchema now in imalink-schemas v2.1.0+ (shared across all imalink modules)
- **Category Field**: User-defined photo categorization (e.g., "vacation", "work", "family")
- **Protected InputChannels**: Auto-created "Quick Channel" per user (cannot be deleted)

**Important Change in v2.4:** `POST /api/v1/photos/new-photo` has been removed. Use `POST /api/v1/photos/create` (primary) or `POST /api/v1/photos/register-image` (web upload) instead.

---

## 🔓 Visibility Levels

All photos and PhotoText documents have a `visibility` field with four possible values:

| Value | Who Can View | Use Case | Requires Auth |
|-------|-------------|----------|---------------|
| `private` | Owner only | Default, personal content | Yes |
| `space` | Space members | Shared workspaces (Phase 2 - not yet functional) | Yes |
| `authenticated` | All logged-in users | Community sharing, portfolio | Yes |
| `public` | Everyone including anonymous | Marketing, SEO, public gallery | No |

**Important Notes:**
- Default visibility for all new content: `private`
- `space` visibility is accepted by the API but treated as `private` in Phase 1
- Anonymous users can only access `public` content
- Authenticated users see: own content + `authenticated` content + `public` content
- Only the owner can change visibility or delete content

---

## 🔐 Authentication

### Register New User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepass123",
  "display_name": "John Doe"
}
```

**Response** (`201 Created`):
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "display_name": "John Doe",
  "is_active": true,
  "created_at": "2025-10-20T10:00:00Z",
  "updated_at": "2025-10-20T10:00:00Z",
  "default_author_id": 1
}
```

**Automatic Setup:**
Registration automatically creates:
1. **Default Author** - Author with same name as user, marked with `is_self=true`
2. **Default Input Channel** - Protected "Quick Channel" for immediate uploads
3. **User account** - With `default_author_id` pointing to the self-author

This allows immediate photo uploads without manual setup.

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "johndoe",
  "password": "securepass123"
}
```

**Response** (`200 OK`):
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "display_name": "John Doe",
    "is_active": true
  }
}
```

### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

### Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer <token>
```

---

## 👤 Users

### Get Current User Profile
```http
GET /api/v1/users/me
Authorization: Bearer <token>
```

### Update Current User Profile
```http
PUT /api/v1/users/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "display_name": "John Updated",
  "email": "john.new@example.com"
}
```

### Change Password
```http
POST /api/v1/users/me/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "oldpass123",
  "new_password": "newpass456"
}
```

### Delete Account
```http
DELETE /api/v1/users/me
Authorization: Bearer <token>
```

---

## 📸 Photos

All photo operations respect visibility settings. Authenticated users see their own photos plus `authenticated` and `public` photos from others. Anonymous users see only `public` photos.

**IMPORTANT for Frontend Integration:**
- All POST/PUT requests must include: `Content-Type: application/json`
- Most requests require: `Authorization: Bearer <token>` (except viewing public photos)
- Dates must be in ISO 8601 format: `"2025-10-15T14:30:00Z"`
- Base64 data can include data URL prefix or be raw: `"data:image/jpeg;base64,..."` or just the Base64 string
- New photos default to `visibility: "private"`

**Quick Start - Upload Your First Photo:**
```javascript
// 1. Get authentication token (do this once)
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'myuser', password: 'mypass' })
});
const { access_token } = await loginResponse.json();

// 2. Process image with imalink-core (desktop app with local instance)
const photoegg = await fetch('http://localhost:8001/v1/process', {
  method: 'POST',
  body: formDataWithImage  // Send image to local imalink-core
}).then(r => r.json());

// 3. Send PhotoEgg to backend
const response = await fetch('http://localhost:8000/api/v1/photos/photoegg', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    photo_egg: photoegg,
    input_channel_id: 5,  // Track input channel
    image_file: {
      filename: 'my_photo.jpg',
      file_path: '/path/to/my_photo.jpg',
      file_size: 2048576,
      file_format: 'JPEG'
    },
    rating: 0,
    visibility: 'private',
    category: 'vacation'  // Optional user category
  })
});

const result = await response.json();
console.log('Photo created:', result.hothash);
```

### List Photos
```http
GET /api/v1/photos?offset=0&limit=100
Authorization: Bearer <token>  # Optional - omit for anonymous access to public photos
```

**Query Parameters:**
- `offset` (int, default=0): Skip N photos
- `limit` (int, default=100, max=5000): Number of photos to return

**Access Control:**
- **Anonymous (no auth header)**: Only `public` photos returned
- **Authenticated**: Own photos + `authenticated` photos + `public` photos returned

**Response:**
```json
{
  "data": [
    {
      "hothash": "abc123def456...",
      "width": 4000,
      "height": 3000,
      "taken_at": "2025-10-15T14:30:00Z",
      "gps_latitude": 59.9139,
      "gps_longitude": 10.7522,
      "rating": 4,
      "visibility": "private",
      "author_id": 1,
      "stack_id": null,
      "created_at": "2025-10-20T10:00:00Z",
      "updated_at": "2025-10-20T10:00:00Z"
    }
  ],
  "meta": {
    "total": 250,
    "offset": 0,
    "limit": 100,
    "page": 1,
    "pages": 3
  }
}
```

### Search Photos
```http
POST /api/v1/photos/search
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "sunset beach",
  "rating_min": 3,
  "rating_max": 5,
  "taken_after": "2025-01-01T00:00:00Z",
  "taken_before": "2025-12-31T23:59:59Z",
  "author_id": 1,
  "offset": 0,
  "limit": 50
}
```

### Get Photo by Hash
```http
GET /api/v1/photos/{hothash}
Authorization: Bearer <token>  # Optional - omit for anonymous access to public photos
```

**Access Control:**
- **Anonymous**: Only `public` photos accessible (404 for others)
- **Authenticated**: Own photos + `authenticated` photos + `public` photos accessible
- **Owner**: Always can access own photos regardless of visibility

**Response:**
```json
{
  "hothash": "abc123def456...",
  "width": 4000,
  "height": 3000,
  "taken_at": "2025-10-15T14:30:00Z",
  "gps_latitude": 59.9139,
  "gps_longitude": 10.7522,
  "rating": 4,
  "visibility": "authenticated",
  "author_id": 1,
  "author": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  },
  "stack_id": null,
  "image_files": [
    {
      "id": 123,
      "filename": "IMG_001.jpg",
      "file_size": 2048576,
      "file_type": "jpeg"
    }
  ],
  "created_at": "2025-10-20T10:00:00Z",
  "updated_at": "2025-10-20T10:00:00Z"
}
```

### Update Photo Metadata
```http
PUT /api/v1/photos/{hothash}
Authorization: Bearer <token>  # Required - owner only
Content-Type: application/json

{
  "rating": 5,
  "visibility": "public",
  "author_id": 2,
  "gps_latitude": 60.0,
  "gps_longitude": 11.0
}
```

**Access Control:**
- Only the photo owner can update metadata
- All fields are optional
- Changing `visibility` immediately affects who can view the photo

**Visibility Field:**
- `"private"` - Only you can see it
- `"space"` - Space members (Phase 2 - not yet functional, treated as private)
- `"authenticated"` - All logged-in users can see it
- `"public"` - Everyone including anonymous users can see it
### Update Photo Time/Location Correction

**Endpoint:** `PATCH /api/v1/photos/{hothash}/timeloc-correction`

**Authentication:** Required (JWT token)

**Description:** Apply non-destructive corrections to photo timestamp and GPS location. Original EXIF data is preserved; corrections override display values only.

**Path Parameters:**
- `hothash` (string, required) - Photo's unique hotpreview hash

**Request Body:**
```json
{
  "taken_at": "2024-03-15T14:30:00Z",  // ISO 8601 format, optional
  "gps_latitude": 59.9139,              // decimal degrees, optional
  "gps_longitude": 10.7522,             // decimal degrees, optional
  "correction_reason": "Camera clock was 2 hours ahead"  // optional, user note
}
```

**Special Behavior - Restore from EXIF:**
Send `null` as entire request body to restore all values from original EXIF:
```json
null
```
This will:
1. Delete the `timeloc_correction` JSON (set to `null`)
2. Re-parse `ImageFile.exif_dict` for original values
3. Update `Photo.taken_at`, `gps_latitude`, `gps_longitude` with EXIF values (or `null`/`0` if not found)

**Response (200 OK):**
```json
{
  "hothash": "abc123...",
  "taken_at": "2024-03-15T14:30:00Z",
  "gps_latitude": 59.9139,
  "gps_longitude": 10.7522,
  "timeloc_correction": {
    "taken_at": "2024-03-15T14:30:00Z",
    "gps_latitude": 59.9139,
    "gps_longitude": 10.7522,
    "correction_reason": "Camera clock was 2 hours ahead",
    "corrected_at": "2024-10-22T10:15:00Z",
    "corrected_by": 1
  }
}
```

**Response after null request (200 OK):**
```json
{
  "hothash": "abc123...",
  "taken_at": "2024-03-15T12:30:00Z",  // restored from EXIF
  "gps_latitude": 59.9139,              // restored from EXIF
  "gps_longitude": 10.7522,             // restored from EXIF
  "timeloc_correction": null            // correction removed
}
```

**Error Responses:**
- `404 Not Found` - Photo not found
- `401 Unauthorized` - No valid token
- `422 Unprocessable Entity` - Invalid data format

**Implementation Notes:**
1. **First correction**: `timeloc_correction` is created with provided fields + metadata
2. **Update correction**: Existing `timeloc_correction` is updated (merge with new fields)
3. **Restore from EXIF**: `timeloc_correction` set to `null`, Photo fields restored from `ImageFile.exif_dict`

**Database Schema:**
```python
# Photo model fields affected:
taken_at: datetime | None           # Display value (EXIF or corrected)
gps_latitude: float | None          # Display value (EXIF or corrected)
gps_longitude: float | None         # Display value (EXIF or corrected)
timeloc_correction: JSON | None     # Correction metadata + values

# timeloc_correction JSON structure:
{
  "taken_at": "2024-03-15T14:30:00Z",
  "gps_latitude": 59.9139,
  "gps_longitude": 10.7522,
  "correction_reason": "User explanation",
  "corrected_at": "2024-10-22T10:15:00Z",  # auto-set
  "corrected_by": 1                         # user_id, auto-set
}
```

**Backend Logic:**

```python
# Scenario 1: NULL request - Restore from EXIF
if request_body is None:
    photo.timeloc_correction = None
    photo.taken_at = parse_exif_datetime(image_file.exif_dict) or None
    photo.gps_latitude = parse_exif_gps_lat(image_file.exif_dict) or 0.0
    photo.gps_longitude = parse_exif_gps_lon(image_file.exif_dict) or 0.0

# Scenario 2: First correction or update
else:
    correction = photo.timeloc_correction or {}
    if request.taken_at is not None:
        correction["taken_at"] = request.taken_at
        photo.taken_at = request.taken_at
    if request.gps_latitude is not None:
        correction["gps_latitude"] = request.gps_latitude
        photo.gps_latitude = request.gps_latitude
    if request.gps_longitude is not None:
        correction["gps_longitude"] = request.gps_longitude
        photo.gps_longitude = request.gps_longitude
    if request.correction_reason:
        correction["correction_reason"] = request.correction_reason
    
    correction["corrected_at"] = datetime.utcnow()
    correction["corrected_by"] = current_user.id
    photo.timeloc_correction = correction
```

---

### Update Photo View Correction

**Endpoint:** `PATCH /api/v1/photos/{hothash}/view-correction`

**Authentication:** Required (JWT token)

**Description:** Store frontend display preferences for rotation, cropping, and exposure adjustments. **No server-side image processing** - these are rendering hints for clients only.

**Path Parameters:**
- `hothash` (string, required) - Photo's unique hotpreview hash

**Request Body:**
```json
{
  "rotation": 90,           // 0, 90, 180, 270 degrees, optional
  "relative_crop": {        // Normalized coordinates 0.0-1.0, optional
    "x": 0.1,               // Left edge (0.0 = left, 1.0 = right)
    "y": 0.1,               // Top edge (0.0 = top, 1.0 = bottom)
    "width": 0.8,           // Width (0.0-1.0)
    "height": 0.8           // Height (0.0-1.0)
  },
  "exposure_adjust": 0.5    // -2.0 to +2.0, optional
}
```

**Validation Rules:**
- `rotation`: Must be 0, 90, 180, or 270
- `relative_crop.x`: 0.0 ≤ x < 1.0
- `relative_crop.y`: 0.0 ≤ y < 1.0
- `relative_crop.width`: 0.0 < width ≤ 1.0
- `relative_crop.height`: 0.0 < height ≤ 1.0
- `x + width ≤ 1.0` (crop must stay within image bounds)
- `y + height ≤ 1.0` (crop must stay within image bounds)
- `exposure_adjust`: -2.0 ≤ value ≤ 2.0

**Special Behavior - Reset to Defaults:**
Send `null` as entire request body to remove all view corrections:
```json
null
```

**Response (200 OK):**
```json
{
  "hothash": "abc123...",
  "view_correction": {
    "rotation": 90,
    "relative_crop": {
      "x": 0.1,
      "y": 0.1,
      "width": 0.8,
      "height": 0.8
    },
    "exposure_adjust": 0.5,
    "corrected_at": "2024-10-22T10:20:00Z",
    "corrected_by": 1
  }
}
```

**Response after null request (200 OK):**
```json
{
  "hothash": "abc123...",
  "view_correction": null
}
```

**Error Responses:**
- `404 Not Found` - Photo not found
- `401 Unauthorized` - No valid token
- `422 Unprocessable Entity` - Invalid data format or out-of-range values

**Implementation Notes:**
1. Backend **only stores** the JSON - no image processing
2. Frontend applies these settings during rendering
3. Relative crop uses normalized coordinates for resolution independence
4. `null` request removes all view corrections

**Database Schema:**
```python
# Photo model field:
view_correction: JSON | None

# view_correction JSON structure:
{
  "rotation": 90,
  "relative_crop": {
    "x": 0.1,
    "y": 0.1,
    "width": 0.8,
    "height": 0.8
  },
  "exposure_adjust": 0.5,
  "corrected_at": "2024-10-22T10:20:00Z",  # auto-set
  "corrected_by": 1                         # user_id, auto-set
}
```

**Frontend Rendering Example:**

```python
# Apply view corrections to image display
if photo.view_correction:
    vc = photo.view_correction
    
    # 1. Apply rotation
    if vc.get("rotation"):
        image = image.rotate(vc["rotation"])
    
    # 2. Apply relative crop (convert to pixel coordinates)
    if crop := vc.get("relative_crop"):
        width, height = image.size
        x = int(crop["x"] * width)
        y = int(crop["y"] * height)
        w = int(crop["width"] * width)
        h = int(crop["height"] * height)
        image = image.crop((x, y, x + w, y + h))
    
    # 3. Apply exposure adjustment
    if exp := vc.get("exposure_adjust"):
        enhancer = ImageEnhance.Brightness(image)
        # exposure -2.0 to +2.0 maps to brightness 0.5 to 1.5
        brightness = 1.0 + (exp * 0.25)
        image = enhancer.enhance(brightness)
```

**Backend Logic:**

```python
# Scenario 1: NULL request - Remove corrections
if request_body is None:
    photo.view_correction = None

# Scenario 2: Update corrections
else:
    correction = photo.view_correction or {}
    
    if request.rotation is not None:
        if request.rotation not in [0, 90, 180, 270]:
            raise ValidationError("rotation must be 0, 90, 180, or 270")
        correction["rotation"] = request.rotation
    
    if request.relative_crop is not None:
        crop = request.relative_crop
        # Validate bounds
        if not (0 <= crop.x < 1 and 0 <= crop.y < 1):
            raise ValidationError("crop x,y must be 0-1")
        if not (0 < crop.width <= 1 and 0 < crop.height <= 1):
            raise ValidationError("crop width,height must be 0-1")
        if crop.x + crop.width > 1 or crop.y + crop.height > 1:
            raise ValidationError("crop exceeds image bounds")
        correction["relative_crop"] = crop
    
    if request.exposure_adjust is not None:
        if not (-2.0 <= request.exposure_adjust <= 2.0):
            raise ValidationError("exposure_adjust must be -2.0 to +2.0")
        correction["exposure_adjust"] = request.exposure_adjust
    
    correction["corrected_at"] = datetime.utcnow()
    correction["corrected_by"] = current_user.id
    photo.view_correction = correction
```

---

## 🏷️ Photo Tags

Photo tags enable flexible organization and search using user-defined keywords. Tags are user-scoped (each user has their own vocabulary) and support many-to-many relationships with photos.

### List All Tags

**Endpoint:** `GET /api/v1/tags`

**Authentication:** Required (JWT token)

**Description:** Get all tags for current user with photo counts.

**Query Parameters:**
- `sort_by` (string, optional) - Sort order: `name` (default), `count`, `created_at`
- `order` (string, optional) - Sort direction: `asc` (default), `desc`

**Response (200 OK):**
```json
{
  "tags": [
    {
      "id": 1,
      "name": "landscape",
      "photo_count": 245,
      "created_at": "2024-10-20T10:00:00Z",
      "updated_at": "2024-10-22T15:30:00Z"
    },
    {
      "id": 2,
      "name": "sunset",
      "photo_count": 89,
      "created_at": "2024-10-20T11:30:00Z",
      "updated_at": "2024-10-22T14:20:00Z"
    }
  ],
  "total": 2
}
```

**Implementation Notes:**
- Returns only tags belonging to current user
- `photo_count` is calculated via COUNT on `photo_tags` association table
- Tags without photos are still included (count = 0)

---

### Tag Autocomplete

**Endpoint:** `GET /api/v1/tags/autocomplete`

**Authentication:** Required (JWT token)

**Description:** Get tag suggestions for autocomplete while typing. Fast prefix-matching search.

**Query Parameters:**
- `q` (string, required) - Search query (minimum 1 character)
- `limit` (integer, optional) - Max results (default: 10, max: 50)

**Response (200 OK):**
```json
{
  "suggestions": [
    {
      "id": 1,
      "name": "landscape",
      "photo_count": 245
    },
    {
      "id": 15,
      "name": "land",
      "photo_count": 12
    }
  ]
}
```

**Example Usage:**
```http
GET /api/v1/tags/autocomplete?q=land&limit=5
```

**Implementation Notes:**
- Case-insensitive prefix matching: `q=land` matches "landscape", "landmark", "land"
- Results ordered by photo count (descending) for most relevant suggestions
- Only returns user's own tags

---

### Add Tags to Photo

**Endpoint:** `POST /api/v1/photos/{hothash}/tags`

**Authentication:** Required (JWT token)

**Description:** Add one or more tags to a photo. Tags are created automatically if they don't exist. Duplicate tags are silently ignored.

**Path Parameters:**
- `hothash` (string, required) - Photo's unique hotpreview hash

**Request Body:**
```json
{
  "tags": ["landscape", "sunset", "norway"]
}
```

**Alternative (single tag):**
```json
{
  "tags": ["vacation"]
}
```

**Response (200 OK):**
```json
{
  "hothash": "abc123...",
  "tags": [
    {
      "id": 1,
      "name": "landscape"
    },
    {
      "id": 2,
      "name": "sunset"
    },
    {
      "id": 3,
      "name": "norway"
    }
  ],
  "added": 3,
  "skipped": 0
}
```

**Response with duplicates (200 OK):**
```json
{
  "hothash": "abc123...",
  "tags": [
    {
      "id": 1,
      "name": "landscape"
    },
    {
      "id": 2,
      "name": "sunset"
    }
  ],
  "added": 1,
  "skipped": 1,
  "message": "Tag 'landscape' was already applied to this photo"
}
```

**Error Responses:**
- `404 Not Found` - Photo not found
- `401 Unauthorized` - No valid token
- `422 Unprocessable Entity` - Invalid tag format

**Validation Rules:**
- Tag names are normalized to lowercase
- Tag names must be 1-50 characters
- Only alphanumeric, space, hyphen, underscore allowed
- Leading/trailing whitespace is trimmed

**Implementation Notes:**
1. Check if tags exist in user's tag vocabulary
2. Create new tags if needed (user-scoped)
3. Create associations in `photo_tags` table
4. Skip if association already exists (no error)
5. Return updated list of all tags for photo

---

### Remove Tag from Photo

**Endpoint:** `DELETE /api/v1/photos/{hothash}/tags/{tag_name}`

**Authentication:** Required (JWT token)

**Description:** Remove a specific tag from a photo. The tag itself remains in the database for reuse.

**Path Parameters:**
- `hothash` (string, required) - Photo's unique hotpreview hash
- `tag_name` (string, required) - Tag name to remove (case-insensitive)

**Response (200 OK):**
```json
{
  "hothash": "abc123...",
  "removed_tag": "landscape",
  "remaining_tags": [
    {
      "id": 2,
      "name": "sunset"
    },
    {
      "id": 3,
      "name": "norway"
    }
  ]
}
```

**Error Responses:**
- `404 Not Found` - Photo or tag not found
- `401 Unauthorized` - No valid token

**Implementation Notes:**
- Only removes association in `photo_tags` table
- Tag remains in `tags` table (can be reused)
- Case-insensitive tag name matching

---

### Delete Tag Completely

**Endpoint:** `DELETE /api/v1/tags/{tag_id}`

**Authentication:** Required (JWT token)

**Description:** Permanently delete a tag and remove it from all photos. Use with caution.

**Path Parameters:**
- `tag_id` (integer, required) - Tag ID to delete

**Response (200 OK):**
```json
{
  "deleted_tag": "landscape",
  "photos_affected": 245,
  "message": "Tag 'landscape' deleted from 245 photos"
}
```

**Error Responses:**
- `404 Not Found` - Tag not found or doesn't belong to user
- `401 Unauthorized` - No valid token

**Implementation Notes:**
- Cascade deletes all `photo_tags` associations
- Only allows deletion of user's own tags

---

### Rename Tag

**Endpoint:** `PUT /api/v1/tags/{tag_id}`

**Authentication:** Required (JWT token)

**Description:** Rename a tag. The new name applies to all photos using this tag.

**Path Parameters:**
- `tag_id` (integer, required) - Tag ID to rename

**Request Body:**
```json
{
  "new_name": "seascape"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "old_name": "landscape",
  "new_name": "seascape",
  "photo_count": 245,
  "updated_at": "2024-10-22T16:45:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Tag not found or doesn't belong to user
- `409 Conflict` - Tag with new name already exists for user
- `401 Unauthorized` - No valid token
- `422 Unprocessable Entity` - Invalid tag name format

---

### Search Photos by Tags

**Endpoint:** `GET /api/v1/photos`

**Authentication:** Required (JWT token)

**Description:** Search photos using tag filters. Supports AND/OR logic for multiple tags.

**Query Parameters:**
- `tags` (string, optional) - Comma-separated tag names: `tags=landscape,sunset`
- `tag_logic` (string, optional) - Logic operator: `AND` (default) or `OR`
- `offset` (integer, optional) - Pagination offset (default: 0)
- `limit` (integer, optional) - Results per page (default: 50, max: 500)

**Example - Photos with ALL specified tags:**
```http
GET /api/v1/photos?tags=landscape,norway&tag_logic=AND
```

**Example - Photos with ANY specified tag:**
```http
GET /api/v1/photos?tags=sunset,sunrise&tag_logic=OR
```

**Response (200 OK):**
```json
{
  "items": [
    {
      "hothash": "abc123...",
      "tags": [
        {"id": 1, "name": "landscape"},
        {"id": 3, "name": "norway"}
      ],
      "taken_at": "2024-08-15T18:30:00Z",
      ...
    }
  ],
  "total": 42,
  "offset": 0,
  "limit": 50
}
```

**Implementation Notes:**

**AND Logic (default):**
```sql
-- Photo must have ALL specified tags
SELECT p.* FROM photos p
INNER JOIN photo_tags pt1 ON p.hothash = pt1.photo_hothash
INNER JOIN tags t1 ON pt1.tag_id = t1.id AND t1.name = 'landscape'
INNER JOIN photo_tags pt2 ON p.hothash = pt2.photo_hothash  
INNER JOIN tags t2 ON pt2.tag_id = t2.id AND t2.name = 'norway'
WHERE p.user_id = ?
```

**OR Logic:**
```sql
-- Photo must have AT LEAST ONE specified tag
SELECT DISTINCT p.* FROM photos p
INNER JOIN photo_tags pt ON p.hothash = pt.photo_hothash
INNER JOIN tags t ON pt.tag_id = t.id
WHERE p.user_id = ? AND t.name IN ('sunset', 'sunrise')
```

---

### Database Schema

```python
# models/tag.py
class Tag(Base, TimestampMixin):
    """User-scoped tag for photo categorization"""
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    name = Column(String(50), nullable=False)  # Lowercase normalized
    
    # Unique constraint per user
    __table_args__ = (
        Index('idx_user_tag', 'user_id', 'name', unique=True),
    )
    
    user = relationship("User", back_populates="tags")
    photos = relationship("Photo", secondary="photo_tags", back_populates="tags")

# Association table (many-to-many)
class PhotoTag(Base):
    """Association between Photos and Tags"""
    __tablename__ = "photo_tags"
    
    photo_hothash = Column(String(64), ForeignKey('photos.hothash'), 
                           primary_key=True, index=True)
    tag_id = Column(Integer, ForeignKey('tags.id'), 
                    primary_key=True, index=True)
    tagged_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite index for reverse lookup
    __table_args__ = (
        Index('idx_tag_photos', 'tag_id', 'photo_hothash'),
    )

# Photo model addition
class Photo(Base):
    # ... existing fields ...
    tags = relationship("Tag", secondary="photo_tags", back_populates="photos")
```

**Key Design Decisions:**
1. **User-scoped**: `(user_id, name)` unique constraint prevents duplicates per user
2. **Normalized**: Tag strings stored once, reused across photos (efficient)
3. **Case-insensitive**: All tag names converted to lowercase
4. **Timestamped**: `tagged_at` tracks when tag was applied to photo
5. **Indexed**: Fast lookups via `idx_user_tag` and `idx_tag_photos`

### Delete Photo
```http
DELETE /api/v1/photos/{hothash}
Authorization: Bearer <token>
```

**Note:** Deletes the Photo record and all associated ImageFiles.

### Get Photo Hotpreview
```http
GET /api/v1/photos/{hothash}/hotpreview
Authorization: Bearer <token>
```

**Returns:** JPEG image (150x150px thumbnail) as binary data

**Response Headers:**
```
Content-Type: image/jpeg
Content-Disposition: inline; filename=hotpreview_{hothash}.jpg
Cache-Control: public, max-age=3600
```

### Upload/Update Photo Coldpreview
```http
PUT /api/v1/photos/{hothash}/coldpreview
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <image file>
```

**Description:** Upload or update medium-size preview (800-1200px) for a photo.

**Response:**
```json
{
  "status": "success",
  "message": "Coldpreview uploaded successfully",
  "data": {
    "hothash": "abc123def456...",
    "coldpreview_path": "/path/to/coldpreview.jpg"
  }
}
```

### Get Photo Coldpreview
```http
GET /api/v1/photos/{hothash}/coldpreview?width=800&height=600
Authorization: Bearer <token>
```

**Query Parameters:**
- `width` (int, optional, 100-2000): Target width for dynamic resizing
- `height` (int, optional, 100-2000): Target height for dynamic resizing

**Returns:** JPEG image (medium-size preview) as binary data

**Response Headers:**
```
Content-Type: image/jpeg
Content-Disposition: inline; filename=coldpreview_{hothash}.jpg
Cache-Control: public, max-age=3600
```

### Delete Photo Coldpreview
```http
DELETE /api/v1/photos/{hothash}/coldpreview
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "Coldpreview deleted successfully"
}
```

### Get Photo's Stack
```http
GET /api/v1/photos/{hothash}/stack
Authorization: Bearer <token>
```

**Description:** Get the PhotoStack containing this photo (if any).

**Response:** PhotoStackSummary object or `null` if photo doesn't belong to a stack.

```json
{
  "id": 5,
  "name": "Sunset Series",
  "stack_type": "burst",
  "photo_count": 8,
  "cover_photo_hothash": "abc123def456...",
  "created_at": "2025-10-20T10:00:00Z"
}
```

### Create Photo from PhotoCreateSchema (Desktop App - PRIMARY METHOD)
```http
POST /api/v1/photos/create
Authorization: Bearer <token>
Content-Type: application/json

{
  "photo_create_schema": {
    "hothash": "a6317d064f4d83ff419b9deaf35ba537ff6a31e6722d7df66510d8a3b5d2e281",
    "hotpreview_base64": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAUDBAQEAwUE...",
    "coldpreview_base64": null,
    "width": 4000,
    "height": 3000,
    "taken_at": "2025-10-15T14:30:00Z",
    "gps_latitude": 59.9139,
    "gps_longitude": 10.7522,
    "exif_dict": {
      "camera_make": "Canon",
      "camera_model": "EOS R5",
      "iso": 400,
      "aperture": 2.8,
      "shutter_speed": "1/250",
      "focal_length": 50,
      "lens_model": "RF 50mm F1.2 L USM",
      "lens_make": "Canon",
      "has_gps": true
    },
    "image_file_list": [
      {
        "filename": "IMG_001.jpg",
        "file_size": 8234567
      }
    ],
    "rating": 0,
    "visibility": "private",
    "input_channel_id": 5,
    "author_id": null,
    "category": null
  },
  "tags": []
}
```

**Description:** Create a Photo from a pre-processed PhotoCreateSchema. This is the **primary method** for desktop applications. The desktop app processes images locally with imalink-core and sends only metadata to the server.

**Architecture:**
1. Desktop app → Local imalink-core → PhotoCreateSchema JSON
2. Desktop app → Backend POST /photos/create → Photo created
3. Original files remain on user's computer
4. **user_id is NOT in PhotoCreateSchema** - backend sets it from JWT token (security)

**Required Fields:**
- `photo_create_schema` (PhotoCreateSchema): Pre-processed photo metadata from imalink-core
  - `hothash` (string): SHA256 hash of hotpreview (unique identifier)
  - `hotpreview_base64` (string): Base64-encoded JPEG preview (~200px)
  - `width` (integer): Original image width
  - `height` (integer): Original image height
  - `image_file_list` (array): List of source files
    - `filename` (string): Original filename
    - `file_size` (integer): File size in bytes (default: 0)
- `tags` (array): Tag names to associate with photo (default: [])

**Optional Fields in PhotoCreateSchema:**
- `exif_dict` (object): Complete EXIF metadata (flexible JSON)
  - `camera_make`, `camera_model`, `iso`, `aperture`, `shutter_speed`, `focal_length`, etc.
- `taken_at` (datetime): When photo was taken (indexed for timeline queries)
- `gps_latitude`, `gps_longitude` (float): GPS coordinates (indexed for map queries)
- `coldpreview_base64` (string): Optional larger preview
- `rating` (integer): 0-5 star rating (default: 0)
- `visibility` (string): private|space|authenticated|public (default: private)
- `input_channel_id` (integer): Input channel ID (defaults to user's "Quick Channel")
- `author_id` (integer): Photographer ID (defaults to user's self-author)
- `category` (string): User-defined category (e.g., "vacation", "work")
- `stack_id` (integer): Photo stack ID for related images
- `timeloc_correction` (object): Time/location corrections
- `view_correction` (object): Visual adjustments

**Automatic Defaults:**
- If `input_channel_id` is not provided, uses the user's protected "Quick Channel"
- If `author_id` is not provided, uses the user's default self-author (created at registration)
- This allows immediate photo uploads without manual setup

**PhotoCreateSchema Metadata:**
All EXIF metadata is stored in flexible `exif_dict` JSON field. Common fields:
- `gps_latitude`, `gps_longitude` (float): GPS coordinates
- `has_gps` (boolean): GPS availability flag
- `iso`, `aperture`, `focal_length` (number): Camera settings
- `shutter_speed` (string): Shutter speed (e.g., "1/250")
- `lens_model`, `lens_make` (string): Lens info

**Response** (`201 Created`):
```json
{
  "id": 123,
  "hothash": "a6317d064f4d83ff419b9deaf35ba537...",
  "user_id": 1,
  "width": 4000,
  "height": 3000,
  "taken_at": "2025-10-15T14:30:00Z",
  "gps_latitude": 59.9139,
  "gps_longitude": 10.7522,
  "rating": 0,
  "category": null,
  "visibility": "private",
  "created_at": "2025-11-12T10:00:00Z",
  "updated_at": "2025-11-12T10:00:00Z"
}
```

**Error Responses:**
- `409 Conflict` - Photo with this hothash already exists (duplicate)
- `400 Bad Request` - Invalid PhotoCreateSchema or validation error
- `422 Unprocessable Entity` - Invalid field values

### Register Image via Web Upload (Web App - CONVENIENCE)
```http
POST /api/v1/photos/register-image?rating=4&visibility=private
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary image data>
```

**Description:** Quick web upload for when user doesn't have desktop app. Backend forwards image to imalink-core server for processing, then stores the PhotoCreateSchema.

**⚠️ NOT RECOMMENDED FOR:** Batch imports (use desktop app with local imalink-core instead)

**Security:** Backend sets `user_id` from JWT token - it is NOT in PhotoCreateSchema.

**Query Parameters:**
- `input_channel_id` (integer, optional): Input channel (defaults to "Quick Channel" if not provided)
- `rating` (integer, optional): 0-5 star rating
- `visibility` (string, optional): private|space|authenticated|public
- `author_id` (integer, optional): Photographer ID (defaults to user's self-author if not provided)
- `coldpreview_size` (integer, optional): Size for larger preview (e.g., 2560)

**Request Body:**
- `file` (binary): Image file (JPEG, PNG, etc.)

**Flow:**
1. Web app uploads file → Backend
2. Backend → imalink-core server (https://core.trollfjell.com)
3. imalink-core → PhotoCreateSchema
4. Backend stores photo metadata
5. user_id set from JWT token (not in PhotoCreateSchema)

**Response** (`201 Created`): Same as POST /photos/create endpoint

**Error Responses:**
- `400 Bad Request` - Invalid image or imalink-core processing failed
- `503 Service Unavailable` - imalink-core service unavailable
- `422 Unprocessable Entity` - Missing file

### Add ImageFile to Existing Photo
```http
POST /api/v1/photos/{hothash}/files
Authorization: Bearer <token>
Content-Type: application/json

{
  "filename": "IMG_001.CR2",
  "file_size": 25000000,
  "input_channel_id": 5,
  "imported_info": {
    "original_path": "/path/to/original.CR2"
  },
  "local_storage_info": {
    "path": "/storage/photos/IMG_001.CR2"
  }
}
```

**Description:** Add a companion ImageFile (e.g., RAW, different resolution) to an existing Photo. No hotpreview needed since the Photo already exists.

**Path Parameters:**
- `hothash` (string): The 64-character hash of the existing Photo

**Required Fields:**
- `filename` (string): Filename with extension

**Optional Fields:**
- `file_size` (integer): File size in bytes
- `input_channel_id` (integer): ID of input channel
- `imported_info` (object): Import context
- `local_storage_info` (object): Local storage metadata
- `cloud_storage_info` (object): Cloud storage metadata

**Note:** The `photo_hothash` field is NOT sent in the request body - it's taken from the URL path parameter.

**Use Cases:**
- Adding RAW file when JPEG already imported
- Adding different resolution of same photo
- Adding edited version to original

**Response** (`201 Created`):
```json
{
  "image_file_id": 124,
  "photo_hothash": "abc123def456789...",
  "photo_created": false,
  "success": true,
  "message": "Image file added to existing photo successfully",
  "filename": "IMG_001.CR2",
  "file_size": 25000000
}
```

**Error Responses:**
- `404 Not Found` - Photo with this hothash doesn't exist
  ```json
  {
    "detail": "Photo with hothash 'abc123...' not found. Use POST /photos/new-photo to create new photo."
  }
  ```
- `400 Bad Request` - Validation error
- `422 Unprocessable Entity` - Invalid field values
- `500 Internal Server Error` - Server error

### Troubleshooting Photo Upload

**Problem: Getting 500 Internal Server Error**

Check the server logs for detailed error messages. Common issues:

1. **Invalid hotpreview data:**
   ```
   ERROR: Validation error creating photo: Invalid hotpreview Base64 data
   ```
   - Solution: Ensure hotpreview is valid Base64-encoded JPEG
   - Must be at least 10 bytes after decoding
   - Can include or exclude `data:image/jpeg;base64,` prefix

2. **Missing required fields:**
   ```
   ERROR: Request data details - filename: None, hotpreview_size: 0
   ```
   - Solution: Both `filename` and `hotpreview` are required

3. **Invalid datetime format:**
   ```
   ERROR: Invalid datetime format for taken_at
   ```
   - Solution: Use ISO 8601 format: `"2025-10-15T14:30:00Z"`

**Problem: Getting 409 Conflict (Duplicate)**

This means a Photo with the same hotpreview already exists.
- The system generates a unique `hothash` from the hotpreview
- If you want to add another file for the same photo (e.g., RAW), use `POST /photos/{hothash}/files`

**Problem: Getting 422 Validation Error**

Check the response detail for specific field validation errors:
- `gps_latitude` must be between -90 and 90
- `gps_longitude` must be between -180 and 180
- `file_size` must be >= 0
- `filename` must be 1-255 characters

**Debug Logging:**

Server logs will show:
```
DEBUG: Creating new photo for user 123
DEBUG: Request data: filename=IMG_001.jpg, has_hotpreview=True, file_size=2048576, has_exif=True
```

If you see:
```
ERROR: Unexpected error creating photo with file: <details>
```

This indicates a server-side issue. Check:
- Database connection
- File permissions
- Server configuration

---

## � PhotoText Documents

PhotoText documents are structured visual storytelling documents that combine photos with narrative text. They support visibility control just like photos.

**Document Types:**
- `general` - Free-form story with photos and text
- `album` - Photo album with captions
- `slideshow` - Presentation-style document

### List PhotoText Documents
```http
GET /api/v1/phototext?offset=0&limit=100
Authorization: Bearer <token>  # Optional - omit for anonymous access to public documents
```

**Query Parameters:**
- `offset` (int, default=0): Skip N documents
- `limit` (int, default=100): Number of documents to return
- `document_type` (string, optional): Filter by type (`general`, `album`, `slideshow`)

**Access Control:**
- **Anonymous (no auth header)**: Only `public` documents returned
- **Authenticated**: Own documents + `authenticated` documents + `public` documents returned

**Response:**
```json
{
  "documents": [
    {
      "id": 123,
      "title": "Summer Vacation 2024",
      "document_type": "album",
      "visibility": "authenticated",
      "is_published": true,
      "user_id": 1,
      "created_at": "2025-10-20T10:00:00Z",
      "updated_at": "2025-10-20T15:30:00Z"
    }
  ],
  "total": 42,
  "offset": 0,
  "limit": 100
}
```

### Get PhotoText Document by ID
```http
GET /api/v1/phototext/{document_id}
Authorization: Bearer <token>  # Optional - omit for anonymous access to public documents
```

**Access Control:**
- **Anonymous**: Only `public` documents accessible (404 for others)
- **Authenticated**: Own documents + `authenticated` documents + `public` documents accessible
- **Owner**: Always can access own documents regardless of visibility

**Response:**
```json
{
  "id": 123,
  "title": "Summer Vacation 2024",
  "document_type": "album",
  "visibility": "authenticated",
  "is_published": true,
  "content": {
    "sections": [
      {
        "type": "text",
        "content": "Our amazing summer vacation..."
      },
      {
        "type": "photo",
        "hothash": "abc123def456...",
        "caption": "Beach sunset"
      }
    ]
  },
  "user_id": 1,
  "created_at": "2025-10-20T10:00:00Z",
  "updated_at": "2025-10-20T15:30:00Z"
}
```

### Create PhotoText Document
```http
POST /api/v1/phototext
Authorization: Bearer <token>  # Required
Content-Type: application/json

{
  "title": "My New Story",
  "document_type": "general",
  "visibility": "private",
  "is_published": false,
  "content": {
    "sections": [
      {
        "type": "text",
        "content": "Introduction text..."
      }
    ]
  }
}
```

**Response (201 Created):**
```json
{
  "id": 124,
  "title": "My New Story",
  "document_type": "general",
  "visibility": "private",
  "is_published": false,
  "content": { ... },
  "user_id": 1,
  "created_at": "2025-11-08T10:00:00Z",
  "updated_at": "2025-11-08T10:00:00Z"
}
```

### Update PhotoText Document
```http
PUT /api/v1/phototext/{document_id}
Authorization: Bearer <token>  # Required - owner only
Content-Type: application/json

{
  "title": "Updated Title",
  "visibility": "public",
  "is_published": true,
  "content": { ... }
}
```

**Access Control:**
- Only the document owner can update
- All fields are optional
- Changing `visibility` immediately affects who can view the document

**Visibility Field:**
- `"private"` - Only you can see it (default)
- `"space"` - Space members (Phase 2 - not yet functional, treated as private)
- `"authenticated"` - All logged-in users can see it
- `"public"` - Everyone including anonymous users can see it

### Delete PhotoText Document
```http
DELETE /api/v1/phototext/{document_id}
Authorization: Bearer <token>  # Required - owner only
```

**Access Control:**
- Only the document owner can delete

**Response (204 No Content)**

---

## �🗂️ ImageFiles

**⚠️ IMPORTANT:** As of API v2.1, the ImageFiles API has been removed. All ImageFile operations are now performed through the Photos API.

### Migration Guide

**Old (Removed as of November 12, 2025):**
```http
POST /api/v1/photos/new-photo            ❌ REMOVED
POST /api/v1/image-files/new-photo       ❌ REMOVED
POST /api/v1/image-files/add-to-photo    ❌ REMOVED
GET /api/v1/image-files/{id}             ❌ REMOVED
```

**New (Current - PhotoEgg Architecture):**
```http
POST /api/v1/photos/photoegg             ✅ PRIMARY - Desktop app (pre-processed PhotoEgg)
POST /api/v1/photos/register-image       ✅ CONVENIENCE - Web app (upload image)
POST /api/v1/photos/{hothash}/files      ✅ Add companion files (RAW, etc.)
GET /api/v1/photos/{hothash}             ✅ ImageFiles included in response
```

### Accessing ImageFiles

ImageFiles are now accessed exclusively through their parent Photo:

```http
GET /api/v1/photos/{hothash}
```

**Response includes ImageFiles:**
```json
{
  "hothash": "abc123def456...",
  "width": 4000,
  "height": 3000,
  "image_files": [
    {
      "id": 123,
      "filename": "IMG_001.jpg",
      "file_size": 2048576,
      "file_type": "jpeg"
    },
    {
      "id": 124,
      "filename": "IMG_001.CR2",
      "file_size": 25000000,
      "file_type": "raw"
    }
  ]
}
```

### Legacy Endpoints (Removed in v2.1)

The following endpoints were removed in API v2.1. All functionality has been moved to the Photos API.

**Removed Endpoints:**
- ❌ `GET /api/v1/image-files` - List ImageFiles
- ❌ `GET /api/v1/image-files/{id}` - Get ImageFile details
- ❌ `POST /api/v1/image-files` - Upload ImageFile (deprecated)
- ❌ `POST /api/v1/image-files/new-photo` - **Moved to** `POST /api/v1/photos/new-photo`
- ❌ `POST /api/v1/image-files/add-to-photo` - **Moved to** `POST /api/v1/photos/{hothash}/files`
- ❌ `GET /api/v1/image-files/{id}/hotpreview` - Use Photo hotpreview instead
- ❌ `GET /api/v1/image-files/similar/{id}` - Similar image search (to be reimplemented)

**Rationale:** ImageFiles are now treated as internal data structures that belong to Photos. All user-facing operations are performed through the Photos API, which provides a cleaner, more intuitive interface.

---

## � Timeline

Navigate photos by time with hierarchical year/month/day/hour aggregation. The Timeline API provides automatic photo organization with representative previews and visibility-aware filtering.

**Features:**
- Hierarchical time navigation (year → month → day → hour)
- Smart preview selection (highest rated or temporally centered)
- Visibility filtering (respects private/authenticated/public)
- Anonymous access support (public photos only)
- Scalable aggregation on server

### Get Timeline Aggregations

```http
GET /api/v1/timeline?granularity=year
Authorization: Bearer <token>  # Optional - anonymous sees only public photos
```

**Query Parameters:**

| Parameter | Type | Required | Description | Values |
|-----------|------|----------|-------------|--------|
| `granularity` | string | No | Time bucket size | `year`, `month`, `day`, `hour` (default: `year`) |
| `year` | integer | No | Filter to specific year | 1900-2100 |
| `month` | integer | No | Filter to specific month | 1-12 (requires `year`) |
| `day` | integer | No | Filter to specific day | 1-31 (requires `year` and `month`) |

### Years Aggregation

```http
GET /api/v1/timeline?granularity=year
```

**Response** (`200 OK`):
```json
{
  "data": [
    {
      "year": 2024,
      "count": 1247,
      "preview_hothash": "abc123...",
      "preview_url": "/api/v1/photos/abc123.../hotpreview",
      "date_range": {
        "first": "2024-01-05T08:23:12Z",
        "last": "2024-12-28T19:45:00Z"
      }
    },
    {
      "year": 2023,
      "count": 892,
      "preview_hothash": "def456...",
      "preview_url": "/api/v1/photos/def456.../hotpreview",
      "date_range": {
        "first": "2023-02-14T10:30:00Z",
        "last": "2023-12-31T23:59:59Z"
      }
    }
  ],
  "meta": {
    "total_years": 5,
    "total_photos": 4521,
    "granularity": "year"
  }
}
```

### Months Aggregation

```http
GET /api/v1/timeline?granularity=month&year=2024
```

**Response** (`200 OK`):
```json
{
  "data": [
    {
      "year": 2024,
      "month": 12,
      "count": 156,
      "preview_hothash": "xyz789...",
      "preview_url": "/api/v1/photos/xyz789.../hotpreview",
      "date_range": {
        "first": "2024-12-01T09:15:00Z",
        "last": "2024-12-28T19:45:00Z"
      }
    }
  ],
  "meta": {
    "total_months": 12,
    "total_photos": 1247,
    "granularity": "month",
    "year": 2024
  }
}
```

### Days Aggregation

```http
GET /api/v1/timeline?granularity=day&year=2024&month=12
```

**Response** (`200 OK`):
```json
{
  "data": [
    {
      "year": 2024,
      "month": 12,
      "day": 28,
      "count": 45,
      "preview_hothash": "rst123...",
      "preview_url": "/api/v1/photos/rst123.../hotpreview",
      "date_range": {
        "first": "2024-12-28T08:00:00Z",
        "last": "2024-12-28T19:45:00Z"
      }
    }
  ],
  "meta": {
    "total_days": 28,
    "total_photos": 156,
    "granularity": "day",
    "year": 2024,
    "month": 12
  }
}
```

### Hours Aggregation

```http
GET /api/v1/timeline?granularity=hour&year=2024&month=12&day=28
```

**Response** (`200 OK`):
```json
{
  "data": [
    {
      "year": 2024,
      "month": 12,
      "day": 28,
      "hour": 14,
      "count": 12,
      "preview_hothash": "lmn456...",
      "preview_url": "/api/v1/photos/lmn456.../hotpreview",
      "date_range": {
        "first": "2024-12-28T14:05:32Z",
        "last": "2024-12-28T14:58:41Z"
      }
    }
  ],
  "meta": {
    "total_hours": 6,
    "total_photos": 45,
    "granularity": "hour",
    "year": 2024,
    "month": 12,
    "day": 28
  }
}
```

**Preview Selection:**
- Priority 1: Highest rated photo (rating 4-5)
- Priority 2: Temporally centered photo (middle of period)
- Priority 3: First photo in period

**Visibility Filtering:**
- Anonymous users see only `public` photos
- Authenticated users see: own + `authenticated` + `public` photos
- Empty periods (no accessible photos) are not included in response

**Use Cases:**
- Year overview grid with preview cards
- Month/day expansion on click
- Lazy-loading infinite scroll timeline
- Public gallery for anonymous users

**See also:** [Timeline API Documentation](./TIMELINE_API.md) for detailed specifications

---

## �📚 Authors

Manage photographers/creators. Authors are **shared metadata tags** used to identify who took a photo - they are NOT user-scoped resources. All users can view all authors.

**Important:** Photo ownership and visibility is controlled via `Photo.user_id`, not Author. Authors are simply metadata for tagging the photographer.

**Self-Author Pattern:**
- When a user registers, an Author is automatically created with `is_self=true`
- This "self-author" represents the user as a photographer
- The user's `default_author_id` points to this self-author
- When importing photos without specifying `author_id`, the default author is used automatically
- Users can create additional authors for other photographers

### List Authors
```http
GET /api/v1/authors?offset=0&limit=100
```

**No authentication required** - all users can view all authors.

**Response** (`200 OK`):
```json
{
  "data": [
    {
      "id": 1,
      "name": "Jane Smith",
      "email": "jane@example.com",
      "bio": "Professional landscape photographer",
      "is_self": true,
      "created_at": "2025-10-20T10:00:00Z",
      "image_count": 42
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 100
}
```

### Get Author
```http
GET /api/v1/authors/{author_id}
```

**No authentication required** - all users can view any author.

### Create Author
```http
POST /api/v1/authors
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "bio": "Professional landscape photographer"
}
```

**Authentication required** - Creating authors requires a logged-in user (for audit trail).

**Response** (`201 Created`):
```json
{
  "id": 1,
  "name": "Jane Smith",
  "email": "jane@example.com",
  "bio": "Professional landscape photographer",
  "created_at": "2025-10-20T10:00:00Z",
  "image_count": 0
}
```

### Update Author
```http
PUT /api/v1/authors/{author_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Jane Smith Updated",
  "bio": "Award-winning photographer"
}
```

**Authentication required** - Updating authors requires authentication.

### Delete Author
```http
DELETE /api/v1/authors/{author_id}
Authorization: Bearer <token>
```

**Authentication required** - Deleting authors requires authentication.

---

## 📦 Input Channels

User-defined channels for organizing photo uploads.

### Create Input Channel
```http
POST /api/v1/input-channels
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Birthday party photos",
  "description": "Photos from birthday celebration",
  "default_author_id": 1
}
```

**Response** (`201 Created`):
```json
{
  "id": 1,
  "title": "Birthday party photos",
  "description": "Photos from birthday celebration",
  "default_author_id": 1,
  "imported_at": "2025-10-20T10:00:00Z",
  "images_count": 0
}
```

### Get Input Channel
```http
GET /api/v1/input-channels/{channel_id}
Authorization: Bearer <token>
```

### List Input Channels
```http
GET /api/v1/input-channels?offset=0&limit=50
Authorization: Bearer <token>
```

### Update Input Channel
```http
PATCH /api/v1/input-channels/{channel_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Updated title",
  "description": "Updated description"
}
```

### Delete Input Channel
```http
DELETE /api/v1/input-channels/{channel_id}
Authorization: Bearer <token>
```

---

## 🗂️ PhotoStacks

Group photos for UI organization (panoramas, bursts, HDR brackets, etc.). Each photo can belong to at most one stack.

### List PhotoStacks
```http
GET /api/v1/photo-stacks?offset=0&limit=50
Authorization: Bearer <token>
```

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "stack_type": "panorama",
      "cover_photo_hothash": "abc123...",
      "photo_count": 5,
      "created_at": "2025-10-20T10:00:00Z",
      "updated_at": "2025-10-20T10:00:00Z"
    }
  ],
  "meta": {
    "total": 15,
    "offset": 0,
    "limit": 50,
    "page": 1,
    "pages": 1
  }
}
```

### Get PhotoStack Details
```http
GET /api/v1/photo-stacks/{stack_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "stack_type": "panorama",
  "cover_photo_hothash": "abc123...",
  "photo_hothashes": ["abc123...", "def456...", "ghi789..."],
  "photo_count": 3,
  "created_at": "2025-10-20T10:00:00Z",
  "updated_at": "2025-10-20T10:00:00Z"
}
```

### Create PhotoStack
```http
POST /api/v1/photo-stacks
Authorization: Bearer <token>
Content-Type: application/json

{
  "stack_type": "panorama",
  "cover_photo_hothash": "abc123..."
}
```

**Response** (`201 Created`):
```json
{
  "success": true,
  "message": "Photo stack created successfully",
  "stack": {
    "id": 1,
    "stack_type": "panorama",
    "cover_photo_hothash": "abc123...",
    "photo_hothashes": [],
    "photo_count": 0,
    "created_at": "2025-10-20T10:00:00Z",
    "updated_at": "2025-10-20T10:00:00Z"
  }
}
```

### Update PhotoStack
```http
PUT /api/v1/photo-stacks/{stack_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "stack_type": "burst",
  "cover_photo_hothash": "def456..."
}
```

### Delete PhotoStack
```http
DELETE /api/v1/photo-stacks/{stack_id}
Authorization: Bearer <token>
```

**Note:** Photos in the stack are not deleted, only the stack grouping.

### Add Photo to Stack
```http
POST /api/v1/photo-stacks/{stack_id}/photo
Authorization: Bearer <token>
Content-Type: application/json

{
  "photo_hothash": "xyz789..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Photo added to stack successfully",
  "stack": {
    "id": 1,
    "photo_hothashes": ["abc123...", "def456...", "xyz789..."],
    "photo_count": 3
  }
}
```

### Remove Photo from Stack
```http
DELETE /api/v1/photo-stacks/{stack_id}/photo/{photo_hothash}
Authorization: Bearer <token>
```

---

## 🐛 Debug Endpoints

**⚠️ Development only - disable in production!**

### System Status
```http
GET /api/v1/debug/status
```

### Database Stats
```http
GET /api/v1/debug/database-stats
```

### Database Schema
```http
GET /api/v1/debug/database-schema
```

### Reset Database
```http
POST /api/v1/debug/reset-database
```

### Clear Table
```http
DELETE /api/v1/debug/clear-table/{table_name}
```

---

## 📊 Common Response Structures

### Paginated Response
```json
{
  "data": [...],
  "meta": {
    "total": 1000,
    "offset": 0,
    "limit": 100,
    "page": 1,
    "pages": 10
  },
  "links": null
}
```

### Error Response
```json
{
  "detail": "Error message here",
  "status_code": 400
}
```

### Common HTTP Status Codes
- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Success with no response body
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Authenticated but not allowed
- `404 Not Found` - Resource not found
- `409 Conflict` - Duplicate resource
- `500 Internal Server Error` - Server error

---

## 🔑 Authentication Headers

All protected endpoints require JWT token:

```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Token Lifetime:** 30 minutes (configurable)

**Refresh Strategy:** Re-login when token expires (refresh tokens not yet implemented)

---

## �� CORS

API accepts requests from:
- `http://localhost:*` (development)
- `http://127.0.0.1:*` (development)
- Configure `ALLOWED_ORIGINS` in production

---

## 📝 Notes

### User Isolation
All data operations are automatically scoped to the authenticated user. Users cannot access or modify other users' data.

### Photo vs ImageFile (Updated in v2.3)
- **Photo**: Logical representation with visual data (hothash, dimensions, EXIF, hotpreview)
  - Created from PhotoEgg (pre-processed metadata from imalink-core)
  - Backend NEVER processes images - only stores metadata
- **ImageFile**: Physical file tracking (filename, file_path, file_size)
  - Optional - used by desktop app to track local files
  - Not required for web uploads
- **Relationship**: One Photo can have multiple ImageFiles (e.g., RAW + JPEG)
- **API Access**: Photos are primary. ImageFiles accessed through Photos only.

### PhotoEgg Architecture (v2.3)
As of v2.3, all photo creation uses PhotoEgg pattern:
- **Desktop app**: Process images locally with imalink-core → PhotoEgg → Backend (`POST /photos/photoegg`)
- **Web app**: Upload image → Backend → imalink-core server → PhotoEgg → Backend stores (`POST /photos/register-image`)
- Backend NEVER processes images directly
- Original files NOT stored on server (only metadata + previews)
- Consistent metadata format regardless of source

### PhotoStacks
- One-to-many relationship: each Photo can belong to at most ONE stack
- Used for UI organization only, doesn't modify Photo objects
- Common stack types: `panorama`, `burst`, `hdr`, `focus_stack`, `time_lapse`

### Hotpreview
- 150x150px JPEG thumbnail
- Auto-rotated based on EXIF orientation
- Stored as binary blob in database
- Used for fast gallery display and generating Photo hothash (SHA256)

---

## 🚀 Getting Started

1. **Register a user:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username":"demo","email":"demo@example.com","password":"demo123","display_name":"Demo User"}'
   ```

2. **Login to get token:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"demo","password":"demo123"}'
   ```

3. **Use token in requests:**
   ```bash
   curl -X GET http://localhost:8000/api/v1/photos \
     -H "Authorization: Bearer YOUR_TOKEN_HERE"
   ```

---

## 📋 Changelog

### v2.3 (November 12, 2025) - PhotoEgg Architecture
**Breaking Changes:**
- ❌ **REMOVED:** `POST /api/v1/photos/new-photo` - Use `/photos/photoegg` or `/photos/register-image` instead

**New Features:**
- ✅ **Added:** `POST /api/v1/photos/photoegg` - Create photo from pre-processed PhotoEgg (desktop app)
- ✅ **Added:** `POST /api/v1/photos/register-image` - Web upload convenience endpoint
- ✅ **Added:** `category` field to Photo model (user-defined categorization)
- ✅ **Added:** `is_protected` field to InputChannel (prevent deletion of default channels)
- ✅ **Added:** Protected "Quick Channel" created automatically per user
- ✅ **Added:** Auto-use protected InputChannel when input_channel_id not provided
- ✅ **Added:** Self-Author pattern - default Author created automatically at registration
- ✅ **Added:** `User.default_author_id` - points to user's self-author
- ✅ **Added:** `Author.is_self` - marks authors that represent users
- ✅ **Added:** Auto-use default author when author_id not provided in photo imports

**Architecture Changes:**
- 🔄 **Changed:** Backend no longer processes images directly
- 🔄 **Changed:** All image processing done by imalink-core (local or server)
- 🔄 **Changed:** New user registration creates Author + InputChannel automatically
- 🔄 **Changed:** PhotoEgg is now the single photo creation format
- 🔄 **Changed:** Desktop app uses local imalink-core (fast, no upload)
- 🔄 **Changed:** Web app uploads to backend → server imalink-core (convenience)

**Migration Guide:**
- See `docs/API_CHANGELOG_2025_11_12.md` for complete migration instructions

### v2.2 (November 8, 2025) - Visibility & Sharing
**New Features:**
- ✅ **Added:** Four-level visibility system (`private`, `space`, `authenticated`, `public`)
- ✅ **Added:** `visibility` field to Photo model (default: `private`)
- ✅ **Added:** `visibility` field to PhotoTextDocument model (default: `private`)
- ✅ **Added:** Anonymous access to `public` photos and documents
- ✅ **Added:** Authenticated community sharing via `authenticated` visibility
- ✅ **Added:** PhotoText Documents API (`/api/v1/phototext`)
- ✅ **Added:** Complete PhotoText CRUD operations with visibility control

**API Changes:**
- 📝 **Modified:** `GET /api/v1/photos` - Now supports anonymous access (returns only public photos)
- 📝 **Modified:** `GET /api/v1/photos/{hothash}` - Now supports anonymous access
- 📝 **Modified:** `PUT /api/v1/photos/{hothash}` - Can update `visibility` field
- 📝 **Modified:** All photo responses now include `visibility` field
- 📝 **Modified:** `GET /api/v1/phototext` - Now supports anonymous access
- 📝 **Modified:** `GET /api/v1/phototext/{id}` - Now supports anonymous access

**Future (Phase 2):**
- 🚧 **Planned:** `space` visibility will become functional with Spaces infrastructure
- 🚧 **Planned:** Create and manage shared workspaces
- 🚧 **Planned:** Share photos/documents to multiple spaces

**Breaking Changes:**
- None - All changes are backwards compatible. Existing photos/documents default to `private`.

---

### v2.1 (October 21, 2025) - 100% Photo-Centric API
**Breaking Changes:**
- ❌ **Removed:** Entire ImageFiles API (`/api/v1/image-files/*`)
- ❌ **Removed:** `GET /api/v1/image-files/{id}` - Access ImageFiles via Photo responses
- ❌ **Removed:** `POST /api/v1/image-files/new-photo` 
- ❌ **Removed:** `POST /api/v1/image-files/add-to-photo`

**New Endpoints:**
- ✅ **Added:** `POST /api/v1/photos/new-photo` - Create Photo with initial ImageFile
- ✅ **Added:** `POST /api/v1/photos/{hothash}/files` - Add ImageFile to existing Photo

**Benefits:**
- Cleaner, more intuitive API
- Photos are the natural entry point for all operations
- ImageFiles accessible via Photo relationships
- Reduced API surface area

**Migration Guide:**
```bash
# Before v2.1:
POST /api/v1/image-files/new-photo

# After v2.1:
POST /api/v1/photos/new-photo

# Before v2.1:
POST /api/v1/image-files/add-to-photo
{
  "photo_hothash": "abc123...",
  "filename": "image.raw"
}

# After v2.1:
POST /api/v1/photos/abc123.../files
{
  "filename": "image.raw"
}
```

---

## 📊 System & Monitoring

### Get Database Statistics
Get comprehensive statistics about database tables, storage usage, and disk space.

```http
GET /api/v1/database-stats
```

**Authentication:** ❌ **Not required** - This endpoint is intended for system monitoring.

**Response** (`200 OK`):
```json
{
  "tables": {
    "photos": {
      "name": "photos",
      "record_count": 45,
      "size_bytes": 4612096,
      "size_mb": 4.4
    },
    "image_files": {
      "name": "image_files",
      "record_count": 45,
      "size_bytes": 92160,
      "size_mb": 0.09
    },
    "users": {
      "name": "users",
      "record_count": 2,
      "size_bytes": 8192,
      "size_mb": 0.01
    },
    "authors": {
      "name": "authors",
      "record_count": 3,
      "size_bytes": 12288,
      "size_mb": 0.01
    },
    "tags": {
      "name": "tags",
      "record_count": 15,
      "size_bytes": 24576,
      "size_mb": 0.02
    },
    "input_channels": {
      "name": "input_channels",
      "record_count": 1,
      "size_bytes": 4096,
      "size_mb": 0.0
    },
    "photo_stacks": {
      "name": "photo_stacks",
      "record_count": 0,
      "size_bytes": 0,
      "size_mb": 0.0
    }
  },
  "coldstorage": {
    "path": "/mnt/c/temp/00imalink_data/coldpreviews",
    "total_files": 45,
    "total_size_bytes": 6656400,
    "total_size_mb": 6.35,
    "total_size_gb": 0.01
  },
  "database_file": "/mnt/c/temp/00imalink_data/imalink.db",
  "database_size_bytes": 8392704,
  "database_size_mb": 8.0
}
```

**Response Fields:**

- `tables`: Dictionary of table statistics
  - `name`: Table name
  - `record_count`: Number of records in table
  - `size_bytes`: Approximate size on disk in bytes
  - `size_mb`: Approximate size on disk in megabytes

- `coldstorage`: Cold storage (coldpreview files) statistics
  - `path`: Storage directory path
  - `total_files`: Number of coldpreview files
  - `total_size_bytes`: Total size in bytes
  - `total_size_mb`: Total size in megabytes
  - `total_size_gb`: Total size in gigabytes

- `database_file`: Path to database file
- `database_size_bytes`: Total database file size in bytes
- `database_size_mb`: Total database file size in megabytes

**Use Cases:**
- System monitoring dashboards
- Storage space alerts
- Database maintenance scheduling
- Performance analysis
- Capacity planning

**Example - Python:**
```python
import requests

response = requests.get("http://localhost:8000/api/v1/database-stats")
stats = response.json()

print(f"Total photos: {stats['tables']['photos']['record_count']}")
print(f"Database size: {stats['database_size_mb']} MB")
print(f"Coldstorage size: {stats['coldstorage']['total_size_gb']} GB")
```

**Example - cURL:**
```bash
curl http://localhost:8000/api/v1/database-stats
```

**Notes:**
- Table sizes are approximate for SQLite (uses dbstat when available)
- Coldstorage includes all coldpreview files (800-1200px JPEG previews)
- Read-only operation with minimal overhead - safe to call frequently

---

## 📅 Events (Hierarchical Photo Organization)

Events organize photos by contextual hierarchy (trips, occasions, projects). Unlike Collections (flat, curated), Events support parent-child relationships for natural grouping.

**Key Features:**
- **Hierarchical**: Parent-child relationships (e.g., "London 2025" > "Tower of London")
- **One-to-many**: Each photo belongs to at most ONE event (simpler model)
- **Recursive queries**: Get all photos in event + descendants
- **Temporal/Spatial**: Optional dates and GPS coordinates
- **User-scoped**: Each user has their own event hierarchy
- **Optional**: Photos can have `event_id=null` (not all photos need events)

### List Events

```http
GET /api/v1/events/
Authorization: Bearer {token}
```

**Query Parameters:**
- `parent_id` (optional): Filter by parent event ID
  - If omitted: Returns root events only
  - If provided: Returns children of that event

**Response** (`200 OK`):
```json
[
  {
    "id": 1,
    "user_id": 1,
    "name": "London Trip 2025",
    "description": "Summer vacation in London",
    "parent_event_id": null,
    "start_date": "2025-07-01T00:00:00Z",
    "end_date": "2025-07-10T00:00:00Z",
    "location_name": "London, UK",
    "gps_latitude": 51.5074,
    "gps_longitude": -0.1278,
    "sort_order": 0,
    "created_at": "2025-12-01T10:00:00Z",
    "updated_at": "2025-12-01T10:00:00Z",
    "photo_count": 42
  }
]
```

**Examples:**
```bash
# List root events
curl http://localhost:8000/api/v1/events/ \
  -H "Authorization: Bearer {token}"

# List children of specific event
curl "http://localhost:8000/api/v1/events/?parent_id=1" \
  -H "Authorization: Bearer {token}"
```

### Get Event Tree

```http
GET /api/v1/events/tree
Authorization: Bearer {token}
```

**Query Parameters:**
- `root_id` (optional): Root event ID to start from
  - If omitted: Returns all root events with full tree
  - If provided: Returns that event + descendants

**Response** (`200 OK`):
```json
{
  "events": [
    {
      "id": 1,
      "name": "London Trip 2025",
      "parent_event_id": null,
      "photo_count": 15,
      "children": [
        {
          "id": 2,
          "name": "Tower of London",
          "parent_event_id": 1,
          "photo_count": 8,
          "children": []
        },
        {
          "id": 3,
          "name": "British Museum",
          "parent_event_id": 1,
          "photo_count": 7,
          "children": []
        }
      ]
    }
  ],
  "total_events": 3
}
```

**Use Cases:**
- Display hierarchical event browser
- Navigation breadcrumbs
- Event tree visualization

### Create Event

```http
POST /api/v1/events/
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "London Trip 2025",
  "description": "Summer vacation in London",
  "parent_event_id": null,
  "start_date": "2025-07-01T00:00:00Z",
  "end_date": "2025-07-10T00:00:00Z",
  "location_name": "London, UK",
  "gps_latitude": 51.5074,
  "gps_longitude": -0.1278,
  "sort_order": 0
}
```

**Required Fields:**
- `name`: Event name (1-200 characters)

**Optional Fields:**
- `description`: Event description (max 2000 characters)
- `parent_event_id`: Parent event for hierarchy (null = root level)
- `start_date`, `end_date`: Temporal context
- `location_name`: Location name (max 200 characters)
- `gps_latitude`, `gps_longitude`: GPS coordinates
- `sort_order`: Order among siblings (default 0)

**Response** (`201 Created`):
```json
{
  "id": 1,
  "user_id": 1,
  "name": "London Trip 2025",
  "description": "Summer vacation in London",
  "parent_event_id": null,
  "start_date": "2025-07-01T00:00:00Z",
  "end_date": "2025-07-10T00:00:00Z",
  "location_name": "London, UK",
  "gps_latitude": 51.5074,
  "gps_longitude": -0.1278,
  "sort_order": 0,
  "created_at": "2025-12-02T10:00:00Z",
  "updated_at": "2025-12-02T10:00:00Z"
}
```

**Validation:**
- Parent event must exist and belong to same user
- Cannot create cycle (parent cannot be own descendant)

### Get Event by ID

```http
GET /api/v1/events/{event_id}
Authorization: Bearer {token}
```

**Response** (`200 OK`): Same as Create response
**Error** (`404 Not Found`): Event not found or access denied

### Update Event

```http
PUT /api/v1/events/{event_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Updated Event Name",
  "description": "New description",
  "start_date": "2025-07-05T00:00:00Z"
}
```

**All fields optional** - only provided fields will be updated.

**Note:** To change parent, use `parent_event_id` field (validated to prevent cycles) or use Move Event endpoint.

### Move Event

```http
POST /api/v1/events/{event_id}/move
Authorization: Bearer {token}
Content-Type: application/json

{
  "new_parent_id": 5
}
```

**Body:**
- `new_parent_id`: New parent event ID (null to move to root level)

**Response** (`200 OK`): Updated event with new parent

**Validation:**
- Cannot move event to itself
- Cannot move event to its own descendant (prevents cycles)
- New parent must belong to same user

**Example:**
```bash
# Move event to root level
curl -X POST http://localhost:8000/api/v1/events/3/move \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"new_parent_id": null}'
```

### Delete Event

```http
DELETE /api/v1/events/{event_id}
Authorization: Bearer {token}
```

**Response** (`204 No Content`)

**Behavior:**
- Child events become root events (parent_event_id set to NULL)
- Photos remain but have event_id set to NULL (via CASCADE SET NULL)
- One-to-many: Each photo has single event_id (simpler than junction table)

### Get Event Photos

```http
GET /api/v1/events/{event_id}/photos
Authorization: Bearer {token}
```

**Query Parameters:**
- `include_descendants` (optional, default: false)
  - `false`: Only photos directly in this event
  - `true`: Photos in this event + all child events (recursive)

**Response** (`200 OK`):
```json
[
  {
    "hothash": "abc123...",
    "user_id": 1,
    "taken_at": "2025-07-05T14:30:00Z",
    "visibility": "private",
    "event_id": 1,
    "width": 4000,
    "height": 3000
    // ... (full PhotoResponse schema)
  }
]
```

**Example:**
```bash
# Get photos in event + all descendants
curl "http://localhost:8000/api/v1/events/1/photos?include_descendants=true" \
  -H "Authorization: Bearer {token}"
```

**Use Cases:**
- Display event gallery
- Export all photos from trip (including sub-events)
- Count photos in event hierarchy

### Set Photo Event (One-to-Many)

```http
PUT /api/v1/photos/{hothash}/event
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:** Send event ID as integer or null (NOT wrapped in object key)
```json
5
```

**Or send `null` to remove from event:**
```json
null
```

**Response** (`200 OK`):
```json
{
  "hothash": "abc123...",
  "event_id": 5,
  "user_id": 1,
  "taken_at": "2025-07-05T14:30:00Z",
  "visibility": "private",
  "width": 4000,
  "height": 3000
  // ... (full PhotoResponse)
}
```

**Behavior:**
- **One-to-many**: Photo can belong to at most ONE event
- Setting new event_id **replaces** previous event (if any)
- Setting `null` removes photo from event
- Event must exist and belong to same user
- Returns updated photo with new event_id

**Examples:**
```bash
# Assign photo to event
curl -X PUT http://localhost:8000/api/v1/photos/abc123.../event \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '5'

# Remove photo from event
curl -X PUT http://localhost:8000/api/v1/photos/abc123.../event \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d 'null'
```

**Use Cases:**
- Add photos to event from gallery
- Move photo from one event to another
- Organize imported photos into events

**Note:** For many-to-many relationships, use Collections or Tags instead.

---

## 📊 Event Statistics & Queries

### Photo Count
- Direct count: Query `GET /api/v1/events/` returns `photo_count` field
- Recursive count: Use `GET /api/v1/events/{id}/photos?include_descendants=true` and count results

### Hierarchy Navigation
- Root events: `GET /api/v1/events/` (no parent_id)
- Children: `GET /api/v1/events/?parent_id={id}`
- Full tree: `GET /api/v1/events/tree`

**Features:**
- **Direct assignment**: Each photo has single event_id
- **Reassignment**: Setting new event_id automatically removes from old event
- **Nullable**: Send `null` to remove photo from all events
- **Validation**: Event must exist and belong to same user
- **Design**: Uses hothash (not photo ID) per ImaLink philosophy

**Examples:**
```bash
# Assign photo to event
curl -X PUT http://localhost:8000/api/v1/photos/abc123.../event \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '5'

# Remove photo from event
curl -X PUT http://localhost:8000/api/v1/photos/abc123.../event \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d 'null'
```

**Alternative:** You can also use `PUT /api/v1/photos/{hothash}` with `event_id` field to update event along with other photo metadata.

---

## 📚 Photo Collections (Curated Photo Sets with Text Cards)

Collections are ordered lists of mixed content (photos + text cards) for curated albums, portfolios, or client deliverables. Unlike Events (hierarchical), Collections are simple flat structures with explicit ordering.

**Key Features:**
- **Mixed content**: Combine photos and text cards in same collection
- **Text cards**: Add captions, notes, descriptions between photos
- **Explicit ordering**: Items array defines exact order (position = array index)
- **Many-to-many**: Photos can be in multiple collections
- **User-scoped**: Each user has their own collections
- **Flexible**: Add/remove items without affecting originals

### List Collections

```http
GET /api/v1/collections/
Authorization: Bearer {token}
```

**Query Parameters:**
- `offset` (int, default=0): Skip N collections
- `limit` (int, default=100, max=5000): Number of collections to return

**Response:**
```json
{
  "collections": [
    {
      "id": 1,
      "name": "Best of 2024",
      "description": "My favorite photos from 2024",
      "item_count": 52,
      "photo_count": 45,
      "text_card_count": 7,
      "cover_photo_hothash": "abc123...",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-12-16T14:22:00Z"
    }
  ],
  "total": 12
}
```

### Get Collection Details

```http
GET /api/v1/collections/{id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "name": "Best of 2024",
  "description": "My favorite photos from 2024",
  "items": [
    {"type": "photo", "photo_hothash": "abc123..."},
    {"type": "text", "text_card": {"title": "Summer Memories", "body": "These photos are from..."}},
    {"type": "photo", "photo_hothash": "def456..."},
    {"type": "photo", "photo_hothash": "ghi789..."}
  ],
  "item_count": 52,
  "photo_count": 45,
  "text_card_count": 7,
  "cover_photo_hothash": "abc123...",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-12-16T14:22:00Z"
}
```

**Note:** Position is implicit from array index (first item = position 0).

### Get Photos in Collection (Photos Only)

```http
GET /api/v1/collections/{id}/photos
Authorization: Bearer {token}
```

**Response (Simple Array):**
```json
[
  {
    "hothash": "abc123...",
    "width": 4000,
    "height": 3000,
    "rating": 4,
    "taken_at": "2024-06-15T14:30:00Z",
    ...
  },
  {
    "hothash": "def456...",
    ...
  }
]
```

**Notes:**
- Returns ALL photos in collection order (no pagination - you always need the complete list)
- Filters out text cards - only returns Photo objects
- For mixed content (photos + text cards), use `GET /collections/{id}` and parse the `items` array

### Create Collection

```http
POST /api/v1/collections/
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Summer Vacation 2024",
  "description": "Photos from our trip to Italy",
  "hothashes": ["abc123...", "def456..."]  // Optional: initial photos
}
```

**Response:**
```json
{
  "id": 5,
  "name": "Summer Vacation 2024",
  "description": "Photos from our trip to Italy",
  "items": [
    {"type": "photo", "photo_hothash": "abc123..."},
    {"type": "photo", "photo_hothash": "def456..."}
  ],
  "item_count": 2,
  "photo_count": 2,
  "text_card_count": 0,
  "cover_photo_hothash": "abc123...",
  "created_at": "2024-12-16T15:00:00Z",
  "updated_at": "2024-12-16T15:00:00Z"
}
```

### Update Collection Metadata

```http
PATCH /api/v1/collections/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Italian Adventure 2024",
  "description": "Updated description"
}
```

**Note:** This only updates metadata (name, description). To modify items, use the item management endpoints below.

### Delete Collection

```http
DELETE /api/v1/collections/{id}
Authorization: Bearer {token}
```

**Notes:**
- Deletes only the collection, not the photos
- Returns 204 No Content on success

---

## Item Management (Photos + Text Cards)

### Add Items to Collection

```http
POST /api/v1/collections/{id}/items
Authorization: Bearer {token}
Content-Type: application/json

{
  "items": [
    {"type": "photo", "photo_hothash": "abc123..."},
    {"type": "text", "text_card": {"title": "Summer Memories", "body": "These photos capture..."}},
    {"type": "photo", "photo_hothash": "def456..."}
  ]
}
```

**Response:**
```json
{
  "collection_id": 1,
  "item_count": 52,
  "photo_count": 45,
  "affected_count": 3
}
```

**Item Types:**
- **Photo**: `{"type": "photo", "photo_hothash": "abc123..."}`
- **Text Card**: `{"type": "text", "text_card": {"title": "...", "body": "..."}}`

**Validation:**
- Text card title: max 200 characters
- Text card body: max 2000 characters (plain text)
- Photos must exist and belong to user
- Duplicate photos are automatically skipped

**Notes:**
- Items are appended to end of collection
- Position is implicit from array index (no position field needed)

### Reorder Items (Drag-and-Drop)

```http
PUT /api/v1/collections/{id}/items/reorder
Authorization: Bearer {token}
Content-Type: application/json

{
  "items": [
    {"type": "text", "text_card": {"title": "Introduction", "body": "..."}},
    {"type": "photo", "photo_hothash": "ghi789..."},
    {"type": "photo", "photo_hothash": "abc123..."},
    {"type": "photo", "photo_hothash": "def456..."}
  ]
}
```

**Response:**
```json
{
  "collection_id": 1,
  "item_count": 4,
  "photo_count": 3,
  "affected_count": 4
}
```

**Important:**
- **Must include ALL items** you want to keep
- Items not in list are removed from collection
- Perfect for drag-and-drop: just send the entire array in new order

### Delete Item at Position

```http
DELETE /api/v1/collections/{id}/items/{position}
Authorization: Bearer {token}
```

**Example:** `DELETE /api/v1/collections/1/items/2` deletes item at index 2 (third item)

**Response:**
```json
{
  "collection_id": 1,
  "item_count": 51,
  "photo_count": 45,
  "affected_count": 1
}
```

**Notes:**
- Position is 0-based index (first item = position 0)
- Remaining items shift down automatically

### Update Text Card

```http
PATCH /api/v1/collections/{id}/items/{position}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Updated Title",
  "body": "Updated body text..."
}
```

**Response:**
```json
{
  "collection_id": 1,
  "item_count": 52,
  "photo_count": 45,
  "affected_count": 1
}
```

**Notes:**
- Only works for text cards (returns 400 if position is a photo)
- Both fields are optional - send only what you want to update
- Title max 200 chars, body max 2000 chars

### Cleanup Invalid Photos

```http
POST /api/v1/collections/{id}/cleanup
Authorization: Bearer {token}
```

**Response:**
```json
{
  "collection_id": 1,
  "removed_count": 3
}
```

**Notes:**
- Removes photos that no longer exist in database
- Useful for maintaining collection integrity after photo deletions

---

**Last Updated:** December 18, 2025  
**API Version:** 3.2 (Collections with Text Cards + Items Array)  
**Backend Version:** Fase 1 (Multi-User + Events + PhotoStacks + Collections with Mixed Content)
