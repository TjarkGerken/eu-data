import { NextRequest, NextResponse } from "next/server";
import {
  S3Client,
  PutObjectCommand,
  ListObjectsV2Command,
  DeleteObjectCommand,
  GetObjectCommand,
  CopyObjectCommand,
  HeadObjectCommand,
} from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME, R2_PUBLIC_URL_BASE } from "@/lib/r2-config";

const s3Client = new S3Client(R2_CONFIG);

// Helper function to extract S3 key from URL or return path as-is
function extractKeyFromPath(pathOrUrl: string): string {
  // If it's a full URL, extract just the key part
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    try {
      const url = new URL(pathOrUrl);
      // Remove leading slash and return the key
      return url.pathname.substring(1);
    } catch (e) {
      console.warn("Failed to parse URL, using as-is:", pathOrUrl);
      return pathOrUrl;
    }
  }
  return pathOrUrl;
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file") as File;
    const category = formData.get("category") as string;
    const scenario = formData.get("scenario") as string;
    const altEn = formData.get("alt_en") as string | null;
    const altDe = formData.get("alt_de") as string | null;
    const captionEn = formData.get("caption_en") as string | null;
    const captionDe = formData.get("caption_de") as string | null;
    const indicatorsRaw = formData.get("indicators") as string | null;
    let indicators: string[] | undefined;
    if (indicatorsRaw) {
      try {
        indicators = JSON.parse(indicatorsRaw);
      } catch {
        indicators = undefined;
      }
    }

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const fileExt = file.name.split(".").pop();
    const fileName = `climate-images/${category}/${
      scenario || "default"
    }/${Date.now()}.${fileExt}`;

    const buffer = Buffer.from(await file.arrayBuffer());

    const command = new PutObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: fileName,
      Body: buffer,
      ContentType: file.type || "application/octet-stream",
      CacheControl: "public, max-age=3600",
    });

    try {
      await s3Client.send(command);
    } catch (error) {
      console.error("R2 storage error:", error);
      return NextResponse.json(
        { error: "Failed to upload file to R2" },
        { status: 500 }
      );
    }

    const publicUrl = `${R2_PUBLIC_URL_BASE}/${fileName}`;

    // Save metadata file alongside upload
    const id =
      fileName.split("/").pop()?.split(".")[0] || Date.now().toString();
    const metadata = {
      id,
      category,
      scenario: scenario || "default",
      indicators,
      alt: {
        en: altEn || "",
        de: altDe || "",
      },
      caption: {
        en: captionEn || "",
        de: captionDe || "",
      },
      uploadedAt: new Date().toISOString(),
      size: file.size,
    };

    try {
      const metaKey = `metadata/${id}.json`;
      const putMeta = new PutObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: metaKey,
        Body: JSON.stringify(metadata),
        ContentType: "application/json",
        CacheControl: "public, max-age=3600",
      });
      await s3Client.send(putMeta);
    } catch (err) {
      console.error("Failed to save metadata:", err);
    }

    return NextResponse.json({
      url: publicUrl,
      path: fileName,
      category,
      scenario: scenario || "default",
      indicators: indicators || [],
      alt: {
        en: altEn || "",
        de: altDe || "",
      },
      caption: {
        en: captionEn || "",
        de: captionDe || "",
      },
    });
  } catch (error) {
    console.error("Upload error:", error);
    return NextResponse.json(
      { error: "Failed to process upload" },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const category = searchParams.get("category");
    const scenario = searchParams.get("scenario");

    let prefix = "climate-images/";
    if (category && scenario) {
      prefix += `${category}/${scenario}/`;
    } else if (category) {
      prefix += `${category}/`;
    }

    const command = new ListObjectsV2Command({
      Bucket: R2_BUCKET_NAME,
      Prefix: prefix,
      MaxKeys: 100,
    });

    const response = await s3Client.send(command);

    if (!response.Contents) {
      return NextResponse.json({ files: [] });
    }

    const files = await Promise.all(
      response.Contents.map(async (object) => {
        const publicUrl = `${R2_PUBLIC_URL_BASE}/${object.Key}`;
        const pathParts = object.Key!.split("/");
        const fileName = pathParts[pathParts.length - 1];

        let meta: Record<string, unknown> | undefined;
        try {
          const metaKey = `metadata/${fileName.split(".")[0]}.json`;
          const metaResp = await s3Client.send(
            new GetObjectCommand({ Bucket: R2_BUCKET_NAME, Key: metaKey })
          );
          if (metaResp.Body) {
            const text = await metaResp.Body.transformToString();
            meta = JSON.parse(text);
          }
        } catch {
          /* ignore metadata fetch errors */
        }

        return {
          id: fileName,
          name: fileName,
          url: publicUrl,
          path: object.Key!, // Add the actual path/key here
          category: meta?.category || pathParts[1] || "default",
          scenario: meta?.scenario || pathParts[2] || "default",
          indicators: (meta?.indicators as string[]) || [],
          alt: meta?.alt || { en: "", de: "" },
          caption: meta?.caption || { en: "", de: "" },
          size: object.Size || 0,
          created_at: object.LastModified?.toISOString(),
        };
      })
    );

    return NextResponse.json({ files });
  } catch (error) {
    console.error("List error:", error);
    return NextResponse.json(
      { error: "Failed to list files" },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { path } = (await request.json()) as { path?: string };
    if (!path) {
      return NextResponse.json({ error: "No path provided" }, { status: 400 });
    }

    // Extract the actual S3 key from the path (in case it's a full URL)
    const actualPath = extractKeyFromPath(path);
    console.log(`DELETE request for path: ${path} -> ${actualPath}`);

    const deleteCommand = new DeleteObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: actualPath,
    });

    await s3Client.send(deleteCommand);

    // Attempt to delete metadata file as well (if exists)
    const metadataKey = actualPath.replace(/\.[^/.]+$/, ".json");
    try {
      const metaDelete = new DeleteObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: metadataKey,
      });
      await s3Client.send(metaDelete);
    } catch {
      /* ignore */
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Delete error:", error);
    return NextResponse.json(
      { error: "Failed to delete file" },
      { status: 500 }
    );
  }
}

