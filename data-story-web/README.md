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
content.json
├── references[]          # Global bibliography
├── en/                  # English content
│   ├── heroTitle
│   ├── heroDescription
│   ├── dataStoryTitle
│   ├── introText1
│   ├── introText2
│   └── visualizations[]
└── de/                  # German content
    └── [same structure]
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

- `GET /api/content` - Fetch all content
- `PUT /api/content` - Update content
- `GET /api/images/[category]` - Fetch category images
- `POST /api/images/upload` - Upload new images

## Key Features

✅ **References Tab**: Complete bibliography management
✅ **Reference Dropdowns**: Visual selection for visualizations  
✅ **Image Previews**: Thumbnail-based image selection
✅ **Multi-language**: English/German content editing
✅ **Real-time Updates**: Changes appear immediately
✅ **Type Safety**: Full TypeScript coverage
