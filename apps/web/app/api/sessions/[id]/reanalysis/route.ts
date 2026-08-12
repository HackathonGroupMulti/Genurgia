import { getBackendBaseUrl } from "@/lib/biomechanics-api";

export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  try {
    const response = await fetch(
      `${getBackendBaseUrl()}/sessions/${encodeURIComponent(id)}/reanalysis`,
      {
        method: "POST",
        body: await request.text(),
        headers: { "content-type": "application/json" },
        cache: "no-store",
      },
    );
    return new Response(response.body, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ detail: "The biomechanics API could not be reached." }, { status: 502 });
  }
}
