"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Code2, Database, BarChart3, ExternalLink } from "lucide-react"
import { useLanguage } from "@/contexts/language-context"

// GitHub and Hugging Face SVG icons
const GitHubIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
  </svg>
)

const HuggingFaceIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm0 22C6.486 22 2 17.514 2 12S6.486 2 12 2s10 4.486 10 10-4.486 10-10 10z" />
    <path d="M12 4C8.691 4 6 6.691 6 10c0 1.657.672 3.157 1.757 4.243L12 18.486l4.243-4.243C17.328 13.157 18 11.657 18 10c0-3.309-2.691-6-6-6zm0 8c-1.105 0-2-.895-2-2s.895-2 2-2 2 .895 2 2-.895 2-2 2z" />
  </svg>
)

export function TechnicalSection() {
  const { t } = useLanguage()

  return (
    <div className="mt-16 space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-[#2d5a3d] mb-4">{t.technicalApproachTitle}</h2>
        <p className="text-lg text-muted-foreground max-w-3xl mx-auto">{t.technicalApproachDesc}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Data Collection & Processing */}
        <Card>
          <CardHeader>
            <div className="flex items-center space-x-2">
              <Database className="h-5 w-5 text-[#2d5a3d]" />
              <CardTitle className="text-lg">{t.methodologyTitle}</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground leading-relaxed">{t.methodologyContent}</p>
            <div className="flex flex-wrap gap-1 mt-4">
              <Badge variant="secondary" className="text-xs">
                Python
              </Badge>
              <Badge variant="secondary" className="text-xs">
                pandas
              </Badge>
              <Badge variant="secondary" className="text-xs">
                xarray
              </Badge>
              <Badge variant="secondary" className="text-xs">
                ERA5
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Statistical Analysis */}
        <Card>
          <CardHeader>
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5 text-[#2d5a3d]" />
              <CardTitle className="text-lg">{t.dataProcessingTitle}</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground leading-relaxed">{t.dataProcessingContent}</p>
            <div className="flex flex-wrap gap-1 mt-4">
              <Badge variant="secondary" className="text-xs">
                Mann-Kendall
              </Badge>
              <Badge variant="secondary" className="text-xs">
                Bootstrap
              </Badge>
              <Badge variant="secondary" className="text-xs">
                WMO Standards
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Visualization Framework */}
        <Card>
          <CardHeader>
            <div className="flex items-center space-x-2">
              <Code2 className="h-5 w-5 text-[#2d5a3d]" />
              <CardTitle className="text-lg">{t.visualizationTechTitle}</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground leading-relaxed">{t.visualizationTechContent}</p>
            <div className="flex flex-wrap gap-1 mt-4">
              <Badge variant="secondary" className="text-xs">
                D3.js
              </Badge>
              <Badge variant="secondary" className="text-xs">
                Observable Plot
              </Badge>
              <Badge variant="secondary" className="text-xs">
                Leaflet
              </Badge>
              <Badge variant="secondary" className="text-xs">
                WCAG
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Repository Links */}
      <Card className="bg-gradient-to-r from-[#2d5a3d]/5 to-[#c4a747]/5">
        <CardHeader>
          <CardTitle className="text-xl text-[#2d5a3d]">{t.repositoriesTitle}</CardTitle>
          <CardDescription className="text-base">{t.repositoriesDesc}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <Button asChild className="flex-1 bg-[#2d5a3d] hover:bg-[#2d5a3d]/90">
              <a href="https://github.com/eu-geolytics/climate-analysis" target="_blank" rel="noopener noreferrer">
                <GitHubIcon className="h-5 w-5 mr-2" />
                {t.sourceCode}
                <ExternalLink className="h-4 w-4 ml-2" />
              </a>
            </Button>
            <Button asChild variant="outline" className="flex-1 border-[#c4a747] text-[#c4a747] hover:bg-[#c4a747]/10">
              <a href="https://huggingface.co/eu-geolytics/climate-models" target="_blank" rel="noopener noreferrer">
                <HuggingFaceIcon className="h-5 w-5 mr-2" />
                {t.modelsData}
                <ExternalLink className="h-4 w-4 ml-2" />
              </a>
            </Button>
          </div>

          <div className="mt-6 p-4 bg-background/50 rounded-lg">
            <h4 className="text-sm font-medium mb-2 text-[#2d5a3d]">Repository Contents:</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Complete data processing pipeline and analysis scripts</li>
              <li>• Interactive visualization components and configurations</li>
              <li>• Pre-trained climate prediction models and datasets</li>
              <li>• Documentation and reproducible research notebooks</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
