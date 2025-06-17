"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import ImageAdmin from "@/components/image-admin";

export default function AdminImagesPage() {
  useEffect(() => {
    const authenticated = sessionStorage.getItem("admin_authenticated");
    if (authenticated !== "true") {
      window.location.href = "/admin";
      return;
    }
  }, []);

  return (
    <div className="container mx-auto py-8">
      <div className="flex items-center gap-4 mb-8">
        <Link href="/admin">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Climate Data Image Management</h1>
          <p className="text-muted-foreground mt-2">
            Upload, manage, and monitor climate visualization images stored in
            Vercel Blob Storage CDN.
          </p>
        </div>
      </div>

      <ImageAdmin />
    </div>
  );
}
