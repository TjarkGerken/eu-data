# Content Block Types - Required Attributes

This document outlines all available content block types and their required form field attributes for the Content Block Editor.

## 1. markdown

**Description**: Simple markdown content rendering
**Required Fields**:

- `content` (textarea): Markdown text content

## 2. callout

**Description**: Styled alert/callout box with icon
**Required Fields**:

- `title` (text): Callout title
- `content` (textarea): Callout content text
- `variant` (select): Type of callout
  - Options: `success`, `warning`, `info`, `error`

## 3. animated-quote

**Description**: Animated quote block with author attribution
**Required Fields**:

- `text` (textarea): Quote text content
- `author` (text): Author name
- `role` (text): Author's role/position (optional)

## 4. animated-statistics

**Description**: Animated cards displaying statistics with icons
**Required Fields**:

- `title` (text): Block title (optional)
- `description` (textarea): Block description (optional)
- `stats` (dynamic array): Array of statistics
  - Each stat requires:
    - `icon` (select): Icon name
      - Options: `thermometer`, `droplets`, `wind`, `zap`, `barchart`, `globe`, `trending`
    - `value` (text): Statistical value (e.g., "42%", "1.5°C")
    - `label` (text): Description label
    - `change` (text): Change indicator (optional, e.g., "+0.3°C")
    - `trend` (select): Trend direction (optional)
      - Options: `up`, `down`
    - `color` (select): Color class for styling
      - Options: `text-blue-500`, `text-red-500`, `text-green-500`, `text-orange-500`, `text-purple-500`

## 5. climate-timeline

**Description**: Timeline of climate events with icons and colors
**Required Fields**:

- `title` (text): Timeline title (optional)
- `description` (textarea): Timeline description (optional)
- `events` (dynamic array): Array of timeline events
  - Each event requires:
    - `year` (number): Event year
    - `title` (text): Event title
    - `description` (textarea): Event description
    - `type` (select): Event type
      - Options: `temperature`, `precipitation`, `policy`, `extreme`
    - `icon` (select): Lucide icon name
      - Options: `thermometer`, `cloud-rain`, `scroll-text`, `zap`, `alert-triangle`, `trending-up`
    - `color` (color): Hex color for event marker (e.g., "#ef4444")

## 6. climate-dashboard

**Description**: Dashboard with climate metrics and progress tracking
**Required Fields**:

- `title` (text): Dashboard title (optional)
- `description` (textarea): Dashboard description (optional)
- `metrics` (dynamic array): Array of climate metrics
  - Each metric requires:
    - `title` (text): Metric title
    - `value` (text): Current value (e.g., "1.1°C", "415 ppm")
    - `change` (text): Change indicator (e.g., "+0.1°C/decade")
    - `trend` (select): Trend direction
      - Options: `up`, `down`
    - `status` (select): Status indicator
      - Options: `success`, `warning`, `danger`
    - `progress` (number): Progress percentage (0-100)
    - `target` (text): Target description
    - `description` (textarea): Metric description

## 7. temperature-spiral

**Description**: Animated temperature spiral visualization
**Required Fields**:

- `title` (text): Spiral title (optional)
- `description` (textarea): Spiral description (optional)
- `startYear` (number): Starting year (default: 1880)
- `endYear` (number): Ending year (default: 2030)
- `rotations` (number): Number of spiral rotations (default: 8)

## 8. interactive-callout

**Description**: Interactive expandable callout block
**Required Fields**:

- `title` (text): Callout title
- `content` (textarea): Callout content (supports multi-line)
- `variant` (select): Visual variant
  - Options: `success`, `warning`, `info`, `error`
- `interactive` (checkbox): Enable interactive behavior (default: true)

## 9. visualization

**Description**: Climate data visualization with image display
**Required Fields**:

- `data` (nested object):
  - `title` (text): Visualization title
  - `description` (textarea): Visualization description
  - `content` (textarea): Additional content text
  - `type` (select): Visualization type
    - Options: `map`, `chart`, `trend`, `gauge`
  - `imageCategory` (select): Image category
    - Options: `exposition`, `hazard`, `risk`, `combined`
  - `imageScenario` (select): Climate scenario (optional)
    - Options: `current`, `severe`
  - `imageId` (text): Specific image identifier (optional)
  - `references` (multi-select): Reference IDs

**Available Images**:
These should be dynamically fetched from the blob and stored in a multi-select. The multi select should contain a small preview of the picture and the file title

- Risk images: `risk_SLR-0-Current_COMBINED.png`, `risk_SLR-3-Severe_COMBINED.png`
- Hazard images: `hazard_risk_current_scenario.png`, `hazard_risk_severe_scenario.png`
- Exposition images: `exposition_layer.png`, `exposition_freight_loading.png`
- Other: `flood_risk_relative_by_scenario.png`

## 10. impact-comparison

**Description**: Predefined impact comparison visualization
**Required Fields**:

- `title` (text): Block title (optional)
- `description` (textarea): Block description (optional)
  **Note**: Uses predefined data from motion-blocks component

## 11. kpi-showcase

**Description**: Predefined KPI showcase visualization
**Required Fields**:

- `title` (text): Block title (optional)
- `description` (textarea): Block description (optional)
  **Note**: Uses predefined data from motion-blocks component

## 12. climate-timeline-minimal

**Description**: Minimal timeline layout
**Required Fields**:

- `title` (text): Timeline title (optional)
- `description` (textarea): Timeline description (optional)
- `events` (dynamic array): Simple timeline events
  - Each event requires:
    - `year` (number): Event year
    - `title` (text): Event title
    - `description` (textarea): Event description

## 13. climate-infographic

**Description**: Predefined climate infographic
**Required Fields**:

- `title` (text): Block title (optional)
- `description` (textarea): Block description (optional)
  **Note**: Uses predefined data from motion-blocks component

## Predefined Motion Blocks (No Configuration Required)

The following blocks use predefined animations and data:

- `neural-climate-network`
- `earth-pulse`
- `carbon-molecule-dance`
- `data-storm`
- `climate-map-static`
- `climate-metamorphosis`

These blocks only need:

- `title` (text): Block title (optional)
- `description` (textarea): Block description (optional)

## Legacy Blocks (Deprecated)

- `quote`: Use `animated-quote` instead
- `statistics`: Use `animated-statistics` instead

## Form Field Types Reference

- **text**: Single-line text input
- **textarea**: Multi-line text input
- **number**: Numeric input with validation
- **select**: Dropdown with predefined options
- **multi-select**: Multiple selection dropdown
- **checkbox**: Boolean toggle
- **color**: Color picker input
- **dynamic array**: Expandable form sections for collections

## Image Dropdown Configuration

For visualization blocks, the image selector should:

1. Filter images by selected category
2. Show thumbnails with names
3. Do not Include scenario filtering
4. Allow "no image" option for placeholder visualization

## Validation Rules

- All required fields must be filled before saving
- Array fields must have at least one item where specified
- Color fields must be valid hex codes
- Number fields must be within reasonable ranges
- References must exist in the database and should be handled via the existing multi-select
