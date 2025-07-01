"use client";

import { useState, useEffect } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
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
import { Reference } from "@/lib/types";

interface ReferencesDropdownProps {
  selectedReferences: string[];
  onReferencesChange: (references: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
}

const typeColors = {
  journal: "bg-blue-100 text-blue-800",
  report: "bg-green-100 text-green-800",
  dataset: "bg-purple-100 text-purple-800",
  book: "bg-orange-100 text-orange-800",
};

export function ReferencesDropdown({
  selectedReferences,
  onReferencesChange,
  placeholder = "Select references...",
  disabled = false,
}: ReferencesDropdownProps) {
  const [open, setOpen] = useState(false);
  const [references, setReferences] = useState<Reference[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReferences();
  }, []);

  const loadReferences = async () => {
    try {
      const response = await fetch("/api/content");
      const data = await response.json();
      setReferences(data.references || []);
    } catch (error) {
      console.error("Failed to load references:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleReference = (referenceId: string) => {
    if (selectedReferences.includes(referenceId)) {
      onReferencesChange(selectedReferences.filter((id) => id !== referenceId));
    } else {
      onReferencesChange([...selectedReferences, referenceId]);
    }
  };

  const getSelectedReferenceNames = () => {
    return selectedReferences
      .map((id) => references.find((ref) => ref.id === id))
      .filter(Boolean)
      .map((ref) => {
        if (!ref || !ref.id || !ref.title) return '';
        return `[${ref.id}] ${ref.title.substring(0, 30)}${
          ref.title.length > 30 ? "..." : ""
        }`;
      })
      .filter(Boolean);
  };

  if (loading) {
    return (
      <Button variant="outline" disabled className="w-full justify-between">
        Loading references...
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
          className="w-full justify-between min-h-[40px] h-auto"
          disabled={disabled}
        >
          <div className="flex flex-wrap gap-1 flex-1">
            {selectedReferences.length === 0 ? (
              <span className="text-muted-foreground">{placeholder}</span>
            ) : selectedReferences.length === 1 ? (
              <span>{getSelectedReferenceNames()[0]}</span>
            ) : (
              <div className="flex flex-wrap gap-1">
                {selectedReferences.slice(0, 2).map((id) => (
                  <Badge key={id} variant="secondary" className="text-xs">
                    [{id}]
                  </Badge>
                ))}
                {selectedReferences.length > 2 && (
                  <Badge variant="secondary" className="text-xs">
                    +{selectedReferences.length - 2}
                  </Badge>
                )}
              </div>
            )}
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0">
        <Command>
          <CommandInput placeholder="Search references..." />
          <CommandList>
            <CommandEmpty>No references found.</CommandEmpty>
            <CommandGroup>
              {references.map((reference) => (
                <CommandItem
                  key={reference.id}
                  value={`${reference.id} ${
                    reference.title
                  } ${reference.authors.join(" ")}`}
                  onSelect={() => toggleReference(reference.id)}
                  className="flex items-start gap-3 p-3"
                >
                  <Check
                    className={cn(
                      "h-4 w-4 mt-1 shrink-0",
                      selectedReferences.includes(reference.id)
                        ? "opacity-100"
                        : "opacity-0"
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        className={`text-xs ${typeColors[reference.type]}`}
                      >
                        {reference.type}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        [{reference.id}]
                      </span>
                    </div>
                    <p className="font-medium text-sm leading-tight">
                      {reference.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {reference.authors.join(", ")} ({reference.year})
                    </p>
                    {reference.journal && (
                      <p className="text-xs text-muted-foreground italic">
                        {reference.journal}
                      </p>
                    )}
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
