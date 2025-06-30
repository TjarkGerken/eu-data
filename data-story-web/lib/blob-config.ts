export const BLOB_CONFIG = {
  maxFileSize: 500 * 1024 * 1024, // 500MB for R2 storage
  allowedTypes: [
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/tiff",
    "image/tif",
    "application/x-mbtiles",
    "application/octet-stream",
  ],
  cacheControl: "public, max-age=31536000, immutable",
  categories: [
    "hazard",
    "exposition",
    "relevance",
    "risk",
    "risk-clusters",
  ] as const,
  scenarios: [
    "current",
    "conservative",
    "moderate",
    "severe",
    "none",
    "all",
  ] as const,
  economicIndicators: [
    "freight",
    "hrst",
    "gdp",
    "population",
    "combined",
    "none",
  ] as const,
};

export type ImageCategory = (typeof BLOB_CONFIG.categories)[number];
export type ImageScenario = (typeof BLOB_CONFIG.scenarios)[number];
export type EconomicIndicator = (typeof BLOB_CONFIG.economicIndicators)[number];
