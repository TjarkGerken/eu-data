"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Badge } from "@/components/ui/badge";
import { Quote, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface Reference {
  id: string;
  title: string;
  authors: string[];
  year: number;
  type: "journal" | "report" | "dataset" | "book";
  readable_id: string;
}

interface CitationInsertionButtonProps {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  onContentChange: (content: string) => void;
  availableReferences: Reference[];
}

const typeColors = {
  journal: "bg-blue-100 text-blue-800",
  report: "bg-green-100 text-green-800",
  dataset: "bg-purple-100 text-purple-800",
  book: "bg-orange-100 text-orange-800",
};

export function CitationInsertionButton({
  textareaRef,
  onContentChange,
  availableReferences,
}: CitationInsertionButtonProps) {
  const [open, setOpen] = useState(false);
  const [selectedReference, setSelectedReference] = useState<string>("");
  const [cursorPosition, setCursorPosition] = useState<number>(0);

  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen && textareaRef.current) {
      setCursorPosition(textareaRef.current.selectionStart || 0);
    }
    setOpen(newOpen);
  };

  const getReadableIdForReference = (refId: string): string => {
    const reference = availableReferences.find((r) => r?.id === refId);
    return reference?.readable_id || refId;
  };

  const insertCitation = (referenceId: string) => {
    if (!textareaRef.current) return;

    const textarea = textareaRef.current;
    const currentContent = textarea.value;
    const readableId = getReadableIdForReference(referenceId);
    const citationText = `\\cite{${readableId}}`;

    const newContent =
      currentContent.slice(0, cursorPosition) +
      citationText +
      currentContent.slice(cursorPosition);

    onContentChange(newContent);

    setOpen(false);
    setSelectedReference("");

    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        const newPosition = cursorPosition + citationText.length;
        textareaRef.current.setSelectionRange(newPosition, newPosition);
      }
    }, 100);
  };

  const handleReferenceSelect = (referenceId: string) => {
    setSelectedReference(referenceId);
    insertCitation(referenceId);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="flex items-center gap-2"
          title="Insert citation"
        >
          <Quote className="h-4 w-4" />
          Insert Citation
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle>Insert Citation</DialogTitle>
          <DialogDescription>
            Select a reference to insert as a citation at the current cursor
            position. This will insert <code>\cite{`{ReadableId}`}</code> syntax
            using human-readable identifiers like <code>Smith2023</code> instead
            of technical IDs.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden">
          <Command className="h-full">
            <CommandInput placeholder="Search references..." />
            <CommandList className="max-h-[400px] overflow-y-auto">
              <CommandEmpty>No references found.</CommandEmpty>
              <CommandGroup>
                {availableReferences.map((reference) => (
                  <CommandItem
                    key={reference.id}
                    value={`${reference.id} ${
                      reference.title
                    } ${reference.authors.join(" ")}`}
                    onSelect={() => handleReferenceSelect(reference.id)}
                    className="flex items-start gap-3 p-3 cursor-pointer"
                  >
                    <Check
                      className={cn(
                        "h-4 w-4 mt-1 shrink-0",
                        selectedReference === reference.id
                          ? "opacity-100"
                          : "opacity-0",
                      )}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge
                          className={`text-xs ${typeColors[reference.type]}`}
                        >
                          {reference.type}
                        </Badge>
                        <span className="text-xs text-muted-foreground font-mono">
                          {getReadableIdForReference(reference.id)}
                        </span>
                      </div>
                      <p className="font-medium text-sm leading-tight">
                        {reference.title}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {reference.authors.join(", ")} ({reference.year})
                      </p>
                      <div className="mt-2 p-2 bg-muted rounded text-xs font-mono">
                        <code>
                          \cite{`{${getReadableIdForReference(reference.id)}}`}
                        </code>
                      </div>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </div>
      </DialogContent>
    </Dialog>
  );
}
