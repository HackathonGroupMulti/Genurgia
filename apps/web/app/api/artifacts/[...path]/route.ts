import { getBackendBaseUrl } from "@/lib/biomechanics-api";

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(_request: Request, context: RouteContext) {
  const { path } = await context.params;
  if (path.length !== 2) {
    return Response.json({ detail: "Artifact not found." }, { status: 404 });
  }

  const artifactPath = path.map(encodeURIComponent).join("/");
  try {
    const response = await fetch(`${getBackendBaseUrl()}/artifacts/${artifactPath}`, {
      cache: "no-store",
    });
    const headers = new Headers();
    for (const name of ["content-type", "content-length", "content-disposition"]) {
      const value = response.headers.get(name);
      if (value) headers.set(name, value);
    }
    return new Response(response.body, { status: response.status, headers });
  } catch {
    return Response.json(
      { detail: "The biomechanics API could not be reached." },
      { status: 502 },
    );
  }
}
