"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function SettingsPage() {
  useEffect(() => {
    const authenticated = sessionStorage.getItem("admin_authenticated");
    if (authenticated !== "true") {
      window.location.href = "/admin";
      return;
    }
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8">
        <div className="flex items-center gap-4 mb-8">
          <Link href="/admin">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
          <h1 className="text-3xl font-bold">Settings</h1>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Environment Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    Admin password is configured via environment variable:{" "}
                    <code>NEXT_PUBLIC_ADMIN_PASSWORD</code>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Current password source:{" "}
                    {process.env.NEXT_PUBLIC_ADMIN_PASSWORD
                      ? "Environment Variable"
                      : "Default Fallback"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Content Management</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Content is stored in <code>lib/content.json</code> and
                  dynamically loaded into the application.
                </p>
                <p className="text-sm text-muted-foreground">
                  Changes made through the Content Management interface are
                  automatically saved and applied.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>System Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">Node Environment:</span>
                  <span className="text-sm font-mono">
                    {process.env.NODE_ENV}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Vercel Environment:</span>
                  <span className="text-sm font-mono">
                    {process.env.VERCEL_ENV || "local"}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
