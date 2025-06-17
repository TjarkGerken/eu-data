"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

interface CalloutBlockProps {
  title: string;
  content: string;
  variant: "success" | "warning" | "info" | "error";
}

export function CalloutBlock({ title, content, variant }: CalloutBlockProps) {
  const variantStyles = {
    success: "border-green-200 bg-green-50 text-green-800",
    warning: "border-yellow-200 bg-yellow-50 text-yellow-800",
    info: "border-blue-200 bg-blue-50 text-blue-800",
    error: "border-red-200 bg-red-50 text-red-800",
  };

  return (
    <Alert className={cn("border-l-4", variantStyles[variant])}>
      <AlertTitle className="text-lg font-semibold mb-2">{title}</AlertTitle>
      <AlertDescription className="text-base whitespace-pre-wrap">
        {content}
      </AlertDescription>
    </Alert>
  );
}
