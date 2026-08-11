import { getBackendBaseUrl } from "@/lib/biomechanics-api";

type RouteContext = { params: Promise<{ id: string }> };

export async function POST(_request: Request, context: RouteContext) {
  const { id } = await context.params;
  try {
    const response = await fetch(
      `${getBackendBaseUrl()}/pose-sequences/${encodeURIComponent(id)}/squat-repetitions`,
      { method: "POST", cache: "no-store" },
    );
    return new Response(response.body, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json(
      { detail: "The biomechanics API could not be reached." },
      { status: 502 },
    );
  }
}
