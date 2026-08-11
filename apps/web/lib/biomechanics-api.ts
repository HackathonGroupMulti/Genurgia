export type HealthResponse = {
  status: "ok";
  service: "biomechanics";
};

export type HealthResult =
  | { ok: true; data: HealthResponse }
  | { ok: false; error: string };

const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

export function parseHealthResponse(value: unknown): HealthResponse | null {
  if (
    typeof value === "object" &&
    value !== null &&
    "status" in value &&
    value.status === "ok" &&
    "service" in value &&
    value.service === "biomechanics"
  ) {
    return { status: value.status, service: value.service };
  }

  return null;
}

export async function getBackendHealth(): Promise<HealthResult> {
  const backendUrl = process.env.BIOMECHANICS_API_URL ?? DEFAULT_BACKEND_URL;

  try {
    const response = await fetch(`${backendUrl}/health`, { cache: "no-store" });

    if (!response.ok) {
      return { ok: false, error: `Health check returned HTTP ${response.status}.` };
    }

    const health = parseHealthResponse(await response.json());

    if (!health) {
      return { ok: false, error: "Health check returned an unexpected response." };
    }

    return { ok: true, data: health };
  } catch {
    return { ok: false, error: `Start the API at ${backendUrl} and refresh this page.` };
  }
}
