"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { Check, ChevronsUpDown, Image as ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { ImageOption } from "@/lib/types";

interface ImageDropdownProps {
  selectedImageId?: string;
  onImageChange: (
    imageId: string,
    imageData?: {
      category: string;
      scenario?: string;
      caption?: { en: string; de: string };
    }
  ) => void;
  placeholder?: string;
  disabled?: boolean;
  category?: string;
}

export function ImageDropdown({
  selectedImageId,
  onImageChange,
  placeholder = "Select image...",
  disabled = false,
  category,
}: ImageDropdownProps) {
  const [open, setOpen] = useState(false);
  const [images, setImages] = useState<ImageOption[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadImages();
  }, []);

  const loadImages = async () => {
    try {
      console.log("Loading all images from API...");
      const response = await fetch("/api/images");
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to fetch images");
      }

      console.log("Received images data:", data);

      const formattedImages = (data.images || [])
        .map(
          (img: {
            path?: string;
            url: string;
            metadata?: {
              id?: string;
              category?: string;
              scenario?: string;
              caption?: string;
            };
          }) => {
            const filename =
              img.path?.split("/").pop() || img.metadata?.id || "unknown";
            console.log({
              id: img.metadata?.id || filename,
              name: filename,
              url: img.url,
              category: img.metadata?.category || "unknown",
              scenario: img.metadata?.scenario,
              caption: img.metadata?.caption,
            });
            return {
              id: img.metadata?.id || filename,
              name: filename,
              url: img.url,
              category: img.metadata?.category || "unknown",
              scenario: img.metadata?.scenario,
              caption: img.metadata?.caption,
            };
          }
        )
        .filter((img: ImageOption) => img.url && img.name !== "unknown");

      console.log("Formatted images:", formattedImages);
      setImages(formattedImages);
    } catch (error) {
      console.error("Failed to load images:", error);
      setImages([]);
    } finally {
      setLoading(false);
    }
  };

  // Filter images by category if specified
  const filteredImages = category
    ? images.filter((img) => img.category === category)
    : images;

  const selectedImage = filteredImages.find(
    (img) => img.id === selectedImageId
  );

  if (loading) {
    return (
      <Button variant="outline" disabled className="w-full justify-between">
        Loading images...
        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Button>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between h-auto min-h-[40px]"
          disabled={disabled}
        >
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {selectedImage ? (
              <>
                <Image
                  src={selectedImage.url}
                  alt={selectedImage.name}
                  width={32}
                  height={24}
                  className="object-cover rounded border"
                />
                <div className="flex flex-col items-start min-w-0">
                  <span className="text-sm truncate">{selectedImage.name}</span>
                  <div className="flex gap-1">
                    <Badge variant="secondary" className="text-xs">
                      {selectedImage.category}
                    </Badge>
                    {selectedImage.scenario && (
                      <Badge variant="outline" className="text-xs">
                        {selectedImage.scenario}
                      </Badge>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <>
                <ImageIcon className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">
                  {placeholder}
                  {!loading && ` (${filteredImages.length} available)`}
                </span>
              </>
            )}
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[500px] p-0">
        <Command>
          <CommandInput placeholder="Search images..." />
          <CommandList>
            <CommandEmpty>
              {loading
                ? "Loading images..."
                : `No images found${
                    category ? ` for category "${category}"` : ""
                  }.`}
            </CommandEmpty>
            <CommandGroup>
              {filteredImages.map((image) => (
                <CommandItem
                  key={image.id}
                  value={`${image.name} ${image.category} ${
                    image.scenario || ""
                  }`}
                  onSelect={() => {
                    onImageChange(image.id, {
                      category: image.category,
                      scenario: image.scenario,
                      caption: image.caption,
                    });
                    setOpen(false);
                  }}
                  className="flex items-center gap-3 p-3"
                >
                  <Check
                    className={cn(
                      "h-4 w-4 shrink-0",
                      selectedImageId === image.id ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <Image
                    src={image.url}
                    alt={image.name}
                    width={64}
                    height={48}
                    className="object-cover rounded border shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm">{image.name}</p>
                    <div className="flex gap-1 mt-1">
                      <Badge variant="secondary" className="text-xs">
                        {image.category}
                      </Badge>
                      {image.scenario && (
                        <Badge variant="outline" className="text-xs">
                          {image.scenario}
                        </Badge>
                      )}
                    </div>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
