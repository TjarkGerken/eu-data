"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ExternalLink, BookOpen } from "lucide-react"
import { useLanguage } from "@/contexts/language-context"

interface Reference {
  id: string
  title: string
  authors: string[]
  year: number
  journal?: string
  url?: string
  type: "journal" | "report" | "dataset" | "book"
}

const references: Reference[] = [
  {
    id: "1",
    title: "Climate Change Impacts on European Agriculture",
    authors: ["Smith, J.", "Johnson, A."],
    year: 2023,
    journal: "Environmental Science & Policy",
    type: "journal",
    url: "#",
  },
  {
    id: "2",
    title: "European Environment Agency Climate Data",
    authors: ["EEA"],
    year: 2023,
    type: "dataset",
    url: "#",
  },
  {
    id: "3",
    title: "Temperature Trends in Central Europe",
    authors: ["Brown, M.", "Davis, K.", "Wilson, R."],
    year: 2022,
    journal: "Climate Dynamics",
    type: "journal",
    url: "#",
  },
  {
    id: "4",
    title: "IPCC Sixth Assessment Report",
    authors: ["IPCC"],
    year: 2021,
    type: "report",
    url: "#",
  },
  {
    id: "5",
    title: "Precipitation Patterns in Northern Europe",
    authors: ["Anderson, L.", "Taylor, S."],
    year: 2023,
    journal: "Journal of Climate",
    type: "journal",
    url: "#",
  },
]

const typeColors = {
  journal: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  report: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  dataset: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  book: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
}

export function ReferencesSidebar() {
  const { t } = useLanguage()

  return (
    <Card className="sticky top-20 h-fit">
      <CardHeader>
        <div className="flex items-center space-x-2">
          <BookOpen className="h-5 w-5 text-[#2d5a3d]" />
          <CardTitle>{t.references}</CardTitle>
        </div>
        <CardDescription>{t.referencesDesc}</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[600px] pr-4">
          <div className="space-y-4">
            {references.map((ref) => (
              <div key={ref.id} className="border-l-2 border-[#2d5a3d]/20 pl-4 pb-4">
                <div className="flex items-start justify-between mb-2">
                  <Badge variant="secondary" className={`text-xs ${typeColors[ref.type]}`}>
                    {ref.type}
                  </Badge>
                  <span className="text-xs text-muted-foreground">[{ref.id}]</span>
                </div>

                <h4 className="text-sm font-medium leading-tight mb-1">{ref.title}</h4>

                <p className="text-xs text-muted-foreground mb-1">
                  {ref.authors.join(", ")} ({ref.year})
                </p>

                {ref.journal && <p className="text-xs text-muted-foreground italic mb-2">{ref.journal}</p>}

                {ref.url && (
                  <a href={ref.url} className="inline-flex items-center text-xs text-[#2d5a3d] hover:underline">
                    <ExternalLink className="h-3 w-3 mr-1" />
                    {t.viewSource}
                  </a>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
