"use client";

import { Card, CardContent } from "@/components/ui/card";

interface StatisticsBlockProps {
  stats: Array<{
    label: string;
    value: string;
    description?: string;
  }>;
}

export function StatisticsBlock({ stats }: StatisticsBlockProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {stats.map((stat, index) => (
        <Card
          key={index}
          className="bg-gradient-to-br from-[#2d5a3d]/5 to-[#2d5a3d]/10 border-[#2d5a3d]/20"
        >
          <CardContent className="p-6 text-center">
            <div className="text-3xl font-bold text-[#2d5a3d] mb-2">
              {stat.value}
            </div>
            <div className="text-lg font-medium text-foreground mb-2">
              {stat.label}
            </div>
            {stat.description && (
              <div className="text-sm text-muted-foreground">
                {stat.description}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
