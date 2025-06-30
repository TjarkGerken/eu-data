"use client";

import { CitationAwareMarkdown } from "./citation-aware-markdown";

interface MarkdownBlockProps {
  content: string;
  references?: Array<{
    id: string;
    title: string;
    authors: string[];
    type: string;
  }>;
}

export function MarkdownBlock({ content, references }: MarkdownBlockProps) {
  return <CitationAwareMarkdown content={content} references={references} />;
}
