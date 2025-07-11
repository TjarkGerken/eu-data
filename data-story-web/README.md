# EU Climate Data Story Web Application

A sophisticated Next.js application for interactive climate data storytelling with comprehensive content management capabilities. This platform combines modern web technologies with specialized scientific data visualization for European climate risk assessment communication.

## 🎯 Overview

This application serves as an interactive data story platform that transforms complex climate risk assessment data into compelling, accessible narratives. Built with Next.js 15 and React 19, it features a dynamic block-based content system, advanced mapping capabilities, and a powerful admin interface for content management.

### Core Capabilities

- **Interactive Data Storytelling**: Dynamic, block-based content system with 15+ specialized visualization types
- **Advanced Mapping**: Multiple map layers with scientific data overlays xand real-time interaction
- **Multilingual CMS**: Complete bilingual content management (English/German) with admin interface
- **Scientific Visualization**: Specialized components for climate dashboards, statistics, and impact analysis
- **Academic Integration**: Citation management system with global reference processing
- **Cloud Storage**: Cloudflare R2 integration supporting large geospatial files up to 500MB

## 🏗️ Architecture

### Technology Stack

**Core Framework:**

- **Next.js 15.2.4** with App Router and React 19
- **TypeScript** with strict configuration for type safety
- **Tailwind CSS** with shadcn/ui component library
- **Turbopack** for optimized development

**Data & Storage:**

- **Supabase** for database management and real-time features
- **Cloudflare R2** for large file storage (S3-compatible)

**Mapping & Geospatial:**

- **Leaflet** with advanced plugins for interactive maps
- **Turf.js** for geospatial data processing
- **Proj4** for coordinate system transformations
- **Vector tiles** with dynamic styling support

**Additional Libraries:**

- **Framer Motion** for animations and transitions
- **React Hook Form** with Zod validation
- **Recharts** for data visualization
- **AWS SDK** for Cloudflare R2 integration

### Application Structure

```
data-story-web/
├── app/                          # Next.js App Router
│   ├── (main)/                   # Main story pages
│   ├── admin/                    # Admin interface
│   ├── api/                      # API routes
│   │   ├── content/              # Content management endpoints
│   │   ├── map-data/             # Map data serving
│   │   ├── map-layers/           # Layer management
│   │   ├── images/               # Image handling
│   │   └── storage/              # File storage operations
│   └── gallery/                  # Image gallery
├── components/                   # React components
│   ├── admin/                    # Admin-specific components
│   ├── blocks/                   # Content block components
│   ├── maps/                     # Mapping components
│   └── ui/                       # Reusable UI components
├── contexts/                     # React contexts (i18n, auth)
├── lib/                          # Utilities and services
├── database/                     # Database migrations
├── hooks/                        # Custom React hooks
└── public/                       # Static assets
```

## 🧩 Content Management System

### Dynamic Block System

The application features a sophisticated block-based content architecture with 15+ specialized block types:

**Core Content Blocks:**

- **Markdown Block**: Rich text with markdown support
- **Callout Block**: Highlighted information boxes
- **Animated Quote**: Dynamic quotations with visual effects
- **Animated Statistics**: Interactive statistical displays
- **Climate Dashboard**: Comprehensive climate data visualization
- **Interactive Callout**: Engaging interactive content
- **Impact Comparison**: Side-by-side impact analysis
- **KPI Showcase**: Key performance indicator displays

**Advanced Visualization Blocks:**

- **Interactive Maps**: Leaflet-based mapping with custom layers
- **Infrastructure Maps**: Transportation and infrastructure visualization
- **Economic Indicators**: Financial impact visualization
- **Hero Video**: Landing page video integration

### Admin Interface (`/admin`)

**Content Management (`/admin/content`):**

- Multilingual story editing (English/German)
- Visual block editor with real-time preview
- Reference management with citation linking
- Block ordering and content validation

**Image Management (`/admin/images`):**

- Multi-category support (Hazard, Risk, Exposition, Combined)
- Automatic scenario detection
- Thumbnail generation and preview
- Cloudflare R2 integration for large files

**Layer Management:**

- Interactive map layer administration
- Vector and raster layer styling
- Upload support for .tif, .cog, .mbtiles files
- Dynamic layer ordering and visibility controls

## 🗺️ Advanced Mapping System

### Map Components

