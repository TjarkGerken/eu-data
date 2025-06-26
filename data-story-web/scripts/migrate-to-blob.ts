import { config } from "dotenv";
import { readdir, readFile } from "fs/promises";
import { join } from "path";
import { CloudflareR2Manager } from "../lib/blob-manager";
import { ImageCategory } from "../lib/blob-config";

// Load environment variables from .env.local
config({ path: ".env.local" });

// Mapping from filename to metadata
const IMAGE_MAPPINGS = {
  "exposition_freight_loading.png": {
    id: "exposition_freight_loading",
    category: "exposition" as ImageCategory,
    scenario: "current",
    description:
      "Freight loading exposition visualization showing transportation infrastructure vulnerability",
  },
  "hazard_assessment_summary.png": {
    id: "hazard_assessment_summary",
    category: "hazard" as ImageCategory,
    scenario: "current",
    description:
      "Comprehensive hazard assessment summary across all risk factors",
  },
  "hazard_risk_current_scenario.png": {
    id: "hazard_risk_current",
    category: "hazard" as ImageCategory,
    scenario: "current",
    description: "Current scenario hazard risk assessment visualization",
  },
  "hazard_risk_severe_scenario.png": {
    id: "hazard_risk_severe",
    category: "hazard" as ImageCategory,
    scenario: "severe",
    description:
      "Severe scenario hazard risk assessment with projected impacts",
  },
  "risk_SLR-0-Current_COMBINED.png": {
    id: "risk_slr_current_combined",
    category: "risk" as ImageCategory,
    scenario: "current",
    description: "Combined risk assessment for current sea level rise scenario",
  },
  "risk_SLR-3-Severe_COMBINED.png": {
    id: "risk_slr_severe_combined",
    category: "risk" as ImageCategory,
    scenario: "severe",
    description: "Combined risk assessment for severe sea level rise scenario",
  },
  "flood_risk_relative_by_scenario.png": {
    id: "flood_risk_relative",
    category: "combined" as ImageCategory,
    scenario: "comparison",
    description: "Relative flood risk comparison across different scenarios",
  },
};

async function migrateImages() {
  console.log("Starting image migration to Cloudflare R2 Storage...");

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
          const result = await CloudflareR2Manager.uploadImage(file, metadata);

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
        `\n🎉 All climate visualization images are now served from Cloudflare R2 Storage CDN!`
      );
    }
  } catch (error) {
    console.error("❌ Migration failed:", error);
    process.exit(1);
  }
}

migrateImages();
