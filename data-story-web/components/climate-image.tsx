"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { CloudflareR2Image, ImageMetadata } from "@/lib/blob-manager";
import { ImageCategory, ImageScenario } from "@/lib/blob-config";
import { SupabaseAnalytics } from "@/lib/blob-analytics";

interface ClimateImageProps {
  category: ImageCategory;
  scenario?: ImageScenario;
  id?: string;
  alt: string;
  className?: string;
  priority?: boolean;
  fill?: boolean;
  width?: number;
  height?: number;
  onMetadataLoaded?: (metadata: ImageMetadata | undefined) => void;
}

export default function ClimateImage({
  category,
  scenario,
  id,
  alt,
  className,
  priority = false,
  fill = true,
  width,
  height,
  onMetadataLoaded,
}: ClimateImageProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [, setMetadata] = useState<ImageMetadata | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadImage() {
      try {
        let targetImage: CloudflareR2Image | null = null;

        const response = await fetch(`/api/images/${category}`);
        if (!response.ok) {
          throw new Error("Failed to fetch images");
        }

        const data = await response.json();
        const imageList = data.images as CloudflareR2Image[];

        if (id) {
          targetImage =
            imageList.find(
              (imageItem) =>
                imageItem.metadata?.id === id &&
                (!scenario || imageItem.metadata?.scenario === scenario)
            ) || null;
        } else {
          targetImage =
            imageList.find(
              (imageItem) =>
                !scenario || imageItem.metadata?.scenario === scenario
            ) ||
            imageList[0] ||
            null;
        }

        if (targetImage) {
          setImageUrl(targetImage.url);

          let richMetadata: ImageMetadata | undefined = targetImage.metadata;

          if (richMetadata?.id) {
            try {
              const metaRes = await fetch(`/api/metadata/${richMetadata.id}`);

              if (metaRes.ok) {
                richMetadata = (await metaRes.json()) as ImageMetadata;
              }
            } catch {}
          }

          setMetadata(richMetadata);

          if (onMetadataLoaded) {
            onMetadataLoaded(richMetadata);
          }

          SupabaseAnalytics.trackImageView(targetImage.url, category, scenario);
        } else {
          setError(
            `No image found for ${category}${scenario ? ` - ${scenario}` : ""}${
              id ? ` (${id})` : ""
            }`
          );
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load image");
      } finally {
        setLoading(false);
      }
    }

    loadImage();
  }, [category, scenario, id, onMetadataLoaded]);

  if (loading) {
    return (
      <div
        className={`animate-pulse bg-gray-200 rounded ${className || ""}`}
        style={{ aspectRatio: "16/9", width: width, height: height }}
      />
    );
  }

  if (error || !imageUrl) {
    return (
      <div
        className={`bg-gray-100 rounded p-4 text-center text-gray-500 ${
          className || ""
        }`}
      >
        {error || "Image not available"}
      </div>
    );
  }

  const imageProps = {
    src: imageUrl,
    alt,
    className,
    priority,
    sizes: "(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw",
  };

  if (fill) {
    return <Image {...imageProps} alt={alt} fill />;
  }

  return (
    <Image
      {...imageProps}
      alt={alt}
      width={width || 800}
      height={height || 450}
    />
  );
}
