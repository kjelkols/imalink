# ImaLink

Et enkelt og intuitivt verktøy for organisering av store bildematerialer.

## 💡 Konsepter og Terminologi

### Hothash vs Perceptual Hash
- **Hothash** (SHA256 av hotpreview): Unik identifikator for bildeidentitet
- **Perceptual hash**: Brukes for similarity search og duplikatdeteksjon
- **Viktig**: Hothash = bildeidentitet, perceptual hash = similarity-matching

**Fase 1 MVP + Multi-User System er ferdig!** ✅

### ✅ Implementerte funksjoner:
- **🔐 Multi-User Authentication**: JWT-basert autentisering med brukerregistrering og innlogging
- **🔒 User Data Isolation**: Komplett dataseparasjon - brukere ser kun egne bilder
- **📅 Events (Hierarchical Organization)**: Organiser bilder hierarkisk (f.eks. "London 2025" > "Tower of London")
- **📚 Collections (Mixed Content)**: Kuraterte album med bilder + tekstkort for porteføljer og leveranser
- **🖼️ Crystal Clear Upload API**: Separate endepunkter for nye bilder vs companion-filer
- **Desktop Client**: Python/Flet desktop application med direkte database-tilgang
- **Import System**: Frontend-styrt import med API-baserte operasjoner
- **EXIF-rotasjon**: Automatisk orientering av bilder som i File Explorer
- **RAW+JPEG håndtering**: Smart deteksjon og håndtering av RAW-filer
- **Duplikatdeteksjon**: Perceptuell hash for å unngå duplikater
- **Preview System**: 
  - Hotpreview (150x150) lagret i database for rask tilgang
  - Coldpreview (800-1200px) lagret på disk for detaljvisning
- **Similarity Search**: Find lignende bilder basert på perceptual hash
- **Fotograf-admin**: Fullstendig CRUD med email og bio (bruker-scoped)
- **Modern arkitektur**: FastAPI + PostgreSQL (prod) / SQLite (test) + JWT + Multi-user support

## 🧠 Designfilosofi

ImaLink følger noen unike prinsipper som skiller den fra andre fotoarkiveringsprogrammer:

### 1. "Hot Hotpreview med EXIF-Orientering"
- **Hot hotpreview**: Miniaturbilder lagres som binærdata direkte i databasen for umiddelbar tilgang
- **EXIF-orientering håndtert**: Hotpreview genereres etter korrekt orientering fra EXIF-data
- **Resultat**: Hotpreview vises alltid riktig orientert, uavhengig av EXIF-orientering
- **Fordel**: Konsistent visning av bilder selv når fildata har rotasjonsmarkering

### 2. Hundre Prosent Skille Mellom Kildefil og Server
- **Kildefiler kan være offline**: Original-filer kan ligge på USB-disker, NAS eller cloud-lagring
- **Serveren er komplett uavhengig**: All nødvendig informasjon lagres i databasen
- **Metadata-preservering**: EXIF, hotpreview og bildedata bevares i database
- **Resultat**: Du kan vise, søke og organisere bilder selv om kildefilene ikke er tilgjengelige
- **Fordel**: Perfekt for arkivering på portable medier eller cloud-lagring

### 3. Hash som Universell Nøkkel
- **Hothash = bildeidentitet**: SHA256-hash av hotpreview ER bildeidentiteten, uavhengig av filnavn eller lokasjon
- **Universell referanse**: Samme hothash refererer til samme bilde på tvers av alle systemer
- **Filnavn-uavhengig**: Bilder kan flyttes, omdøpes eller kopieres uten å miste identitet
- **Fremtidssikring**: Hash-basert system kan utvides til distribuerte løsninger
- **Fordel**: Robust identifikasjon som aldri går i stykker ved filoperasjoner
- **Perceptual hash**: Brukes separat for similarity search og duplikatdeteksjon

Denne filosofien gjør ImaLink spesielt egnet for fotografer med store arkiver som må håndtere bilder på tvers av forskjellige lagringsmedier og systemer.

## Photo Corrections

ImaLink supports non-destructive photo corrections that preserve original metadata while allowing users to override display values:

### Time/Location Correction (`timeloc_correction`)
Correct inaccurate timestamps and GPS coordinates without modifying the original image file. Common use cases:
- Camera clock was set to wrong timezone
- GPS coordinates are missing or incorrect
- Date/time needs manual adjustment for historical photos

**How it works:**
- Original EXIF data is preserved in `ImageFile.exif_dict`
- Corrections are stored in `Photo.timeloc_correction` (JSON field)
- When corrections exist, display values are overwritten
- Setting correction to `null` restores original EXIF values

