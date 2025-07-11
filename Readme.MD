# Meer, Märkte, Mobilität: EU Klimarisiko-Bewertung

## Project Overview

This repository contains a comprehensive climate-risk assessment framework for European regions with advanced geospatial analysis and interactive data visualization. The project investigates opportunities for the EU in the field of data science through evidence-based climate-risk analysis.

### Central Research Question

**“Where are the opportunities for the EU in the field of data science?”**

This question is addressed by developing a climate-risk assessment system that combines the following components:

- Multi-scenario modeling of sea-level rise  
- Quantification of economic impacts  
- Interactive web-based data storytelling  
- Advanced geospatial data processing  

## Project Outcomes

- **Data Story**: An interactive web application for visualizing the climate-risk analysis  
  https://eu-data.vercel.app/

- **Multimedia Presentation**: A comprehensive introduction to the project and its results  
  https://www.youtube.com/watch?v=HwzwvXECIFY

- **Data & Analyses**: Full access to the datasets used and the analysis results  
  https://huggingface.co/datasets/TjarkGerken/eu-data

## System Components

### 🔬 [EU Climate Risk Assessment Framework](./eu_climate/README.md)

A comprehensive Python-based geospatial analysis framework with a four-layer climate-risk assessment approach:

- **Hazard Layer**: Sea-level-rise scenarios and coastal flood modeling  
- **Exposure Layer**: Building-density and population-exposure analysis  
- **Relevance Layer**: Assessment of economic factors (GDP, freight, human capital)  
- **Risk Layer**: Integrated multi-scenario risk evaluation based on selected factors  
- **Advanced Features**: Cluster analysis, economic-impact quantification, web-optimized outputs  

**Core Capabilities:**

- Multi-scenario analysis (currently up to 15 m sea-level rise)  
- Cloud-Optimized GeoTIFF (COG) and Mapbox Vector Tiles (MVT) generation  
- Automated data-processing pipelines with Hugging Face integration  
- Economic-impact analysis for GDP, freight, and human resources  

### 🌐 [Data Story Web Application](./data-story-web/README.md)

An interactive Next.js application with comprehensive data-story visualization and full admin management:

- **Interactive Visualizations**: Dynamic maps and charts  
- **Admin Panel**: Complete content-management system for stories and references  
- **Cloud Storage**: Cloudflare R2 integration with support for large geospatial files  

**Technical Features:**

- Supabase database integration  
- Support for large geospatial file formats (.tif, .cog, .mbtiles)  
- Advanced image and reference management  

## Project Goals

Based on the project briefing, the following core requirements were defined:

- **Evidence-Based Storytelling**: Developing a robust, data-driven narrative on EU climate risks  
- **Data-Science Methodology**: Applying advanced geospatial analysis and machine-learning techniques  
- **Compelling Presentation**: Technically sound and visually appealing result presentation  
- **Scalable Architecture**: Web-optimized outputs for policy and research applications  

## Project Team

- Leon Randzio (6065618)  
- Ingo Weber (1254816)  
- Tjark Gerken (8692717)  
- Yannick Königstein (9502377)  
- Sophie Blum (4362025)  

## Quick Start

### Climate Analysis

```bash
cd eu_climate
python -m eu_climate.main
```

### Web Application

```bash
cd data-story-web
pnpm install && pnpm dev
```

For detailed installation instructions, see the linked README files of the individual components.

## Repository Structure

```
├── eu_climate/                                    # Climate-risk assessment framework
├── data-story-web/                                # Interactive web application
├── Milestone – Project Initiation/                # Project-initiation deliverables
├── Milestone – Interim Report/                    # Interim-milestone submissions
├── Milestone – Final Submission/                  # Final project submissions
└── requirements.txt                               # Python dependencies
```