**Interactive Map (`components/maps/interactive-map.tsx`):**

- Multi-layer climate data visualization
- Economic indicator overlay
- Dynamic styling and filtering
- Real-time data interaction

**Infrastructure Map (`components/maps/infrastructure-map.tsx`):**

- Transportation network visualization
- Port and logistics data display
- Economic impact analysis

### Map Data APIs

**Vector Tile Serving:**

- Dynamic tile generation at `/api/map-data/vector/[layerId]/[z]/[x]/[y]`
- Style management for vector layers
- Real-time layer updates

**Raster Data Handling:**

- Cloud Optimized GeoTIFF (COG) support
- Color scheme management
- Multi-resolution tile serving

**Cluster Analysis:**

- Dynamic cluster data at `/api/map-data/clusters/[scenario]`
- DBSCAN algorithm integration
- Alpha-shape polygon generation

## 📊 Database Schema

### Core Tables (Supabase)

**Content Management:**

```sql
content_stories       # Story metadata (titles, descriptions, language)
content_blocks        # Dynamic content blocks with JSON data
content_references    # Academic citations and bibliography
block_references      # Many-to-many block-citation relationships
```

**Asset Management:**

```sql
climate_images        # Image metadata with blob storage URLs
layer_styles          # Map layer styling configurations
```

### Migration System

Automated database migrations in `database/migrations/`:

- Schema evolution tracking
- Layer style management
- Reference system enhancements
- Content block field additions

## 🔧 Development

### Quick Start

```bash
# Install dependencies
pnpm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development server
pnpm dev

# Build for production
pnpm build

# Type checking
pnpm type-check
```

### Environment Configuration

Create `.env.local` with the following variables:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Cloudflare R2 Storage (Required)
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET_NAME=eu-data

# Custom Domain (Optional)
R2_PUBLIC_URL_BASE=https://tjarkgerken.com/eu-data

# Authentication
AUTH_SECRET=your_auth_secret
```

### Development Commands

```bash
# Package management with pnpm
pnpm install                    # Install dependencies
pnpm dev                       # Development server with Turbopack
pnpm build                     # Production build
pnpm start                     # Start production server
pnpm lint                      # ESLint checking
pnpm type-check               # TypeScript validation
pnpm db:migrate               # Run database migrations
pnpm db:generate              # Generate database types
```

## 📋 API Reference

### Content Management APIs

```
GET  /api/content              # Fetch content blocks
POST /api/content              # Create new content blocks
PUT  /api/content              # Update content blocks
GET  /api/stories              # Fetch story metadata
POST /api/stories              # Create new stories
```

### File Management APIs

```
POST /api/images/upload        # Upload climate images
GET  /api/images/[category]    # Fetch category images
POST /api/storage/upload       # General file upload
GET  /api/storage/upload       # List stored files
```

### Map Data APIs

```
GET  /api/map-data/vector/[layerId]/[z]/[x]/[y]  # Vector tiles
GET  /api/map-data/cog/[layerId]                 # Raster tiles
GET  /api/map-data/clusters/[scenario]           # Cluster data
POST /api/map-layers/upload                      # Layer upload
GET  /api/map-layers/[layerId]                   # Layer metadata
```

## 🗂️ File Support

### Supported Formats

**Map Layers:**

- `.cog` - Cloud Optimized GeoTIFF (raster data)
- `.mbtiles` - Vector tiles for interactive maps
- `.tif`, `.tiff` - TIFF raster data for cluster processing
- `.gpkg` - GeoPackage vector data

**Climate Images:**

- `.png`, `.jpg`, `.jpeg`, `.webp` - Standard image formats
- `.tiff` - High-resolution climate data visualizations

### Storage Capabilities

- **File Size Limit**: Up to 500MB per file
- **Storage Backend**: Cloudflare R2 with S3-compatible API
- **CDN Integration**: Custom domain support for fast delivery
- **Metadata Tracking**: Comprehensive file metadata and versioning

## 📖 Further Documentation

- **EU Climate Framework**: See `../eu_climate/README.md` for data processing
- **Database Schema**: Check `database/migrations/` for structure
- **Component Library**: Explore `components/ui/` for reusable components
- **API Documentation**: Review individual endpoint files in `app/api/`

For technical support and detailed implementation information, refer to individual component documentation and the configuration files.
