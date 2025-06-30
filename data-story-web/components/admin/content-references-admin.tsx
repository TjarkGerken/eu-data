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
import { Trash2, Plus, Save, X, Edit } from "lucide-react";
import { supabase } from "@/lib/supabase";
import type { ContentReference, ContentReferenceInsert } from "@/lib/supabase";
import { useToast } from "@/hooks/use-toast";

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
    });
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

    if (formData.authors.length === 0 || formData.authors.every(author => !author.trim())) {
      toast({
        title: "Validation Error", 
        description: "At least one author is required",
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
          id: crypto.randomUUID()
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
                    setFormData((prev) => ({ ...prev, type: value as "journal" | "book" | "website" | "report" }))
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
                  <div className="mt-2">
                    <Badge variant="outline">{reference.type}</Badge>
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