export async function PUT(request: NextRequest) {
  try {
    const { path, category, scenario, indicators, description, alt, caption } =
      (await request.json()) as {
        path: string;
        category?: string;
        scenario?: string;
        indicators?: string[];
        description?: string;
        alt?: { en: string; de: string };
        caption?: { en: string; de: string };
      };

    if (!path) {
      return NextResponse.json({ error: "No path provided" }, { status: 400 });
    }

    // Extract the actual S3 key from the path (in case it's a full URL)
    const actualPath = extractKeyFromPath(path);
    console.log(
      `PUT request to update image metadata for path: ${path} -> ${actualPath}`
    );

    const pathParts = actualPath.split("/");
    const hasPrefix = pathParts[0] === "climate-images";
    const currentCategory = hasPrefix ? pathParts[1] : pathParts[0];
    const currentScenario = hasPrefix
      ? pathParts[2]
      : pathParts[1] || "default";
    const fileName = pathParts.slice(-1)[0];

    const basePrefix = hasPrefix ? "climate-images/" : "";

    console.log(
      `Parsed path - category: ${currentCategory}, scenario: ${currentScenario}, file: ${fileName}`
    );

    let newPath = actualPath;

    // If category or scenario changed, move the object
    if (
      (category && category !== currentCategory) ||
      (scenario && scenario !== currentScenario)
    ) {
      newPath = `${basePrefix}${category || currentCategory}/${
        scenario || currentScenario
      }/${fileName}`;

      // First check if source object exists
      try {
        const headCmd = new HeadObjectCommand({
          Bucket: R2_BUCKET_NAME,
          Key: actualPath,
        });
        await s3Client.send(headCmd);

        // Copy object to new path
        const copyCmd = new CopyObjectCommand({
          Bucket: R2_BUCKET_NAME,
          CopySource: `${R2_BUCKET_NAME}/${actualPath}`,
          Key: newPath,
          CacheControl: "public, max-age=3600",
        });
        await s3Client.send(copyCmd);

        // Delete old object only if copy succeeded
        const delCmd = new DeleteObjectCommand({
          Bucket: R2_BUCKET_NAME,
          Key: actualPath,
        });
        await s3Client.send(delCmd);

        console.log(
          `Successfully moved object from ${actualPath} to ${newPath}`
        );
      } catch (e) {
        console.warn(
          `Failed to move object from ${actualPath} to ${newPath}:`,
          e
        );
        // If source doesn't exist or copy fails, continue with metadata update only
        // Reset newPath to original path since move failed
        newPath = actualPath;
      }
    }

    const id = fileName.split(".")[0];
    const metaKey = `metadata/${id}.json`;

    const newMetadata = {
      id,
      category: category || currentCategory,
      scenario: scenario || currentScenario,
      indicators: indicators || [],
      description: description || "",
      alt: alt || { en: "", de: "" },
      caption: caption || { en: "", de: "" },
      updatedAt: new Date().toISOString(),
    };

    const putMeta = new PutObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: metaKey,
      Body: JSON.stringify(newMetadata),
      ContentType: "application/json",
      CacheControl: "public, max-age=3600",
    });

    await s3Client.send(putMeta);

    console.log(`Successfully updated metadata for ${newPath}`);
    return NextResponse.json({ success: true, path: newPath });
  } catch (error) {
    console.error("Update error:", error);
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { error: `Failed to update metadata: ${errorMessage}` },
      { status: 500 }
    );
  }
}
