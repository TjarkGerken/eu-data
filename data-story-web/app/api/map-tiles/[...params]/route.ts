import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import sharp from "sharp";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let createCanvas: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let CanvasImageData: any = null;
let canvasAvailable = false;

const TILE_SIZE = 256;
const MAX_ZOOM = 10;

async function initializeCanvas() {
  if (canvasAvailable) return;

  try {
    const canvas = await import("canvas");
    createCanvas = canvas.createCanvas;
    CanvasImageData = canvas.ImageData;
    canvasAvailable = true;
    console.log("Canvas initialized successfully");
  } catch (error) {
    console.warn("Canvas not available:", error);
    canvasAvailable = false;
  }
}

interface TileRequest {
  layerName: string;
  zoom: number;
  x: number;
  y: number;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ params: string[] }> }
) {
  try {
    const resolvedParams = await params;

    if (!resolvedParams.params || resolvedParams.params.length < 4) {
      return NextResponse.json(
        { error: "Invalid tile request" },
        { status: 400 }
      );
    }

    const [layerName, zoomStr, xStr, yStr] = resolvedParams.params;
    const zoom = parseInt(zoomStr);
    const x = parseInt(xStr);
    const y = parseInt(yStr.replace(".png", ""));

    if (isNaN(zoom) || isNaN(x) || isNaN(y)) {
      return NextResponse.json(
        { error: "Invalid coordinates" },
        { status: 400 }
      );
    }

    if (zoom > MAX_ZOOM) {
      return NextResponse.json(
        { error: "Zoom level too high" },
        { status: 400 }
      );
    }

    const cacheKey = `map-tile-${layerName}-${zoom}-${x}-${y}`;

    try {
      const cachedTile = await getCachedTile();
      if (cachedTile) {
        return new NextResponse(cachedTile, {
          headers: {
            "Content-Type": "image/png",
            "Cache-Control": "public, max-age=86400",
          },
        });
      }
    } catch {
      console.warn("Cache miss for tile:", cacheKey);
    }

    const tileBuffer = await generateTile({ layerName, zoom, x, y });

    await cacheTile();

    return new NextResponse(tileBuffer, {
      headers: {
        "Content-Type": "image/png",
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch (error) {
    console.error("Error generating tile:", error);

    // Return a transparent tile as fallback
    const fallbackTile = await generateFallbackTile();
    return new NextResponse(fallbackTile, {
      headers: {
        "Content-Type": "image/png",
        "Cache-Control": "public, max-age=300", // Shorter cache for errors
      },
    });
  }
}

async function generateFallbackTile(): Promise<Buffer> {
  // Generate a simple transparent tile using Sharp
  return await sharp({
    create: {
      width: TILE_SIZE,
      height: TILE_SIZE,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    },
  })
    .png()
    .toBuffer();
}

async function generateTile(tileRequest: TileRequest): Promise<Buffer> {
  const { layerName, zoom, x, y } = tileRequest;

  // Try to get the file from Supabase storage
  const sourceBuffer = await getSourceFileFromStorage(layerName);
  if (!sourceBuffer) {
    console.warn(`Source file not found in storage: ${layerName}`);
    return generateFallbackTile();
  }

  try {
    const tileExtent = getTileExtent(x, y, zoom);
    const extractedRegion = await extractRegionFromBuffer(
      sourceBuffer,
      tileExtent
    );
    const tileBuffer = await renderTileWithColormap(extractedRegion, layerName);
    return tileBuffer;
  } catch (error) {
    console.error(`Error generating tile for ${layerName}:`, error);
    return generateFallbackTile();
  }
}

function getTileExtent(
  x: number,
  y: number,
  zoom: number
): [number, number, number, number] {
  const n = Math.pow(2, zoom);
  const lonDeg = (x / n) * 360.0 - 180.0;
  const latRad = Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n)));
  const latDeg = (latRad * 180.0) / Math.PI;

  const lonDegNext = ((x + 1) / n) * 360.0 - 180.0;
  const latRadNext = Math.atan(Math.sinh(Math.PI * (1 - (2 * (y + 1)) / n)));
  const latDegNext = (latRadNext * 180.0) / Math.PI;

  return [lonDeg, latDegNext, lonDegNext, latDeg];
}

async function extractRegionFromBuffer(
  buffer: Buffer,
  extent: [number, number, number, number]
): Promise<{ data: Uint8ClampedArray; width: number; height: number }> {
  const image = sharp(buffer);
  const metadata = await image.metadata();

  if (!metadata.width || !metadata.height) {
    throw new Error("Invalid image metadata");
  }

  // Calculate extract bounds with better validation
  const left = Math.max(
    0,
    Math.floor((extent[0] * metadata.width) / 360 + metadata.width / 2)
  );
  const top = Math.max(
    0,
    Math.floor(((90 - extent[3]) * metadata.height) / 180)
  );
  const width = Math.min(
    metadata.width - left,
    Math.floor(((extent[2] - extent[0]) * metadata.width) / 360)
  );
  const height = Math.min(
    metadata.height - top,
    Math.floor(((extent[3] - extent[1]) * metadata.height) / 180)
  );

  if (
    width <= 0 ||
    height <= 0 ||
    left >= metadata.width ||
    top >= metadata.height
  ) {
    // Return transparent data for invalid regions
    const transparentData = new Uint8ClampedArray(TILE_SIZE * TILE_SIZE * 4);
    return {
      data: transparentData,
      width: TILE_SIZE,
      height: TILE_SIZE,
    };
  }

  try {
    const resized = await image
      .extract({ left, top, width, height })
      .resize(TILE_SIZE, TILE_SIZE)
      .ensureAlpha()
      .raw()
      .toBuffer();

    return {
      data: new Uint8ClampedArray(resized),
      width: TILE_SIZE,
      height: TILE_SIZE,
    };
  } catch (error) {
    console.warn("Extract failed, returning transparent tile:", error);
    const transparentData = new Uint8ClampedArray(TILE_SIZE * TILE_SIZE * 4);
    return {
      data: transparentData,
      width: TILE_SIZE,
      height: TILE_SIZE,
    };
  }
}

async function renderTileWithColormap(
  imageData: { data: Uint8ClampedArray; width: number; height: number },
  layerName: string
): Promise<Buffer> {
  await initializeCanvas();

  if (!canvasAvailable || !createCanvas || !CanvasImageData) {
    // Fallback to Sharp-based rendering without canvas
    return await renderTileWithSharp(imageData, layerName);
  }

  try {
    const canvas = createCanvas(TILE_SIZE, TILE_SIZE);
    const ctx = canvas.getContext("2d");

    const colormap = getColormapForLayer(layerName);
    const canvasImageData = new CanvasImageData(
      imageData.data,
      TILE_SIZE,
      TILE_SIZE
    );

    // Apply colormap
    for (let i = 0; i < canvasImageData.data.length; i += 4) {
      const value = canvasImageData.data[i];
      const normalizedValue = value / 255;
      const color = interpolateColor(colormap, normalizedValue);

      canvasImageData.data[i] = color.r;
      canvasImageData.data[i + 1] = color.g;
      canvasImageData.data[i + 2] = color.b;
      canvasImageData.data[i + 3] = value === 0 ? 0 : 255;
    }

    ctx.putImageData(canvasImageData, 0, 0);
    return canvas.toBuffer("image/png");
  } catch (error) {
    console.warn("Canvas rendering failed, using Sharp fallback:", error);
    return await renderTileWithSharp(imageData, layerName);
  }
}

async function renderTileWithSharp(
  imageData: { data: Uint8ClampedArray; width: number; height: number },
  layerName: string
): Promise<Buffer> {
  // Simple Sharp-based rendering without colormap for now
  const colormap = getColormapForLayer(layerName);
  const baseColor = colormap[Math.floor(colormap.length / 2)];

  return await sharp({
    create: {
      width: TILE_SIZE,
      height: TILE_SIZE,
      channels: 4,
      background: {
        r: baseColor.r,
        g: baseColor.g,
        b: baseColor.b,
        alpha: 0.7,
      },
    },
  })
    .png()
    .toBuffer();
}

function getColormapForLayer(
  layerName: string
): Array<{ r: number; g: number; b: number }> {
  const colormaps = {
    risk: [
      { r: 255, g: 255, b: 255 },
      { r: 255, g: 255, b: 0 },
      { r: 255, g: 165, b: 0 },
      { r: 255, g: 0, b: 0 },
    ],
    hazard: [
      { r: 173, g: 216, b: 230 },
      { r: 0, g: 191, b: 255 },
      { r: 0, g: 0, b: 255 },
      { r: 0, g: 0, b: 139 },
    ],
    exposition: [
      { r: 255, g: 255, b: 255 },
      { r: 144, g: 238, b: 144 },
      { r: 34, g: 139, b: 34 },
      { r: 0, g: 100, b: 0 },
    ],
  };

  return colormaps[layerName as keyof typeof colormaps] || colormaps.risk;
}

function interpolateColor(
  colormap: Array<{ r: number; g: number; b: number }>,
  value: number
): { r: number; g: number; b: number } {
  if (value <= 0) return colormap[0];
  if (value >= 1) return colormap[colormap.length - 1];

  const scaledValue = value * (colormap.length - 1);
  const index = Math.floor(scaledValue);
  const fraction = scaledValue - index;

  const color1 = colormap[index];
  const color2 = colormap[index + 1] || color1;

  return {
    r: Math.round(color1.r + (color2.r - color1.r) * fraction),
    g: Math.round(color1.g + (color2.g - color1.g) * fraction),
    b: Math.round(color1.b + (color2.b - color1.b) * fraction),
  };
}

async function getSourceFileFromStorage(
  layerId: string
): Promise<Buffer | null> {
  try {
    // Try different possible file extensions and names
    const possibleFileNames = [
      `${layerId}.tif`,
      `${layerId}.tiff`,
      `${layerId}.png`,
      `${layerId}_optimized.tif`,
      `${layerId}_optimized.tiff`,
      `${layerId}_optimized.png`,
    ];

    for (const fileName of possibleFileNames) {
      try {
        const { data, error } = await supabase.storage
          .from("map-layers")
          .download(fileName);

        if (!error && data) {
          const arrayBuffer = await data.arrayBuffer();
          return Buffer.from(arrayBuffer);
        }
      } catch (downloadError) {
        // Continue trying other file names
        console.warn(`Could not download ${fileName}:`, downloadError);
      }
    }

    console.warn(`No source file found for layer: ${layerId}`);
    return null;
  } catch (error) {
    console.error("Error getting source file from storage:", error);
    return null;
  }
}

async function getCachedTile(): Promise<Buffer | null> {
  // Simple in-memory cache implementation
  // In production, you'd want Redis or similar
  return null;
}

async function cacheTile(): Promise<void> {
  // Simple in-memory cache implementation
  // In production, you'd want Redis or similar
}
