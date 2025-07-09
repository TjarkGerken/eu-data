"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { CloudflareR2Image, ImageMetadata } from "@/lib/blob-manager";
import { ImageCategory, ImageScenario } from "@/lib/blob-config";

interface ClimateImageProps {
  category: ImageCategory;
  scenario?: ImageScenario;
  id?: string;
  alt: string;
  className?: string;
  priority?: boolean;
  fill?: boolean; // Default: true - fills container. Set false for fixed dimensions
  width?: number; // Only used when fill=false
  height?: number; // Only used when fill=false
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
  const [targetImage, setTargetImage] = useState<CloudflareR2Image | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchImages = async () => {
      try {
        setLoading(true);
        setError(null);

        let images: CloudflareR2Image[];

        if (category) {
          const response = await fetch(`/api/images/${category}`);
          if (!response.ok) {
            throw new Error(`Failed to fetch images: ${response.statusText}`);
          }
          const data = await response.json();
          images = data.images || [];
        } else {
          const response = await fetch("/api/images");
          if (!response.ok) {
            throw new Error(`Failed to fetch images: ${response.statusText}`);
          }
          const data = await response.json();
          images = data.images || [];
        }

        if (!Array.isArray(images) || images.length === 0) {
          setError("No images found");
          return;
        }

        let filteredImages = images;

        if (scenario && scenario !== "none") {
          filteredImages = images.filter(
            (img) => img.metadata?.scenario === scenario
          );
        }

        if (id) {
          filteredImages = filteredImages.filter(
            (img) => img.metadata?.id === id
          );
        }

        if (filteredImages.length === 0) {
          filteredImages = images;
        }

        const image = filteredImages[0];
        setTargetImage(image);

        if (onMetadataLoaded) {
          console.log("image.metadata", image.metadata);
          onMetadataLoaded(image.metadata);
        }

        // Track image view
      } catch (err) {
        console.error("Error fetching images:", err);
        setError(err instanceof Error ? err.message : "Failed to load image");
      } finally {
        setLoading(false);
      }
    };

    fetchImages();
  }, [category, scenario, id, onMetadataLoaded]);

  if (loading) {
    return <div className={`${className} bg-muted animate-pulse`} />;
  }

  if (error || !targetImage) {
    return (
      <div className={`${className} bg-muted flex items-center justify-center`}>
        <span className="text-muted-foreground text-sm">
          {error || "Image not found"}
        </span>
      </div>
    );
  }

  // Warn developers about missing dimensions when fill=false
  if (!fill && (!width || !height)) {
    console.warn(
      "ClimateImage: When fill=false, both width and height must be provided to avoid Next.js Image errors"
    );
  }

  return (
    <Image
      src={targetImage.url}
      alt={alt}
      className={className}
      priority={priority}
      fill={fill}
      width={!fill && width ? width : undefined}
      height={!fill && height ? height : undefined}
      sizes={
        fill
          ? "(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          : undefined
      }
    />
  );
}
