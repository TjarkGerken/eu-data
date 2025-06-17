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
        references: [
          {
            id: "ref1",
            title: "Climate Change Vulnerability Assessment",
            authors: ["Smith, J.", "Brown, A."],
            year: 2023,
            journal: "Environmental Research Letters",
            type: "journal",
          },
        ],
        en: {
          heroTitle: "European Climate Data Analysis",
          heroDescription:
            "Exploring climate patterns and environmental changes across European regions through comprehensive data visualization and analysis.",
          dataStoryTitle: "European Climate Risk Assessment",
          introText1:
            "Climate change poses significant threats to European coastal regions through sea level rise, increased storm intensity, and changing precipitation patterns.",
          introText2:
            "This data story presents a systematic approach to climate risk assessment, integrating high-resolution spatial data, scenario modeling, and impact analysis.",
          blocks: [
            {
              type: "markdown",
              content:
                "# Climate Risk Assessment\n\nWelcome to our comprehensive climate risk analysis.",
            },
          ],
        },
        de: {
          heroTitle: "Europäische Klimadatenanalyse",
          heroDescription:
            "Erforschung von Klimamustern und Umweltveränderungen in europäischen Regionen durch umfassende Datenvisualisierung und -analyse.",
          dataStoryTitle: "Europäische Klimarisiko-Bewertung",
          introText1:
            "Der Klimawandel stellt erhebliche Bedrohungen für europäische Küstenregionen durch den Anstieg des Meeresspiegels dar.",
          introText2:
            "Diese Datengeschichte präsentiert einen systematischen Ansatz zur Klimarisikobewertung.",
          blocks: [
            {
              type: "markdown",
              content:
                "# Klimarisiko-Bewertung\n\nWillkommen zu unserer umfassenden Klimarisikoanalyse.",
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

export async function POST(request: NextRequest) {
  try {
    const content = await request.json();
    console.log("Received content to save:", JSON.stringify(content, null, 2));

    // Validate content structure
    if (!content || typeof content !== "object") {
      throw new Error("Invalid content structure");
    }

    if (!content.en || !content.de || !content.references) {
      throw new Error(
        "Missing required content properties (en, de, references)"
      );
    }

    // Ensure directory exists
    await fs.mkdir(path.dirname(CONTENT_FILE_PATH), { recursive: true });

    // Write file
    await fs.writeFile(CONTENT_FILE_PATH, JSON.stringify(content, null, 2));
    console.log("Content saved successfully to:", CONTENT_FILE_PATH);

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error saving content:", error);
    console.error("Error details:", {
      message: error instanceof Error ? error.message : "Unknown error",
      stack: error instanceof Error ? error.stack : undefined,
    });
    return NextResponse.json(
      {
        error: "Failed to save content",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
