import { getBackendBaseUrl } from "@/lib/biomechanics-api";

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: Context) {
  const { path } = await context.params;
  const suffix = path.map(encodeURIComponent).join("/");
  const sourceUrl = new URL(request.url);
  const backendUrl = `${getBackendBaseUrl()}/${suffix}${sourceUrl.search}`;
  try {
    const headers: HeadersInit = {};
    const contentType = request.headers.get("content-type");
    if (contentType) headers["content-type"] = contentType;
    const response = await fetch(backendUrl, {
      method: request.method,
      headers,
      body: request.method === "GET" ? undefined : await request.arrayBuffer(),
      cache: "no-store",
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return Response.json(
      { detail: "The biomechanics API could not be reached." },
      { status: 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
