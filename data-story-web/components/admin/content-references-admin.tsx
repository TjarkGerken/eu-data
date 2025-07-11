"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Trash2,
  Plus,
  Save,
  X,
  Edit,
  AlertCircle,
  CheckCircle,
  RefreshCw,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import type { ContentReference, ContentReferenceInsert } from "@/lib/supabase";
import { useToast } from "@/hooks/use-toast";
import {
  generateUniqueReadableId,
  validateReadableIdUniqueness,
  sanitizeReadableId,
} from "@/lib/readable-id-utils";

export default function ContentReferencesAdmin() {
  const [references, setReferences] = useState<ContentReference[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    title: "",
    authors: [] as string[],
    year: new Date().getFullYear(),
    journal: "",
    url: "",
    type: "journal" as "journal" | "book" | "website" | "report",
    readable_id: "",
  });

  const [readableIdValidation, setReadableIdValidation] = useState<{
    isValidating: boolean;
    isValid: boolean | null;
    suggestedId?: string;
    message?: string;
  }>({
    isValidating: false,
    isValid: null,
  });

  const loadReferences = useCallback(async () => {
    setIsLoading(true);
    try {
      const { data, error } = await supabase
        .from("content_references")
        .select("*")
        .order("created_at", { ascending: false });

      if (error) throw error;
      setReferences(data || []);
    } catch (error) {
      toast({
        title: "Error loading references",
        description:
          error instanceof Error ? error.message : "Failed to load references",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadReferences();
  }, [loadReferences]);

  const resetForm = () => {
    setFormData({
      title: "",
      authors: [],
      year: new Date().getFullYear(),
      journal: "",
      url: "",
      type: "journal" as "journal" | "book" | "website" | "report",
      readable_id: "",
    });
    setReadableIdValidation({
      isValidating: false,
      isValid: null,
    });
  };

  const validateReadableId = async (readableId: string) => {
    if (!readableId.trim()) {
      setReadableIdValidation({
        isValidating: false,
        isValid: false,
        message: "Readable ID is required",
      });
      return;
    }

    setReadableIdValidation({ isValidating: true, isValid: null });

    try {
      const result = await validateReadableIdUniqueness(
        readableId,
        editingId || undefined
      );

      setReadableIdValidation({
        isValidating: false,
        isValid: result.isValid,
        suggestedId: result.suggestedId,
        message: result.isValid
          ? "ID is available"
          : `ID already exists${
              result.suggestedId ? `. Suggested: ${result.suggestedId}` : ""
            }`,
      });
    } catch {
      setReadableIdValidation({
        isValidating: false,
        isValid: false,
        message: "Error validating ID",
      });
    }
  };

  const generateReadableIdFromForm = async () => {
    if (formData.authors.length === 0 || !formData.authors[0].trim()) {
      toast({
        title: "Cannot generate ID",
        description: "Please add at least one author first",
        variant: "destructive",
      });
      return;
    }

    try {
      const readableId = await generateUniqueReadableId({
        authors: formData.authors,
        year: formData.year,
        excludeId: editingId || undefined,
      });

      setFormData((prev) => ({ ...prev, readable_id: readableId }));
      setReadableIdValidation({
        isValidating: false,
        isValid: true,
        message: "ID generated successfully",
      });
    } catch (error) {
      toast({
        title: "Error generating ID",
        description:
          error instanceof Error ? error.message : "Failed to generate ID",
        variant: "destructive",
      });
    }
  };

  const handleSave = async () => {
    if (!formData.title.trim()) {
      toast({
        title: "Validation Error",
        description: "Title is required",
        variant: "destructive",
      });
      return;
    }

    if (
      formData.authors.length === 0 ||
      formData.authors.every((author) => !author.trim())
    ) {
      toast({
        title: "Validation Error",
        description: "At least one author is required",
        variant: "destructive",
      });
      return;
    }

    if (!formData.readable_id.trim()) {
      toast({
        title: "Validation Error",
        description: "Readable ID is required",
        variant: "destructive",
      });
      return;
    }

    if (readableIdValidation.isValid === false) {
      toast({
        title: "Validation Error",
        description: "Please fix the readable ID before saving",
        variant: "destructive",
      });
      return;
    }

    try {
      if (editingId) {
        const { error } = await supabase
          .from("content_references")
          .update(formData)
          .eq("id", editingId);

        if (error) throw error;
        toast({ title: "Reference updated successfully" });
      } else {
        const insertData: ContentReferenceInsert = {
          ...formData,
          id: crypto.randomUUID(),
        };
        const { error } = await supabase
          .from("content_references")
          .insert([insertData]);

        if (error) throw error;
        toast({ title: "Reference created successfully" });
      }

      setEditingId(null);
      setShowNewForm(false);
      resetForm();
      loadReferences();
    } catch (error) {
      toast({
        title: editingId
          ? "Error updating reference"
          : "Error creating reference",
        description:
          error instanceof Error ? error.message : "Operation failed",
        variant: "destructive",
      });
    }
  };

  const handleEdit = (reference: ContentReference) => {
    setFormData({
      title: reference.title,
      authors: reference.authors,
      year: reference.year,
      journal: reference.journal || "",
      url: reference.url || "",
      type: reference.type as "journal" | "book" | "website" | "report",
      readable_id: reference.readable_id,
    });
    setReadableIdValidation({
      isValidating: false,
      isValid: true,
      message: "Current ID",
    });
    setEditingId(reference.id);
    setShowNewForm(false);
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this reference?")) return;

    try {
      const { error } = await supabase
        .from("content_references")
        .delete()
        .eq("id", id);

      if (error) throw error;
      toast({ title: "Reference deleted successfully" });
      loadReferences();
    } catch (error) {
      toast({
        title: "Error deleting reference",
        description:
          error instanceof Error ? error.message : "Failed to delete reference",
        variant: "destructive",
      });
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setShowNewForm(false);
    resetForm();
  };

  const addAuthor = () => {
    setFormData((prev) => ({ ...prev, authors: [...prev.authors, ""] }));
  };

  const updateAuthor = (index: number, value: string) => {
    setFormData((prev) => ({
      ...prev,
      authors: prev.authors.map((author, i) => (i === index ? value : author)),
    }));
  };

  const removeAuthor = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      authors: prev.authors.filter((_, i) => i !== index),
    }));
  };

  if (isLoading) {
    return <div>Loading references...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Content References</h2>
        <Button
          onClick={() => setShowNewForm(true)}
          disabled={editingId !== null || showNewForm}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Reference
        </Button>
      </div>

      {(showNewForm || editingId) && (
        <Card>
          <CardHeader>
            <CardTitle>
              {editingId ? "Edit Reference" : "New Reference"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, title: e.target.value }))
                }
                placeholder="Reference title"
              />
            </div>

            <div>
              <Label>Authors</Label>
              <div className="space-y-2">
                {formData.authors.map((author, index) => (
                  <div key={index} className="flex gap-2">
                    <Input
                      value={author}
                      onChange={(e) => updateAuthor(index, e.target.value)}
                      placeholder="Author name"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => removeAuthor(index)}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addAuthor}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Author
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="year">Year</Label>
                <Input
                  id="year"
                  type="number"
                  value={formData.year}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      year: parseInt(e.target.value),
                    }))
                  }
                />
              </div>
              <div>
                <Label htmlFor="type">Type</Label>
                <Select
                  value={formData.type}
                  onValueChange={(value) =>
                    setFormData((prev) => ({
                      ...prev,
                      type: value as "journal" | "book" | "website" | "report",
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="journal">Journal</SelectItem>
                    <SelectItem value="book">Book</SelectItem>
                    <SelectItem value="website">Website</SelectItem>
                    <SelectItem value="report">Report</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label htmlFor="readable_id">Readable ID</Label>
              <div className="flex gap-2">
                <Input
                  id="readable_id"
                  value={formData.readable_id}
                  onChange={(e) => {
                    const sanitized = sanitizeReadableId(e.target.value);
                    setFormData((prev) => ({
                      ...prev,
                      readable_id: sanitized,
                    }));
                    if (sanitized !== e.target.value) {
                      // Show user that input was sanitized
                      setTimeout(() => validateReadableId(sanitized), 100);
                    } else {
                      validateReadableId(sanitized);
                    }
                  }}
                  placeholder="e.g., Smith2023"
                  className={
                    readableIdValidation.isValid === false
                      ? "border-red-500"
                      : readableIdValidation.isValid === true
                      ? "border-green-500"
                      : ""
                  }
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={generateReadableIdFromForm}
                  disabled={readableIdValidation.isValidating}
                  title="Generate ID from author and year"
                >
                  {readableIdValidation.isValidating ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                </Button>
              </div>

              {readableIdValidation.message && (
                <div className="mt-1 flex items-center gap-1 text-sm">
                  {readableIdValidation.isValid === true ? (
                    <CheckCircle className="w-3 h-3 text-green-600" />
                  ) : readableIdValidation.isValid === false ? (
                    <AlertCircle className="w-3 h-3 text-red-600" />
                  ) : null}
                  <span
                    className={
                      readableIdValidation.isValid === true
                        ? "text-green-600"
                        : readableIdValidation.isValid === false
                        ? "text-red-600"
                        : "text-gray-600"
                    }
                  >
                    {readableIdValidation.message}
                  </span>
                  {readableIdValidation.suggestedId && (
                    <Button
                      type="button"
                      variant="link"
                      size="sm"
                      className="h-auto p-0 ml-2 text-xs"
                      onClick={() => {
                        setFormData((prev) => ({
                          ...prev,
                          readable_id: readableIdValidation.suggestedId!,
                        }));
                        validateReadableId(readableIdValidation.suggestedId!);
                      }}
                    >
                      Use suggested: {readableIdValidation.suggestedId}
                    </Button>
                  )}
                </div>
              )}

              <p className="text-xs text-muted-foreground mt-1">
                This ID will be used in citations like \cite
                {`{${formData.readable_id || "YourId"}}`}. It should be short,
                memorable, and unique.
              </p>
            </div>

            <div>
              <Label htmlFor="journal">Journal/Publisher</Label>
              <Input
                id="journal"
                value={formData.journal}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, journal: e.target.value }))
                }
                placeholder="Journal or publisher name"
              />
            </div>

            <div>
              <Label htmlFor="url">URL</Label>
              <Input
                id="url"
                type="url"
                value={formData.url}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, url: e.target.value }))
                }
                placeholder="https://example.com/research"
              />
            </div>

            <div className="flex gap-2">
              <Button onClick={handleSave}>
                <Save className="w-4 h-4 mr-2" />
                {editingId ? "Update" : "Create"}
              </Button>
              <Button variant="outline" onClick={handleCancel}>
                <X className="w-4 h-4 mr-2" />
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {references.map((reference) => (
          <Card key={reference.id}>
            <CardContent className="pt-6">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="font-semibold text-lg">{reference.title}</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {reference.authors.join(", ")} ({reference.year})
                  </p>
                  {reference.journal && (
                    <p className="text-sm text-muted-foreground">
                      {reference.journal}
                    </p>
                  )}
                  {reference.url && (
                    <a
                      href={reference.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline"
                    >
                      View Source
                    </a>
                  )}
                  <div className="mt-2 flex gap-2 flex-wrap">
                    <Badge variant="outline">{reference.type}</Badge>
                    <Badge variant="secondary" className="font-mono text-xs">
                      {reference.readable_id}
                    </Badge>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEdit(reference)}
                    disabled={editingId !== null || showNewForm}
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(reference.id)}
                    disabled={editingId !== null || showNewForm}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {references.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            No references found. Add one to get started.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
