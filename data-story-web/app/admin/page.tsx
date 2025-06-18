"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import AuthWrapper from "@/components/admin/auth-wrapper";
import MultilingualStoryEditor from "@/components/admin/multilingual-story-editor";
import ContentBlockEditor from "@/components/admin/content-block-editor";
import ContentReferencesAdmin from "@/components/admin/content-references-admin";
import ClimateImagesAdmin from "@/components/admin/climate-images-admin";
import { Shield, BookOpen, Blocks, FileText, Image } from "lucide-react";

export default function AdminDashboard() {
  return (
    <AuthWrapper>
      <div className="container mx-auto p-6">
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="h-6 w-6" />
            <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          </div>
          <p className="text-muted-foreground">
            Manage the climate data story content in multiple languages
          </p>
        </div>

        <Tabs defaultValue="story" className="space-y-6">
          <TabsList className="grid grid-cols-4 w-full max-w-2xl">
            <TabsTrigger value="story" className="flex items-center gap-2">
              <BookOpen className="h-4 w-4" />
              Story
            </TabsTrigger>
            <TabsTrigger value="blocks" className="flex items-center gap-2">
              <Blocks className="h-4 w-4" />
              Blocks
            </TabsTrigger>
            <TabsTrigger value="references" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              References
            </TabsTrigger>
            <TabsTrigger value="images" className="flex items-center gap-2">
              <Image className="h-4 w-4" />
              Images
            </TabsTrigger>
          </TabsList>

          <TabsContent value="story">
            <Card>
              <CardHeader>
                <CardTitle>Story Content</CardTitle>
                <CardDescription>
                  Edit the main story content in English and German
                </CardDescription>
              </CardHeader>
              <CardContent>
                <MultilingualStoryEditor />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="blocks">
            <Card>
              <CardHeader>
                <CardTitle>Content Blocks</CardTitle>
                <CardDescription>
                  Create, edit, and manage content blocks with ordering
                  controls, validation, and reference management
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ContentBlockEditor />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="references">
            <Card>
              <CardHeader>
                <CardTitle>Academic References</CardTitle>
                <CardDescription>
                  Manage citations and research references used in the story
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ContentReferencesAdmin />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="images">
            <Card>
              <CardHeader>
                <CardTitle>Climate Images</CardTitle>
                <CardDescription>
                  Upload and manage climate visualization images
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ClimateImagesAdmin />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AuthWrapper>
  );
}
