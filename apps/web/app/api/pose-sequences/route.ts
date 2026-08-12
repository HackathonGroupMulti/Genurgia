import { getBackendBaseUrl } from "@/lib/biomechanics-api";

export async function POST(request: Request) {
  try {
    const contentType = request.headers.get("content-type");
    const contentLength = request.headers.get("content-length");
    const headers = new Headers();
    if (contentType) headers.set("content-type", contentType);
    if (contentLength) headers.set("content-length", contentLength);
    const response = await fetch(`${getBackendBaseUrl()}/pose-sequences`, {
      method: "POST",
      body: request.body,
      headers,
      duplex: "half",
      cache: "no-store",
    } as RequestInit & { duplex: "half" });
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
