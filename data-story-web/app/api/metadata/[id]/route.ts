import { NextRequest, NextResponse } from "next/server";

const METADATA_BASE_URL =
  process.env.NEXT_PUBLIC_METADATA_BASE_URL || "https://tjarkgerken.com";

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  if (!id) {
    return NextResponse.json({ error: "Missing metadata id" }, { status: 400 });
  }

  const url = `${METADATA_BASE_URL}/metadata/${id}.json`;

  try {
    const res = await fetch(url, { cache: "no-store" });

    if (!res.ok) {
      return NextResponse.json(
        { error: `Failed to fetch metadata (${res.status})` },
        { status: res.status }
      );
    }

    const data = await res.json();

    return NextResponse.json(data, {
      headers: {
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Unable to fetch metadata",
      },
      { status: 500 }
    );
  }
}
