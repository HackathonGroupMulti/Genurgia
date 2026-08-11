import { getBackendBaseUrl } from "@/lib/biomechanics-api";

export async function GET() {
  try {
    const response = await fetch(`${getBackendBaseUrl()}/sessions/comparison`, {
      cache: "no-store",
    });
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
