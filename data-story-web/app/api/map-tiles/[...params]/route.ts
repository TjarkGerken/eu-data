import { NextRequest, NextResponse } from "next/server";
import { createCanvas, loadImage, ImageData } from "canvas";
import sharp from "sharp";
import { get } from "@vercel/blob";

interface TileRequest {
  layerName: string;
  zoom: number;
  x: number;
  y: number;
}

const TILE_SIZE = 256;
const MAX_ZOOM = 18;

export async function GET(
  request: NextRequest,
  { params }: { params: { params: string[] } }
) {
  try {
    if (!params.params || params.params.length < 4) {
      return NextResponse.json(
        { error: "Invalid tile request" },
        { status: 400 }
      );
    }

    const [layerName, zoomStr, xStr, yStr] = params.params;
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
      const cachedTile = await getCachedTile(cacheKey);
      if (cachedTile) {
        return new NextResponse(cachedTile, {
          headers: {
            "Content-Type": "image/png",
            "Cache-Control": "public, max-age=86400",
          },
        });
      }
    } catch (cacheError) {
      console.warn("Cache miss for tile:", cacheKey);
    }

    const tileBuffer = await generateTile({ layerName, zoom, x, y });

    await cacheTile(cacheKey, tileBuffer);

    return new NextResponse(tileBuffer, {
      headers: {
        "Content-Type": "image/png",
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch (error) {
    console.error("Error generating tile:", error);
    return NextResponse.json(
      { error: "Failed to generate tile" },
      { status: 500 }
    );
  }
}

async function generateTile(tileRequest: TileRequest): Promise<Buffer> {
  const { layerName, zoom, x, y } = tileRequest;

  const sourceFilePath = getSourceFilePath(layerName);

  const tileExtent = getTileExtent(x, y, zoom);

  const extractedRegion = await extractRegionFromGeoTiff(
    sourceFilePath,
    tileExtent
  );

  const tileBuffer = await renderTileWithColormap(extractedRegion, layerName);

  return tileBuffer;
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

async function extractRegionFromGeoTiff(
  filePath: string,
  extent: [number, number, number, number]
): Promise<ImageData> {
  const image = sharp(filePath);
  const metadata = await image.metadata();

  const resized = await image
    .extract({
      left: Math.floor(extent[0] * (metadata.width || 1)),
      top: Math.floor(extent[1] * (metadata.height || 1)),
      width: Math.floor((extent[2] - extent[0]) * (metadata.width || 1)),
      height: Math.floor((extent[3] - extent[1]) * (metadata.height || 1)),
    })
    .resize(TILE_SIZE, TILE_SIZE)
    .raw()
    .toBuffer();

  return new ImageData(new Uint8ClampedArray(resized), TILE_SIZE, TILE_SIZE);
}

async function renderTileWithColormap(
  imageData: ImageData,
  layerName: string
): Promise<Buffer> {
  const canvas = createCanvas(TILE_SIZE, TILE_SIZE);
  const ctx = canvas.getContext("2d");

  const colormap = getColormapForLayer(layerName);

  for (let i = 0; i < imageData.data.length; i += 4) {
    const value = imageData.data[i];
    const normalizedValue = value / 255;
    const color = interpolateColor(colormap, normalizedValue);

    imageData.data[i] = color.r;
    imageData.data[i + 1] = color.g;
    imageData.data[i + 2] = color.b;
    imageData.data[i + 3] = value === 0 ? 0 : 255;
  }

  ctx.putImageData(imageData, 0, 0);

  return canvas.toBuffer("image/png");
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

function getSourceFilePath(layerName: string): string {
  return `./public/risk/${layerName}.tif`;
}

async function getCachedTile(key: string): Promise<Buffer | null> {
  try {
    const response = await get(`cache/${key}`);
    return Buffer.from(await response.arrayBuffer());
  } catch {
    return null;
  }
}

async function cacheTile(key: string, buffer: Buffer): Promise<void> {
  // Implement caching to Vercel Blob or similar
}
