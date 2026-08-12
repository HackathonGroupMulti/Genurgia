import { getBackendBaseUrl } from "@/lib/biomechanics-api";

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams;
  const backendQuery = new URLSearchParams();
  for (const name of ["baseline_id", "current_id"]) {
    const value = query.get(name);
    if (value) backendQuery.set(name, value);
  }
  try {
    const response = await fetch(
      `${getBackendBaseUrl()}/sessions/selected-comparison?${backendQuery}`,
      { cache: "no-store" },
    );
    return new Response(response.body, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ detail: "The biomechanics API could not be reached." }, { status: 502 });
  }
}
