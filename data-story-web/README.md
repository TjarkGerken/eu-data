# Data Story Web Application

This Next.js application provides an interactive data story interface with comprehensive admin management capabilities.

## Features

### Admin Panel (`/admin`)

#### Content Management (`/admin/content`)

- **Multi-language support**: Edit content in English and German
- **Basic Content**: Hero section and main introduction text
- **Visualizations Management**: Create and edit visualization cards
- **References Management**: Full CRUD operations for bibliography

#### Visualizations Features

- **Rich Editor**: Title, description, content, and type selection
- **Image Integration**: Visual dropdown with thumbnail previews
- **Reference Linking**: Multi-select dropdown for bibliography
- **Dynamic Preview**: Changes reflect immediately on main page

#### References Management

- **Complete Bibliography**: ID, title, authors, year, journal, URL
- **Type Categories**: Journal, Report, Dataset, Book with color coding
- **Search & Filter**: Searchable dropdown across all visualizations
- **Auto-linking**: References automatically appear in sidebar

#### Image Management (`/admin/images`)

- **Multi-category Support**: Hazard, Risk, Exposition, Combined
- **Scenario Detection**: Automatic current/severe scenario recognition
- **Thumbnail Previews**: Visual selection with category badges
- **Dynamic Loading**: Real-time image availability

## Architecture

### Data Structure

```
Supabase Database
├── content_stories       # Story containers (EN/DE)
├── content_blocks        # Individual content blocks
│   ├── block_type       # Type of content block
│   ├── order_index      # Display order
│   ├── data             # Block-specific data
│   ├── title            # Optional title
│   ├── content          # Optional content
│   └── language         # Language code
├── content_references   # Global bibliography
└── block_references     # Block-reference associations
```

### Component Hierarchy

```
AdminPanel
├── ContentManagement
│   ├── BasicContent (per language)
│   ├── VisualizationsEditor
│   │   ├── ReferencesDropdown
│   │   └── ImageDropdown
│   └── ReferencesManager
└── ImageManagement
```

### Type System (`lib/types.ts`)

- `Reference`: Bibliography entries
- `Visualization`: Content cards with media
- `LanguageContent`: Per-language content structure
- `ContentData`: Complete data model
- `ImageOption`: Image metadata with previews

## Development Commands

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Build for production
pnpm build

# Type checking
pnpm type-check
```

## Admin Authentication

Access admin panel at `/admin` with session-based authentication.

## API Endpoints

- `GET /api/content` - Fetch content blocks from database
- `POST /api/content` - Create new content blocks
- `PUT /api/content` - Create block pairs (EN/DE)
- `GET /api/images/[category]` - Fetch category images
- `POST /api/images/upload` - Upload new images

## Key Features

✅ **References Tab**: Complete bibliography management
✅ **Reference Dropdowns**: Visual selection for visualizations  
✅ **Image Previews**: Thumbnail-based image selection
✅ **Multi-language**: English/German content editing
✅ **Real-time Updates**: Changes appear immediately
✅ **Type Safety**: Full TypeScript coverage

## Storage Migration: Supabase → Cloudflare R2

The application has been migrated from Supabase storage to Cloudflare R2 for better scalability and larger file support.

### Key Changes:

- **File Size Limit**: Increased from 50MB to 500MB
- **Supported File Types**: Added support for `.tif` and `.tiff` files for cluster layer processing
- **Storage Backend**: Migrated to Cloudflare R2 with S3-compatible API
- **URL Structure**: Files now served from `tjarkgerken.com/eu-data/` custom domain

### Environment Configuration

Create a `.env.local` file in the `data-story-web` directory with the following variables:

```env
# Cloudflare R2 Storage Configuration (Required)
R2_ENDPOINT=https://daa96ebb0b3ee7e44349906f0f752c94.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET_NAME=eu-data

# Custom Domain (Optional - fallback to development URL if not set)
R2_PUBLIC_URL_BASE=https://tjarkgerken.com/eu-data
```

**Required Environment Variables:**

- `R2_ENDPOINT` - Your Cloudflare R2 S3-compatible API endpoint
- `R2_ACCESS_KEY_ID` - Your R2 access key ID
- `R2_SECRET_ACCESS_KEY` - Your R2 secret access key
- `R2_BUCKET_NAME` - The name of your R2 bucket (`eu-data`)

**Optional Environment Variables:**

- `R2_PUBLIC_URL_BASE` - Custom domain for public file access. If not set, falls back to development URL: `https://pub-d032794d3f654d3eb7dfb097724ded50.r2.dev`

### Supported File Types

#### Map Layers:

- `.cog` - Cloud Optimized GeoTIFF (raster data)
- `.mbtiles` - Vector tiles for interactive maps
- `.tif`, `.tiff` - TIFF raster data for cluster processing

#### Climate Images:

- `.png`, `.jpg`, `.jpeg`, `.webp` - Standard image formats
- `.tiff` - High-resolution climate data visualizations

### Cluster Layer Workflow

The cluster layer approach processes risk assessment data through the following pipeline:

1. **Input**: `.tif` files containing risk assessment results from eu_climate
2. **Processing**: Cluster extraction using DBSCAN and alpha-shape algorithms
3. **Output**: Web-optimized formats (`.gpkg`, `.mbtiles`, `.png`) for visualization

### Storage Structure

```
eu-data/
├── map-layers/           # Uploaded map layers (.cog, .mbtiles, .tif)
├── climate-images/       # Climate visualization images
│   ├── risk/            # Risk scenario images
│   ├── hazard/          # Hazard layer visualizations
│   ├── exposition/      # Exposition data images
│   └── combined/        # Combined assessment results
└── metadata/            # JSON metadata for all assets
```

### API Endpoints

- `POST /api/map-layers/upload` - Upload map layers (supports .tif files)
- `POST /api/storage/upload` - Upload climate images
- `GET /api/storage/upload` - List stored files by category/scenario

### Testing the Migration

To verify the migration is working correctly:

1. **Test .tif Upload**: Visit `/admin` and try uploading a `.tif` file
2. **Verify R2 Storage**: Check that files appear in the Cloudflare R2 bucket
3. **Test Large Files**: Upload files larger than 50MB (up to 500MB supported)

### Development

```bash
pnpm install
pnpm dev
```

The application will start on `http://localhost:3000` with the layer manager accessible at `/admin`.
