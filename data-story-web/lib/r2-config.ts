// Fallback public URL for development/testing
const FALLBACK_PUBLIC_URL =
  "https://pub-d032794d3f654d3eb7dfb097724ded50.r2.dev";

export const R2_CONFIG = {
  region: "auto",
  endpoint: process.env.R2_ENDPOINT!,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
  },
};

export const R2_BUCKET_NAME = process.env.R2_BUCKET_NAME!;

// Use custom domain if available, otherwise fallback to development URL
export const R2_PUBLIC_URL_BASE =
  process.env.R2_PUBLIC_URL_BASE || FALLBACK_PUBLIC_URL;

// Validate required environment variables
function validateR2Config() {
  const requiredVars = [
    "R2_ENDPOINT",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
  ];

  const missing = requiredVars.filter((varName) => !process.env[varName]);

  if (missing.length > 0) {
    throw new Error(
      `Missing required R2 environment variables: ${missing.join(", ")}`,
    );
  }
}

// Validate on import
if (typeof window === "undefined") {
  // Only validate on server side
  validateR2Config();
}
