import { NextRequest, NextResponse } from "next/server";
import {
  S3Client,
  PutObjectCommand,
  ListObjectsV2Command,
} from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME, R2_PUBLIC_URL_BASE } from "@/lib/r2-config";

const s3Client = new S3Client(R2_CONFIG);

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file") as File;
    const category = formData.get("category") as string;
    const scenario = formData.get("scenario") as string;

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

    return NextResponse.json({
      url: publicUrl,
      path: fileName,
      category,
      scenario: scenario || "default",
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

    const files = response.Contents.map((object) => {
      const publicUrl = `${R2_PUBLIC_URL_BASE}/${object.Key}`;
      const pathParts = object.Key!.split("/");
      const fileName = pathParts[pathParts.length - 1];

      return {
        id: fileName,
        name: fileName,
        url: publicUrl,
        category: category || "default",
        scenario: scenario || "default",
        size: object.Size || 0,
        created_at: object.LastModified?.toISOString(),
      };
    });

    return NextResponse.json({ files });
  } catch (error) {
    console.error("List error:", error);
    return NextResponse.json(
      { error: "Failed to list files" },
      { status: 500 }
    );
  }
}