### View Correction (`view_correction`)
Apply visual adjustments for display purposes only - no server-side image processing:
- **Rotation**: Rotate image by 90° increments (0, 90, 180, 270)
- **Relative Crop**: Crop using normalized coordinates (0.0-1.0)
- **Exposure**: Adjust brightness for viewing (-2.0 to +2.0)

**Important:** These are frontend rendering hints only. The backend stores preferences but does not modify images.

### API Endpoints

**Update Time/Location Correction:**
```
PATCH /api/v1/photos/{hothash}/timeloc-correction
```

**Update View Correction:**
```
PATCH /api/v1/photos/{hothash}/view-correction
```

See [API_REFERENCE.md](docs/api/API_REFERENCE.md) for detailed endpoint documentation.

## Photo Tags

ImaLink provides a flexible tagging system for organizing and searching photos with user-defined keywords.

### Tag System Architecture
- **User-scoped tags**: Each user has their own tag vocabulary (no tag sharing between users)
- **Many-to-many relationship**: Photos can have multiple tags, tags can be applied to multiple photos
- **Normalized storage**: Tags are stored once in `tags` table, linked via `photo_tags` association table
- **Case-insensitive**: Tags are normalized to lowercase for consistent searching
- **Autocomplete support**: Fast prefix-matching for tag suggestions while typing

### Key Features
- **Fast search**: Search photos by one or multiple tags (AND/OR logic)
- **Tag management**: Create, rename, delete tags with automatic cleanup
- **Photo counts**: See how many photos are tagged with each tag
- **Bulk operations**: Add/remove multiple tags at once
- **Duplicate prevention**: Same tag cannot be applied twice to the same photo

### API Endpoints

**List all user tags:**
```
GET /api/v1/tags
```

**Autocomplete tag suggestions:**
```
GET /api/v1/tags/autocomplete?q=land
```

**Add tags to photo:**
```
POST /api/v1/photos/{hothash}/tags
Body: ["landscape", "sunset", "norway"]
```

**Remove tag from photo:**
```
DELETE /api/v1/photos/{hothash}/tags/{tag_name}
```

**Search photos by tags:**
```
GET /api/v1/photos?tags=landscape,sunset&tag_logic=AND
```

See [API_REFERENCE.md](docs/api/API_REFERENCE.md) for detailed endpoint documentation.

## � Lagringsstruktur

ImaLink organiserer data i en ryddig struktur:

```
{DATA_DIRECTORY}/                    # /mnt/c/temp/00imalink_data/
├── imalink.db                       # Hoveddatabase (SQLite)
└── coldpreviews/                    # Medium-size preview bilder
    ├── ab/cd/abcd1234...jpg        # Organisert i 2-nivå hash-struktur
    └── ef/gh/efgh5678...jpg        # For optimal ytelse
```

**Lagringsprinsipper:**
- **Database**: Metadata, hotpreview (150x150), perceptual hashes
- **Filesystem**: Kun coldpreview (800-1200px) for detaljvisning
- **Hash-basert**: Filnavn er content-hash for garantert unikhet
- **Skalerbar**: 2-nivå katalogstruktur håndterer millioner av bilder

## �🚀 Kom i gang

### 📚 Dokumentasjon
- **[Fullstendig dokumentasjon](docs/README.md)** - Oversikt over all dokumentasjon
- **[API Reference](docs/api/API_REFERENCE.md)** - REST API dokumentasjon
- **[Qt Frontend Guide](docs/frontend/QT_FRONTEND_GUIDE.md)** - Qt desktop client utvikling

### Backend API:
```bash
# Naviger til Fase 1
cd fase1/src

# Start backend
python main.py

# API dokumentasjon
open http://localhost:8000/docs
```

### Desktop Client:
```bash
# Start desktop demo
cd fase1/desktop_demo
uv run python author_crud_demo.py

# Åpner i nettleser (WSL mode)
open http://localhost:8550
```

Se [Fase 1 README](./fase1/README.md) for detaljert backend-dokumentasjon og [docs/](docs/) for fullstendig API og frontend guides.

## 🏗️ Utviklingsplan

1. **✅ Programspesifikasjon** - Ferdig
2. **✅ Teknologivalg** - Python/FastAPI/SQLite/Flet
3. **✅ Prototype (Fase 1)** - Ferdig MVP med desktop client
4. **⏳ Full Import** - Photo import i desktop client
5. **⏳ Bildehåndtering** - Visning, organisering, tagging

## 🎯 Målsetting

Utvikle et skalerbart system for:
- ✅ Organisering av store bildesamlinger
- ✅ Duplikatdeteksjon
- ✅ EXIF-metadata håndtering
- ✅ Desktop-grensesnitt (Python/Flet)
- ⏳ Fullverdig photo management
- ⏳ Web viewer (read-only, senere fase)

