import { getBackendBaseUrl } from "@/lib/biomechanics-api";

export async function POST(request: Request) {
  try {
    const response = await fetch(`${getBackendBaseUrl()}/pose-sequences`, {
      method: "POST",
      body: await request.formData(),
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
