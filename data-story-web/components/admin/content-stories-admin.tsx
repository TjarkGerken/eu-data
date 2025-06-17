"use client";

import { useState, useEffect } from "react";
import {
  supabase,
  type ContentStory,
  type ContentStoryInsert,
  type ContentStoryUpdate,
} from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Trash2, Plus, Edit, Save, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function ContentStoriesAdmin() {
  const [stories, setStories] = useState<ContentStory[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [newStory, setNewStory] = useState<ContentStoryInsert>({
    hero_title: "",
    language_code: "en",
    hero_description: "",
    data_story_title: "",
    intro_text_1: "",
    intro_text_2: "",
  });
  const [editForm, setEditForm] = useState<ContentStoryUpdate>({});
  const { toast } = useToast();

  useEffect(() => {
    fetchStories();
  }, []);

  const fetchStories = async () => {
    try {
      const { data, error } = await supabase
        .from("content_stories")
        .select("*")
        .order("created_at", { ascending: false });

      if (error) throw error;
      setStories(data || []);
    } catch (error) {
      console.error("Error fetching stories:", error);
      toast({
        title: "Error",
        description: "Failed to fetch content stories",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStory.hero_title) {
      toast({
        title: "Error",
        description: "Hero title is required",
        variant: "destructive",
      });
      return;
    }

    try {
      const { error } = await supabase
        .from("content_stories")
        .insert([newStory]);

      if (error) throw error;

      toast({
        title: "Success",
        description: "Content story created successfully",
      });

      setNewStory({
        hero_title: "",
        language_code: "en",
        hero_description: "",
        data_story_title: "",
        intro_text_1: "",
        intro_text_2: "",
      });
      fetchStories();
    } catch (error) {
      console.error("Create error:", error);
      toast({
        title: "Error",
        description: "Failed to create content story",
        variant: "destructive",
      });
    }
  };

  const handleEdit = (story: ContentStory) => {
    setEditingId(story.id);
    setEditForm({
      hero_title: story.hero_title,
      language_code: story.language_code,
      hero_description: story.hero_description,
      data_story_title: story.data_story_title,
      intro_text_1: story.intro_text_1,
      intro_text_2: story.intro_text_2,
    });
  };

  const handleUpdate = async (id: string) => {
    try {
      const { error } = await supabase
        .from("content_stories")
        .update(editForm)
        .eq("id", id);

      if (error) throw error;

      toast({
        title: "Success",
        description: "Content story updated successfully",
      });

      setEditingId(null);
      setEditForm({});
      fetchStories();
    } catch (error) {
      console.error("Update error:", error);
      toast({
        title: "Error",
        description: "Failed to update content story",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (story: ContentStory) => {
    if (
      !confirm(
        `Are you sure you want to delete the story "${story.hero_title}"?`
      )
    )
      return;

    try {
      const { error } = await supabase
        .from("content_stories")
        .delete()
        .eq("id", story.id);

      if (error) throw error;

      toast({
        title: "Success",
        description: "Content story deleted successfully",
      });

      fetchStories();
    } catch (error) {
      console.error("Delete error:", error);
      toast({
        title: "Error",
        description: "Failed to delete content story",
        variant: "destructive",
      });
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Unknown";
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">Loading...</div>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" />
            Create New Story
          </CardTitle>
          <CardDescription>
            Add a new content story with hero content and introductory text
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="hero_title">Hero Title *</Label>
                <Input
                  id="hero_title"
                  value={newStory.hero_title}
                  onChange={(e) =>
                    setNewStory((prev) => ({
                      ...prev,
                      hero_title: e.target.value,
                    }))
                  }
                  placeholder="Main hero title"
                  required
                />
              </div>
              <div>
                <Label htmlFor="language_code">Language</Label>
                <Select
                  value={newStory.language_code}
                  onValueChange={(value) =>
                    setNewStory((prev) => ({ ...prev, language_code: value }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select language" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="nl">Dutch</SelectItem>
                    <SelectItem value="de">German</SelectItem>
                    <SelectItem value="fr">French</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="hero_description">Hero Description</Label>
              <Textarea
                id="hero_description"
                value={newStory.hero_description || ""}
                onChange={(e) =>
                  setNewStory((prev) => ({
                    ...prev,
                    hero_description: e.target.value,
                  }))
                }
                placeholder="Description text for the hero section"
              />
            </div>
            <div>
              <Label htmlFor="data_story_title">Data Story Title</Label>
              <Input
                id="data_story_title"
                value={newStory.data_story_title || ""}
                onChange={(e) =>
                  setNewStory((prev) => ({
                    ...prev,
                    data_story_title: e.target.value,
                  }))
                }
                placeholder="Title for the data story section"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="intro_text_1">Intro Text 1</Label>
                <Textarea
                  id="intro_text_1"
                  value={newStory.intro_text_1 || ""}
                  onChange={(e) =>
                    setNewStory((prev) => ({
                      ...prev,
                      intro_text_1: e.target.value,
                    }))
                  }
                  placeholder="First introductory paragraph"
                />
              </div>
              <div>
                <Label htmlFor="intro_text_2">Intro Text 2</Label>
                <Textarea
                  id="intro_text_2"
                  value={newStory.intro_text_2 || ""}
                  onChange={(e) =>
                    setNewStory((prev) => ({
                      ...prev,
                      intro_text_2: e.target.value,
                    }))
                  }
                  placeholder="Second introductory paragraph"
                />
              </div>
            </div>
            <Button type="submit">Create Story</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Content Stories ({stories.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Hero Title</TableHead>
                  <TableHead>Language</TableHead>
                  <TableHead>Data Story Title</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stories.map((story) => (
                  <TableRow key={story.id}>
                    <TableCell>
                      {editingId === story.id ? (
                        <Input
                          value={editForm.hero_title || ""}
                          onChange={(e) =>
                            setEditForm((prev) => ({
                              ...prev,
                              hero_title: e.target.value,
                            }))
                          }
                        />
                      ) : (
                        <div className="font-medium">{story.hero_title}</div>
                      )}
                    </TableCell>
                    <TableCell>
                      {editingId === story.id ? (
                        <Select
                          value={editForm.language_code}
                          onValueChange={(value) =>
                            setEditForm((prev) => ({
                              ...prev,
                              language_code: value,
                            }))
                          }
                        >
                          <SelectTrigger className="w-32">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="en">English</SelectItem>
                            <SelectItem value="nl">Dutch</SelectItem>
                            <SelectItem value="de">German</SelectItem>
                            <SelectItem value="fr">French</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        <Badge variant="outline">{story.language_code}</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {editingId === story.id ? (
                        <Input
                          value={editForm.data_story_title || ""}
                          onChange={(e) =>
                            setEditForm((prev) => ({
                              ...prev,
                              data_story_title: e.target.value,
                            }))
                          }
                        />
                      ) : (
                        story.data_story_title || "—"
                      )}
                    </TableCell>
                    <TableCell>{formatDate(story.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {editingId === story.id ? (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleUpdate(story.id)}
                            >
                              <Save className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEditingId(null);
                                setEditForm({});
                              }}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEdit(story)}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(story)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
