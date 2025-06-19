import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import { promises as fs } from "fs";
import path from "path";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

interface ProcessingResult {
  success: boolean;
  outputPath?: string;
  error?: string;
  size?: number;
}

export async function POST(request: NextRequest) {
  const tempDir = path.join(process.cwd(), "temp");
  let tempInputPath: string | null = null;
  let tempOutputPath: string | null = null;

  try {
    // Ensure temp directory exists
    await fs.mkdir(tempDir, { recursive: true });

    const formData = await request.formData();
    const file = formData.get("file") as File;
    const layerName = formData.get("layerName") as string;
    const layerType = formData.get("layerType") as string;

    if (!file || !layerName) {
      return NextResponse.json(
        { error: "File and layer name are required" },
        { status: 400 }
      );
    }

    const fileExtension = file.name.split(".").pop()?.toLowerCase();

    if (!["tif", "tiff", "gpkg", "geojson"].includes(fileExtension || "")) {
      return NextResponse.json(
        {
          error:
            "Unsupported file type. Please upload .tif, .tiff, .gpkg, or .geojson files",
        },
        { status: 400 }
      );
    }

    // Save uploaded file temporarily
    const tempFileName = `${Date.now()}_${file.name}`;
    tempInputPath = path.join(tempDir, tempFileName);

    const buffer = Buffer.from(await file.arrayBuffer());
    await fs.writeFile(tempInputPath, buffer);

    console.log(`Processing ${fileExtension} file: ${tempInputPath}`);

    // Process the file based on type
    let processingResult: ProcessingResult;

    if (fileExtension === "tif" || fileExtension === "tiff") {
      processingResult = await optimizeGeoTIFF(tempInputPath, layerName);
    } else if (fileExtension === "gpkg") {
      processingResult = await optimizeGeoPackage(tempInputPath, layerName);
    } else if (fileExtension === "geojson") {
      processingResult = await optimizeGeoJSON(tempInputPath, layerName);
    } else {
      throw new Error(`Unsupported file extension: ${fileExtension}`);
    }

    if (!processingResult.success || !processingResult.outputPath) {
      throw new Error(processingResult.error || "File processing failed");
    }

    tempOutputPath = processingResult.outputPath;

    // Read the optimized file
    const optimizedBuffer = await fs.readFile(tempOutputPath);
    const optimizedFile = new File(
      [optimizedBuffer],
      path.basename(tempOutputPath),
      {
        type: getOptimizedMimeType(tempOutputPath),
      }
    );

    console.log(
      `Original size: ${file.size} bytes, Optimized size: ${optimizedBuffer.length} bytes`
    );

    // Upload to Supabase
    const { data, error } = await supabase.storage
      .from("map-layers")
      .upload(path.basename(tempOutputPath), optimizedFile, {
        cacheControl: "3600",
        upsert: true,
      });

    if (error) {
      console.error("Upload error:", error);
      throw new Error(`Failed to upload optimized file: ${error.message}`);
    }

    const { data: publicUrlData } = supabase.storage
      .from("map-layers")
      .getPublicUrl(path.basename(tempOutputPath));

    return NextResponse.json({
      success: true,
      layerId: layerName,
      fileName: path.basename(tempOutputPath),
      url: publicUrlData.publicUrl,
      originalSize: file.size,
      optimizedSize: optimizedBuffer.length,
      compressionRatio: Math.round(
        (1 - optimizedBuffer.length / file.size) * 100
      ),
      message: "Layer uploaded and optimized successfully",
    });
  } catch (error) {
    console.error("Server error:", error);
    return NextResponse.json(
      {
        error: "Failed to process and upload file",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  } finally {
    // Clean up temporary files
    try {
      if (tempInputPath) await fs.unlink(tempInputPath);
      if (tempOutputPath) await fs.unlink(tempOutputPath);
    } catch (cleanupError) {
      console.warn("Failed to clean up temp files:", cleanupError);
    }
  }
}

async function optimizeGeoTIFF(
  inputPath: string,
  layerName: string
): Promise<ProcessingResult> {
  try {
    // First try to create a PNG for web display (works with any bit depth)
    const pngOutputPath = path.join(
      path.dirname(inputPath),
      `${layerName}_optimized.png`
    );

    // Convert to PNG with significant downsampling for web display
    const pngCommand = `gdal_translate -of PNG -outsize 10% 10% -scale "${inputPath}" "${pngOutputPath}"`;

    console.log(`Running GDAL PNG command: ${pngCommand}`);
    try {
      const { stdout: pngStdout, stderr: pngStderr } = await execAsync(
        pngCommand
      );

      // Check PNG size
      const pngStats = await fs.stat(pngOutputPath);
      console.log(`PNG size: ${pngStats.size} bytes`);

      // If PNG is small enough (< 50MB), use it
      if (pngStats.size < 50 * 1024 * 1024) {
        return {
          success: true,
          outputPath: pngOutputPath,
          size: pngStats.size,
        };
      }

      // Clean up PNG if too large
      await fs.unlink(pngOutputPath);
    } catch (pngError) {
      console.log("PNG conversion failed, trying COG:", pngError);
    }

    // Fallback: try COG with LZW compression
    const cogOutputPath = path.join(
      path.dirname(inputPath),
      `${layerName}_optimized.tif`
    );

    const cogCommand = `gdal_translate -of COG -co COMPRESS=LZW -co PREDICTOR=2 -co OVERVIEW_RESAMPLING=AVERAGE -co BLOCKSIZE=512 -outsize 15% 15% "${inputPath}" "${cogOutputPath}"`;

    console.log(`Running GDAL COG command: ${cogCommand}`);
    const { stdout: cogStdout, stderr: cogStderr } = await execAsync(
      cogCommand
    );

    if (cogStderr && !cogStderr.includes("Warning")) {
      throw new Error(`GDAL error: ${cogStderr}`);
    }

    const cogStats = await fs.stat(cogOutputPath);

    return {
      success: true,
      outputPath: cogOutputPath,
      size: cogStats.size,
    };
  } catch (error) {
    console.error("GeoTIFF optimization failed:", error);
    return {
      success: false,
      error:
        error instanceof Error ? error.message : "GeoTIFF processing failed",
    };
  }
}

async function optimizeGeoPackage(
  inputPath: string,
  layerName: string
): Promise<ProcessingResult> {
  try {
    const outputPath = path.join(
      path.dirname(inputPath),
      `${layerName}_optimized.geojson`
    );

    // Convert to optimized GeoJSON with coordinate precision
    const command = `ogr2ogr -f GeoJSON -lco COORDINATE_PRECISION=6 -simplify 0.0001 "${outputPath}" "${inputPath}"`;

    console.log(`Running OGR command: ${command}`);
    const { stdout, stderr } = await execAsync(command);

    if (stderr && !stderr.includes("Warning")) {
      throw new Error(`OGR error: ${stderr}`);
    }

    const stats = await fs.stat(outputPath);

    return {
      success: true,
      outputPath,
      size: stats.size,
    };
  } catch (error) {
    console.error("GeoPackage optimization failed:", error);
    return {
      success: false,
      error:
        error instanceof Error ? error.message : "GeoPackage processing failed",
    };
  }
}

async function optimizeGeoJSON(
  inputPath: string,
  layerName: string
): Promise<ProcessingResult> {
  try {
    const outputPath = path.join(
      path.dirname(inputPath),
      `${layerName}_optimized.geojson`
    );

    // Read and optimize GeoJSON (remove precision, simplify if needed)
    const geojsonData = JSON.parse(await fs.readFile(inputPath, "utf-8"));

    // Round coordinates to 6 decimal places for optimization
    if (geojsonData.features) {
      geojsonData.features.forEach((feature: any) => {
        if (feature.geometry && feature.geometry.coordinates) {
          feature.geometry.coordinates = roundCoordinates(
            feature.geometry.coordinates,
            6
          );
        }
      });
    }

    await fs.writeFile(outputPath, JSON.stringify(geojsonData), "utf-8");
    const stats = await fs.stat(outputPath);

    return {
      success: true,
      outputPath,
      size: stats.size,
    };
  } catch (error) {
    console.error("GeoJSON optimization failed:", error);
    return {
      success: false,
      error:
        error instanceof Error ? error.message : "GeoJSON processing failed",
    };
  }
}

function roundCoordinates(coords: any, precision: number): any {
  if (typeof coords[0] === "number") {
    return coords.map(
      (coord: number) =>
        Math.round(coord * Math.pow(10, precision)) / Math.pow(10, precision)
    );
  }
  return coords.map((coord: any) => roundCoordinates(coord, precision));
}

function getOptimizedMimeType(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case ".tif":
    case ".tiff":
      return "image/tiff";
    case ".png":
      return "image/png";
    case ".geojson":
      return "application/geo+json";
    default:
      return "application/octet-stream";
  }
}
