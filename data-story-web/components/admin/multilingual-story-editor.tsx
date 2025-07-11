"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Save, Languages } from "lucide-react";

interface StoryData {
  heroTitle: string;
  heroDescription: string;
  dataStoryTitle: string;
  introText1: string;
  introText2: string;
}

interface Story {
  id: string;
  languageCode: string;
  heroTitle: string;
  heroDescription: string;
  dataStoryTitle: string;
  dataStorySubtitle: string;
  introText: string;
}

export default function MultilingualStoryEditor() {
  const [englishData, setEnglishData] = useState<StoryData>({
    heroTitle: "",
    heroDescription: "",
    dataStoryTitle: "",
    introText1: "",
    introText2: "",
  });

  const [germanData, setGermanData] = useState<StoryData>({
    heroTitle: "",
    heroDescription: "",
    dataStoryTitle: "",
    introText1: "",
    introText2: "",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [stories, setStories] = useState<Story[]>([]);

  useEffect(() => {
    fetchStories();
  }, []);

  const fetchStories = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from("content_stories")
        .select("*")
        .in("language_code", ["en", "de"])
        .order("language_code");

      if (error) throw error;

      const mappedStories: Story[] = (data || []).map((story) => ({
        id: story.id,
        languageCode: story.language_code,
        heroTitle: story.hero_title || "",
        heroDescription: story.hero_description || "",
        dataStoryTitle: story.data_story_title || "",
        dataStorySubtitle: "", // Not in database, using default
        introText: story.intro_text_1 || "", // Using intro_text_1 as introText
      }));

      setStories(mappedStories);

      // Populate form with existing data
      const englishStory = mappedStories.find((s) => s.languageCode === "en");
      const germanStory = mappedStories.find((s) => s.languageCode === "de");

      if (englishStory) {
        setEnglishData({
          heroTitle: englishStory.heroTitle || "",
          heroDescription: englishStory.heroDescription || "",
          dataStoryTitle: englishStory.dataStoryTitle || "",
          introText1: englishStory.introText || "",
          introText2: "", // Not available in mapped data
        });
      }

      if (germanStory) {
        setGermanData({
          heroTitle: germanStory.heroTitle || "",
          heroDescription: germanStory.heroDescription || "",
          dataStoryTitle: germanStory.dataStoryTitle || "",
          introText1: germanStory.introText || "",
          introText2: "", // Not available in mapped data
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load stories");
    } finally {
      setLoading(false);
    }
  };

  const saveStory = async (languageCode: string, data: StoryData) => {
    setSaving(true);
    setError(null);

    try {
      const existingStory = stories.find(
        (s) => s.languageCode === languageCode,
      );

      const storyData = {
        language_code: languageCode,
        hero_title: data.heroTitle,
        hero_description: data.heroDescription,
        data_story_title: data.dataStoryTitle,
        intro_text_1: data.introText1,
        intro_text_2: data.introText2,
      };

      if (existingStory) {
        // Update existing story
        const { error } = await supabase
          .from("content_stories")
          .update(storyData)
          .eq("id", existingStory.id);

        if (error) throw error;
      } else {
        // Create new story
        const { error } = await supabase.from("content_stories").insert({
          ...storyData,
          created_at: new Date().toISOString(),
        });

        if (error) throw error;
      }

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);

      // Refresh stories to get updated data
      await fetchStories();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save story");
    } finally {
      setSaving(false);
    }
  };

  const renderStoryForm = (
    data: StoryData,
    setData: (data: StoryData) => void,
    language: string,
    languageCode: string,
  ) => (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor={`heroTitle-${languageCode}`}>Hero Title</Label>
        <Input
          id={`heroTitle-${languageCode}`}
          value={data.heroTitle}
          onChange={(e) => setData({ ...data, heroTitle: e.target.value })}
          placeholder={`Enter hero title in ${language}...`}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`heroDescription-${languageCode}`}>
          Hero Description
        </Label>
        <Textarea
          id={`heroDescription-${languageCode}`}
          value={data.heroDescription}
          onChange={(e) =>
            setData({ ...data, heroDescription: e.target.value })
          }
          placeholder={`Enter hero description in ${language}...`}
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`dataStoryTitle-${languageCode}`}>
          Data Story Title
        </Label>
        <Input
          id={`dataStoryTitle-${languageCode}`}
          value={data.dataStoryTitle}
          onChange={(e) => setData({ ...data, dataStoryTitle: e.target.value })}
          placeholder={`Enter data story title in ${language}...`}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`introText1-${languageCode}`}>
          Introduction Text 1
        </Label>
        <Textarea
          id={`introText1-${languageCode}`}
          value={data.introText1}
          onChange={(e) => setData({ ...data, introText1: e.target.value })}
          placeholder={`Enter first introduction paragraph in ${language}...`}
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`introText2-${languageCode}`}>
          Introduction Text 2
        </Label>
        <Textarea
          id={`introText2-${languageCode}`}
          value={data.introText2}
          onChange={(e) => setData({ ...data, introText2: e.target.value })}
          placeholder={`Enter second introduction paragraph in ${language}...`}
          rows={3}
        />
      </div>

      <Button
        onClick={() => saveStory(languageCode, data)}
        disabled={saving}
        className="w-full"
      >
        {saving ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Saving {language}...
          </>
        ) : (
          <>
            <Save className="mr-2 h-4 w-4" />
            Save {language} Story
          </>
        )}
      </Button>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading story content...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Languages className="h-5 w-5" />
        <h2 className="text-xl font-semibold">Story Content Editor</h2>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert>
          <AlertDescription>Story saved successfully!</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="english" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="english">English</TabsTrigger>
          <TabsTrigger value="german">Deutsch</TabsTrigger>
        </TabsList>

        <TabsContent value="english">
          <Card>
            <CardHeader>
              <CardTitle>English Story Content</CardTitle>
            </CardHeader>
            <CardContent>
              {renderStoryForm(englishData, setEnglishData, "English", "en")}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="german">
          <Card>
            <CardHeader>
              <CardTitle>German Story Content</CardTitle>
            </CardHeader>
            <CardContent>
              {renderStoryForm(germanData, setGermanData, "German", "de")}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
