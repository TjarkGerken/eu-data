import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

const CONTENT_FILE_PATH = path.join(process.cwd(), "lib", "content.json");

export async function GET() {
  try {
    const fileExists = await fs
      .access(CONTENT_FILE_PATH)
      .then(() => true)
      .catch(() => false);

    if (!fileExists) {
      const defaultContent = {
        en: {
          heroTitle: "European Climate Data Analysis",
          heroDescription:
            "Exploring climate patterns and environmental changes across European regions through comprehensive data visualization and analysis.",
          dataStoryTitle: "European Climate Risk Assessment",
          introText1:
            "Climate change poses significant threats to European coastal regions through sea level rise, increased storm intensity, and changing precipitation patterns. Our comprehensive risk assessment framework combines hazard analysis, exposure mapping, and vulnerability assessment to quantify climate risks across different scenarios and inform adaptation planning.",
          introText2:
            "This data story presents a systematic approach to climate risk assessment, integrating high-resolution spatial data, scenario modeling, and impact analysis. Each visualization below demonstrates different components of our risk assessment methodology, providing decision-makers with the tools needed to understand and address climate vulnerabilities in their regions.",
          visualizations: [
            {
              title: "Climate Hazard Risk Assessment",
              description:
                "Comprehensive analysis of climate hazards across different sea level rise scenarios showing current and projected risk levels.",
              content:
                "Our hazard assessment reveals significant variations in climate risk across European coastal regions. Under current conditions, 9.7% of the study area faces high risk, with moderate and low risk areas covering 5.4% and 4.1% respectively.",
              type: "map",
              imageCategory: "hazard",
              imageScenario: "current",
              imageId: "current-scenario",
              references: ["1", "3"],
            },
          ],
        },
        de: {
          heroTitle: "Europäische Klimadatenanalyse",
          heroDescription:
            "Erforschung von Klimamustern und Umweltveränderungen in europäischen Regionen durch umfassende Datenvisualisierung und -analyse.",
          dataStoryTitle: "Europäische Klimarisiko-Bewertung",
          introText1:
            "Der Klimawandel stellt erhebliche Bedrohungen für europäische Küstenregionen durch den Anstieg des Meeresspiegels, verstärkte Sturmintensität und veränderte Niederschlagsmuster dar.",
          introText2:
            "Diese Datengeschichte präsentiert einen systematischen Ansatz zur Klimarisikobewertung, der hochauflösende räumliche Daten, Szenariomodellierung und Folgenanalyse integriert.",
          visualizations: [
            {
              title: "Klimagefahren-Risikobewertung",
              description:
                "Umfassende Analyse von Klimagefahren in verschiedenen Meeresspiegelanstieg-Szenarien mit aktuellen und prognostizierten Risikoniveaus.",
              content:
                "Unsere Gefahrenbewertung zeigt erhebliche Variationen im Klimarisiko in europäischen Küstenregionen. Unter aktuellen Bedingungen sind 9,7% des Untersuchungsgebiets einem hohen Risiko ausgesetzt.",
              type: "map",
              imageCategory: "hazard",
              imageScenario: "current",
              imageId: "current-scenario",
              references: ["1", "3"],
            },
          ],
        },
      };

      await fs.writeFile(
        CONTENT_FILE_PATH,
        JSON.stringify(defaultContent, null, 2)
      );
      return NextResponse.json(defaultContent);
    }

    const content = await fs.readFile(CONTENT_FILE_PATH, "utf8");
    return NextResponse.json(JSON.parse(content));
  } catch (error) {
    console.error("Error reading content:", error);
    return NextResponse.json(
      { error: "Failed to read content" },
      { status: 500 }
    );
  }
}

export async function PUT(request: NextRequest) {
  try {
    const content = await request.json();

    await fs.mkdir(path.dirname(CONTENT_FILE_PATH), { recursive: true });
    await fs.writeFile(CONTENT_FILE_PATH, JSON.stringify(content, null, 2));

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error saving content:", error);
    return NextResponse.json(
      { error: "Failed to save content" },
      { status: 500 }
    );
  }
}
