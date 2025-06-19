import { NextRequest, NextResponse } from "next/server";
import { get } from "@vercel/blob";
import path from "path";

export async function GET(
  request: NextRequest,
  { params }: { params: { scenario: string } }
) {
  try {
    const { scenario } = params;

    if (!scenario) {
      return NextResponse.json(
        { error: "Scenario parameter is required" },
        { status: 400 }
      );
    }

    const geoPackagePath = getClusterGeoPackagePath(scenario);

    try {
      const geoPackageBlob = await get(geoPackagePath);
      const buffer = Buffer.from(await geoPackageBlob.arrayBuffer());

      const geoJsonData = await convertGeoPackageToGeoJSON(buffer);

      if (!geoJsonData) {
        return NextResponse.json(
          { error: "No cluster data found for scenario" },
          { status: 404 }
        );
      }

      return NextResponse.json(geoJsonData, {
        headers: {
          "Cache-Control": "public, max-age=3600",
          "Content-Type": "application/json",
        },
      });
    } catch (blobError) {
      console.error("Blob storage error:", blobError);

      const localFilePath = getLocalClusterFilePath(scenario);

      try {
        const localGeoJsonData = await loadLocalClusterFile(localFilePath);

        if (!localGeoJsonData) {
          return NextResponse.json(
            { error: "Cluster data not available" },
            { status: 404 }
          );
        }

        return NextResponse.json(localGeoJsonData, {
          headers: {
            "Cache-Control": "public, max-age=3600",
            "Content-Type": "application/json",
          },
        });
      } catch (localError) {
        console.error("Local file error:", localError);
        return NextResponse.json(
          { error: "Cluster data not available" },
          { status: 404 }
        );
      }
    }
  } catch (error) {
    console.error("Error serving cluster data:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

function getClusterGeoPackagePath(scenario: string): string {
  return `clusters/${scenario}/clusters_${scenario}_COMBINED.gpkg`;
}

function getLocalClusterFilePath(scenario: string): string {
  return path.join(
    process.cwd(),
    "public",
    "clusters",
    scenario,
    `clusters_${scenario}_COMBINED.geojson`
  );
}

async function convertGeoPackageToGeoJSON(buffer: Buffer): Promise<any> {
  try {
    const fs = require("fs").promises;
    const { exec } = require("child_process");
    const { promisify } = require("util");
    const execAsync = promisify(exec);

    const tempGpkgPath = `/tmp/temp_${Date.now()}.gpkg`;
    const tempGeojsonPath = `/tmp/temp_${Date.now()}.geojson`;

    await fs.writeFile(tempGpkgPath, buffer);

    await execAsync(`ogr2ogr -f GeoJSON ${tempGeojsonPath} ${tempGpkgPath}`);

    const geoJsonBuffer = await fs.readFile(tempGeojsonPath);
    const geoJsonData = JSON.parse(geoJsonBuffer.toString());

    await fs.unlink(tempGpkgPath).catch(() => {});
    await fs.unlink(tempGeojsonPath).catch(() => {});

    return geoJsonData;
  } catch (error) {
    console.error("GeoPackage conversion error:", error);
    return null;
  }
}

async function loadLocalClusterFile(filePath: string): Promise<any> {
  try {
    const fs = require("fs").promises;

    const fileContent = await fs.readFile(filePath, "utf8");
    return JSON.parse(fileContent);
  } catch (error) {
    console.error("Local file loading error:", error);
    return null;
  }
}
