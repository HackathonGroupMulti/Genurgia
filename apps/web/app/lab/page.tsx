import Link from "next/link";

import { KneeLab } from "@/components/knee-lab";
import { getBackendBaseUrl } from "@/lib/biomechanics-api";
import type { Reconstruction } from "@/lib/evidence-contracts";
import {
  parseSimulationAdapters,
  parseSimulationModels,
} from "@/lib/simulation-contracts";

export const dynamic = "force-dynamic";

async function loadJson(path: string): Promise<unknown> {
  try {
    const response = await fetch(`${getBackendBaseUrl()}${path}`, { cache: "no-store" });
    return response.ok ? response.json() : null;
  } catch {
    return null;
  }
}

export default async function LabPage() {
  const [adapterPayload, modelPayload, reconstructionPayload] = await Promise.all([
    loadJson("/simulation-adapters"),
    loadJson("/simulation-models"),
    loadJson("/reconstructions"),
  ]);
  const adapters = parseSimulationAdapters(adapterPayload) ?? [];
  const models = parseSimulationModels(modelPayload) ?? [];
  const reconstructions =
    typeof reconstructionPayload === "object" &&
    reconstructionPayload !== null &&
    "reconstructions" in reconstructionPayload &&
    Array.isArray(reconstructionPayload.reconstructions)
      ? (reconstructionPayload.reconstructions as Reconstruction[])
      : [];

  return (
    <main className="lab-page">
      <header className="lab-header">
        <div>
          <p className="eyebrow">Knee Twin · Open hypothesis machine</p>
          <h1>Try the knee.</h1>
          <p className="lede">
            Build reproducible finite-element attempts that other researchers can inspect,
            challenge, and improve.
          </p>
        </div>
        <Link className="artifact-link" href="/">Movement workspace</Link>
      </header>
      <KneeLab adapters={adapters} models={models} reconstructions={reconstructions} />
    </main>
  );
}
