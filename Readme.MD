# Meer, Märkte, Mobilität: EU Klimarisiko-Bewertung

## Projektübersicht

Dieses Repository enthält ein umfassendes Klimarisiko-Bewertungsframework für europäische Regionen mit fortschrittlicher geospatialer Analyse und interaktiver Datenvisualisierung. Das Projekt erforscht Chancen für die EU im Bereich Data Science durch evidenzbasierte Klimarisikoanalyse.

### Zentrale Forschungsfrage

**"Wo liegen Chancen für die EU im Bereich Data Science?"**

Diese Frage wird durch die Entwicklung eines Klimarisiko-Bewertungssystems beantwortet, das folgende Komponenten kombiniert:

- Multi-Szenario-Modellierung des Meeresspiegelanstiegs
- Quantifizierung wirtschaftlicher Auswirkungen
- Interaktives webbasiertes Data Storytelling
- Fortschrittliche geospatiale Datenverarbeitung

## Systemkomponenten

### 🔬 [EU Klimarisiko-Bewertungsframework](./eu_climate/README.md)

Ein umfassendes Python-basiertes geospatiales Analyseframework mit einem vierschichtigen Klimarisiko-Bewertungsansatz:

- **Gefährdungsschicht**: Meeresspiegelanstieg-Szenarien und Küstenhochwasser-Modellierung
- **Expositionsschicht**: Gebäudedichte und Bevölkerungsexpositionsanalyse
- **Relevanzschicht**: Bewertung wirtschaftlicher Faktoren (BIP, Fracht, Humankapital)
- **Risikoschicht**: Integrierte Multi-Szenario-Risikobewertung
- **Erweiterte Funktionen**: Clusteranalyse, wirtschaftliche Auswirkungsquantifizierung, weboptimierte Ausgaben

**Kernfähigkeiten:**

- Multi-Szenario-Analyse (aktuell bis 15m Meeresspiegelanstieg)
- Cloud-Optimized GeoTIFF (COG) und Mapbox Vector Tiles (MVT) Generierung
- Automatisierte Datenverarbeitungspipelines mit Hugging Face Integration
- Wirtschaftliche Auswirkungsanalyse für BIP, Fracht und Humanressourcen

### 🌐 [Data Story Webanwendung](./data-story-web/README.md)

Eine interaktive Next.js-Anwendung mit umfassender Data Story Visualisierung und vollständigem Admin-Management:

- **Interaktive Visualisierungen**: Dynamische Karten und Diagramme mit Echtzeitdaten
- **Admin-Panel**: Komplettes Content-Management-System für Geschichten und Referenzen
- **Cloud-Speicher**: Cloudflare R2 Integration mit Unterstützung großer Geodateien
- **Echtzeitaktualisierungen**: Änderungen spiegeln sich sofort in der gesamten Anwendung wider

**Technische Features:**

- Supabase Datenbankintegration
- TypeScript für vollständige Typsicherheit
- Unterstützung großer Geodateiformate (.tif, .cog, .mbtiles)
- Erweiterte Bild- und Referenzverwaltung

## Projektziele

Basierend auf dem Projektbriefing wurden folgende Kernanforderungen definiert:

- **Evidenzbasierte Erzählung**: Entwicklung einer robusten, datengestützten Geschichte über EU-Klimarisiken
- **Data Science Methodik**: Anwendung fortschrittlicher geospatialer Analyse- und Machine Learning-Techniken
- **Überzeugende Präsentation**: Technisch fundierte und visuell ansprechende Ergebnisdarstellung
- **Skalierbare Architektur**: Weboptimierte Ausgaben für Politik- und Forschungsanwendungen

## Projektteam

- Leon Randzio (6065618)
- Ingo Weber (1254816)
- Tjark Gerken (8692717)
- Yannick Königstein (9502377)
- Sophie Blum (4362025)

## Schnellstart

### Klimaanalyse

```bash
cd eu_climate
python -m eu_climate.main
```

### Webanwendung

```bash
cd data-story-web
pnpm install && pnpm dev
```

Für detaillierte Installationsanweisungen siehe die verlinkten README-Dateien der einzelnen Komponenten.

## Repository-Struktur

```
├── eu_climate/                                    # Klimarisiko-Bewertungsframework
├── data-story-web/                                # Interaktive Webanwendung
├── Meilenstein - Projektinitialisierung/          # Projektinitialisierungs-Deliverables
├── Meilenstein - Zwischenstand/                   # Zwischenmeilenstein-Abgaben
├── Meilenstein - Finale Abgabe/                   # Finale Projektabgaben
└── requirements.txt                               # Python-Abhängigkeiten
```
