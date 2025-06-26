import { NextRequest, NextResponse } from "next/server";
import { R2_PUBLIC_URL_BASE } from "@/lib/r2-config";
import path from "path";
import { promises as fs } from "fs";
import { exec } from "child_process";
import { promisify } from "util";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ scenario: string }> }
) {
  try {
    const { scenario } = await params;

    if (!scenario) {
      return NextResponse.json(
        { error: "Scenario parameter is required" },
        { status: 400 }
      );
    }

    const geoPackagePath = getClusterGeoPackagePath(scenario);

    try {
      // Try to get from R2 storage first
      const publicUrl = `${R2_PUBLIC_URL_BASE}/${geoPackagePath}`;

      const response = await fetch(publicUrl);
      if (!response.ok) {
        throw new Error("Cluster file not found in R2");
      }

      const buffer = Buffer.from(await response.arrayBuffer());

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
    } catch (r2Error) {
      console.error("R2 storage error:", r2Error);

      // Fallback to local file if R2 fails
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

async function convertGeoPackageToGeoJSON(
  buffer: Buffer
): Promise<object | null> {
  try {
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

async function loadLocalClusterFile(filePath: string): Promise<object | null> {
  try {
    const fileContent = await fs.readFile(filePath, "utf8");
    return JSON.parse(fileContent);
  } catch (error) {
    console.error("Local file loading error:", error);
    return null;
  }
}
