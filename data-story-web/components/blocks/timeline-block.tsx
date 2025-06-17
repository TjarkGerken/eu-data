"use client";

interface TimelineBlockProps {
  events: Array<{
    year: string;
    title: string;
    description: string;
  }>;
}

export function TimelineBlock({ events }: TimelineBlockProps) {
  return (
    <div className="space-y-8">
      {events.map((event, index) => (
        <div key={index} className="flex items-start space-x-4">
          <div className="flex-shrink-0">
            <div className="w-16 h-16 bg-[#2d5a3d] rounded-full flex items-center justify-center text-white font-bold text-sm">
              {event.year}
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-lg font-semibold text-[#2d5a3d] mb-2">
              {event.title}
            </div>
            <div className="text-muted-foreground whitespace-pre-wrap">
              {event.description}
            </div>
          </div>
          {index < events.length - 1 && (
            <div className="absolute left-8 mt-16 w-0.5 h-8 bg-[#2d5a3d]/20"></div>
          )}
        </div>
      ))}
    </div>
  );
}
