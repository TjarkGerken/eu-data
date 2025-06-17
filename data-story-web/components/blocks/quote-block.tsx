"use client";

interface QuoteBlockProps {
  content: string;
  author: string;
  role?: string;
}

export function QuoteBlock({ content, author, role }: QuoteBlockProps) {
  return (
    <div className="bg-gradient-to-r from-[#2d5a3d]/5 to-[#2d5a3d]/10 border-l-4 border-[#2d5a3d] p-6 rounded-r-lg">
      <blockquote className="text-lg italic text-muted-foreground mb-4">
        "{content}"
      </blockquote>
      <footer className="text-right">
        <cite className="text-sm font-medium text-[#2d5a3d]">— {author}</cite>
        {role && (
          <div className="text-xs text-muted-foreground mt-1">{role}</div>
        )}
      </footer>
    </div>
  );
}
