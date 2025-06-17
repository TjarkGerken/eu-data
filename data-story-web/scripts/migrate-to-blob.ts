import { config } from "dotenv";
import { readdir, readFile } from "fs/promises";
import { join } from "path";
import { BlobImageManager } from "../lib/blob-manager";

// Load environment variables from .env.local
config({ path: ".env.local" });

const IMAGE_MAPPINGS = {
  "exposition_freight_loading.png": {
    category: "exposition",
    id: "freight-loading",
    description: "Freight loading exposition data",
  },
  "exposition_layer.png": {
    category: "exposition",
    id: "layer-overview",
    description: "Exposition layer visualization",
  },
  "hazard_risk_current_scenario.png": {
    category: "hazard",
    id: "current-scenario",
    scenario: "current",
    description: "Current hazard risk scenario",
  },
  "hazard_risk_severe_scenario.png": {
    category: "hazard",
    id: "severe-scenario",
    scenario: "severe",
    description: "Severe hazard risk scenario",
  },
  "risk_SLR-0-Current_COMBINED.png": {
    category: "risk",
    id: "slr-current",
    scenario: "current",
    description: "Sea level rise current scenario",
  },
  "risk_SLR-3-Severe_COMBINED.png": {
    category: "risk",
    id: "slr-severe",
    scenario: "severe",
    description: "Sea level rise severe scenario",
  },
  "flood_risk_relative_by_scenario.png": {
    category: "risk",
    id: "flood-relative",
    description: "Flood risk relative by scenario",
  },
} as const;

async function migrateImages() {
  console.log("Starting image migration to Vercel Blob Storage...");

  const publicDir = join(process.cwd(), "public");

  try {
    const imageFiles = await readdir(publicDir);
    let migratedCount = 0;
    let skippedCount = 0;

    for (const filename of imageFiles) {
      if (filename.endsWith(".png") && filename in IMAGE_MAPPINGS) {
        try {
          const filePath = join(publicDir, filename);
          const fileBuffer = await readFile(filePath);
          const file = new File([fileBuffer], filename, { type: "image/png" });

          const metadata =
            IMAGE_MAPPINGS[filename as keyof typeof IMAGE_MAPPINGS];
          const result = await BlobImageManager.uploadImage(file, metadata);

          console.log(`✅ Migrated ${filename} -> ${result.url}`);
          migratedCount++;
        } catch (error) {
          console.error(`❌ Failed to migrate ${filename}:`, error);
          skippedCount++;
        }
      }
    }

    console.log(`\n📊 Migration complete:`);
    console.log(`  - Successfully migrated: ${migratedCount} images`);
    console.log(`  - Skipped/Failed: ${skippedCount} images`);

    if (migratedCount > 0) {
      console.log(
        `\n🎉 All climate visualization images are now served from Vercel Blob Storage CDN!`
      );
    }
  } catch (error) {
    console.error("❌ Migration failed:", error);
    process.exit(1);
  }
}

export default migrateImages;

if (require.main === module) {
  migrateImages();
}
