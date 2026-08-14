"use client";

import { useMemo, useState } from "react";

import type { Reconstruction } from "@/lib/evidence-contracts";
import {
  parseFlexionResult,
  reconstructionForModel,
  syntheticExperimentTemplate,
  type FebioFlexionSweepResultV1,
  type SimulationAdapterV1,
  type SimulationModelV1,
} from "@/lib/simulation-contracts";
import { SimulationFieldViewer } from "./simulation-field-viewer";

type Props = {
  adapters: SimulationAdapterV1[];
  models: SimulationModelV1[];
  reconstructions: Reconstruction[];
};

type ExperimentManifest = Record<string, unknown>;
type RunRecord = {
  jobId: string;
  result: FebioFlexionSweepResultV1;
  definition: ExperimentManifest;
};
type RetryRecord = { jobId: string; definition: ExperimentManifest };

export function KneeLab({ adapters, models, reconstructions }: Props) {
  const [availableModels, setAvailableModels] = useState(models);
  const [modelId, setModelId] = useState(models[0]?.id ?? "");
  const [modelPackage, setModelPackage] = useState<File | null>(null);
  const selectedModel = availableModels.find((model) => model.id === modelId) ?? null;
  const reconstruction = selectedModel
    ? reconstructionForModel(selectedModel, reconstructions)
    : null;
  const [definitionText, setDefinitionText] = useState("");
  const [status, setStatus] = useState("Select a solver-ready model and author its assumptions.");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [retryRecord, setRetryRecord] = useState<RetryRecord | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [runIndex, setRunIndex] = useState(0);
  const [poseIndex, setPoseIndex] = useState(0);
  const adapter = adapters.find((item) => item.adapter_id === "febio-4.12") ?? null;
  const selectedRun = runs[runIndex] ?? null;
  const pose = selectedRun?.result.poses[poseIndex] ?? null;
  const canLoadFixture = selectedModel?.version.startsWith("cc0-synthetic-flexion") ?? false;
  const assumptionCount = useMemo(() => {
    try {
      const parsed = JSON.parse(definitionText) as Record<string, unknown>;
      return [parsed.materials, parsed.ligaments, parsed.contacts].reduce<number>(
        (total, value) => total + (Array.isArray(value) ? value.length : 0),
        0,
      );
    } catch {
      return 0;
    }
  }, [definitionText]);

  function selectModel(nextId: string) {
    setModelId(nextId);
    setDefinitionText("");
    setRuns([]);
    setRunIndex(0);
    setPoseIndex(0);
    setRetryRecord(null);
  }

  function loadFixture() {
    if (!selectedModel || !canLoadFixture) return;
    setDefinitionText(JSON.stringify(syntheticExperimentTemplate(selectedModel), null, 2));
    setStatus("Loaded fixture-only assumptions. Review every value before running.");
  }

  async function importModel() {
    if (!modelPackage) return;
    const body = new FormData();
    body.append("package", modelPackage);
    setStatus("Validating and hashing the finite-element model package...");
    const response = await fetch("/api/knee-twin/simulation-models/imports/febio", {
      method: "POST",
      body,
    });
    if (!response.ok) {
      setStatus(await detail(response));
      return;
    }
    const job = (await response.json()) as { id: string };
    setActiveJobId(job.id);
    setStatus(`Import job ${job.id} queued; validating topology and provenance...`);
    try {
      const workerResponse = await fetch("/api/knee-twin/jobs/worker/run-next", {
        method: "POST",
      });
      if (!workerResponse.ok) throw new Error(await detail(workerResponse));
      const complete = (await workerResponse.json()) as {
        status: string;
        error_detail: string | null;
        result_artifact_reference: string | null;
      };
      if (!complete.result_artifact_reference) {
        throw new Error(complete.error_detail ?? `Import ended as ${complete.status}.`);
      }
      const resultResponse = await fetch(
        `/api/knee-twin${complete.result_artifact_reference}`,
        { cache: "no-store" },
      );
      if (!resultResponse.ok) throw new Error(await detail(resultResponse));
      const payload = (await resultResponse.json()) as {
        simulation_model: SimulationModelV1;
      };
      setAvailableModels((current) => [...current, payload.simulation_model]);
      selectModel(payload.simulation_model.id);
      setStatus("The immutable solver-ready model was imported and linked to its reconstruction.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The model import failed.");
    } finally {
      setActiveJobId(null);
    }
  }

  function exportManifest() {
    const blob = new Blob([definitionText], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "knee-twin-experiment-definition-v2.json";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function runExperiment() {
    if (!selectedModel || !reconstruction || !adapter?.available) return;
    try {
      const definition = JSON.parse(definitionText) as Record<string, unknown>;
      setStatus("Creating immutable canonical experiment…");
      const experimentResponse = await fetch("/api/knee-twin/experiments", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          knee_id: reconstruction.knee_id,
          timepoint_id: reconstruction.timepoint_id,
          definition_version: "experiment-definition-v2",
          definition,
          validation_tier: definition.validation_tier,
        }),
      });
      if (!experimentResponse.ok) throw new Error(await detail(experimentResponse));
      const experiment = (await experimentResponse.json()) as { id: string };
      const jobResponse = await fetch("/api/knee-twin/jobs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          job_type: "febio-flexion-sweep-v1",
          request: { virtual_experiment_id: experiment.id, experiment: definition },
        }),
      });
      if (!jobResponse.ok) throw new Error(await detail(jobResponse));
      const job = (await jobResponse.json()) as { id: string };
      setActiveJobId(job.id);
      setStatus(`Job ${job.id} queued; the local worker is running it.`);
      const workerResponse = await fetch("/api/knee-twin/jobs/worker/run-next", {
        method: "POST",
      });
      if (!workerResponse.ok) throw new Error(await detail(workerResponse));
      await collectWorkerResult(job.id, definition, workerResponse);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The experiment failed.");
    } finally {
      setActiveJobId(null);
    }
  }

  async function collectWorkerResult(
    jobId: string,
    definition: ExperimentManifest,
    workerResponse: Response,
  ) {
    if (!workerResponse.ok) throw new Error(await detail(workerResponse));
    const complete = (await workerResponse.json()) as {
      status: string;
      error_detail: string | null;
      result_artifact_reference: string | null;
    };
    if (!complete.result_artifact_reference) {
      setRetryRecord({ jobId, definition });
      throw new Error(complete.error_detail ?? `Job ended as ${complete.status}.`);
    }
    const resultResponse = await fetch(
      `/api/knee-twin${complete.result_artifact_reference}`,
      { cache: "no-store" },
    );
    const result = parseFlexionResult(await resultResponse.json());
    if (!result) throw new Error("The worker returned an invalid flexion-sweep result.");
    setRunIndex(runs.length);
    setRuns((current) => [...current, { jobId, result, definition }]);
    setPoseIndex(0);
    setRetryRecord(null);
    setStatus(
      complete.status === "cancelled"
        ? "The cancelled run and its partial evidence were preserved."
        : "Exploratory sweep complete. Convergence does not establish accuracy.",
    );
  }

  async function retry() {
    if (!retryRecord) return;
    setActiveJobId(retryRecord.jobId);
    setStatus(`Retrying job ${retryRecord.jobId} with its unchanged manifest…`);
    try {
      const retryResponse = await fetch(
        `/api/knee-twin/jobs/${retryRecord.jobId}/retry`,
        { method: "POST" },
      );
      if (!retryResponse.ok) throw new Error(await detail(retryResponse));
      const workerResponse = await fetch("/api/knee-twin/jobs/worker/run-next", {
        method: "POST",
      });
      await collectWorkerResult(retryRecord.jobId, retryRecord.definition, workerResponse);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The retry failed.");
    } finally {
      setActiveJobId(null);
    }
  }

  async function cancel() {
    if (!activeJobId) return;
    const response = await fetch(`/api/knee-twin/jobs/${activeJobId}/cancel`, {
      method: "POST",
    });
    setStatus(response.ok ? "Cancellation requested; completed poses will be preserved." : await detail(response));
  }

  return (
    <section className="knee-lab-panel" aria-labelledby="lab-heading">
      <div>
        <p className="section-label">Exploratory simulation</p>
        <h2 id="lab-heading">FEBio Knee Lab</h2>
        <p className="section-copy">
          A transparent attempt engine. Inputs may be assumptions and outputs may be wrong; neither is
          hidden or presented as diagnosis.
        </p>
      </div>

      <div className="evidence-legend" aria-label="Evidence classes">
        {["Observed", "Reconstructed", "Expert assumption", "Simulated"].map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>

      <div className={`adapter-card ${adapter?.available ? "available" : "unavailable"}`}>
        <strong>{adapter?.display_name ?? "FEBio adapter unavailable"}</strong>
        <span>{adapter?.available ? `Ready · ${adapter.detected_version}` : "Not ready"}</span>
        {adapter?.unavailable_reasons.map((reason) => <small key={reason}>{reason}</small>)}
      </div>

      <div className="model-import">
        <label className="file-field">
          Contributor-authored FE model ZIP
          <input
            type="file"
            accept=".zip,application/zip"
            onChange={(event) => setModelPackage(event.target.files?.[0] ?? null)}
          />
        </label>
        <button type="button" onClick={importModel} disabled={!modelPackage}>
          Import solver-ready model
        </button>
      </div>

      <label className="lab-field">
        Solver-ready model
        <select value={modelId} onChange={(event) => selectModel(event.target.value)}>
          <option value="">Select an imported FE model</option>
          {availableModels.map((model) => (
            <option key={model.id} value={model.id}>{model.version} · {model.id}</option>
          ))}
        </select>
      </label>

      {selectedModel && (
        <dl className="lab-model-summary">
          <div><dt>Reconstruction</dt><dd>{selectedModel.reconstruction_id}</dd></div>
          <div><dt>Model SHA-256</dt><dd><code>{selectedModel.model_sha256}</code></dd></div>
          <div><dt>Included</dt><dd>{selectedModel.included_structures.join(", ")}</dd></div>
          <div><dt>Explicitly excluded</dt><dd>{selectedModel.excluded_structures.join(", ") || "None"}</dd></div>
        </dl>
      )}

      <div className="manifest-editor">
        <div className="manifest-actions">
          <div>
            <strong>ExperimentDefinitionV2</strong>
            <small>{assumptionCount} explicit material, ligament, and contact records</small>
          </div>
          {canLoadFixture && <button type="button" onClick={loadFixture}>Load CC0 demo assumptions</button>}
          <button type="button" onClick={exportManifest} disabled={!definitionText}>Export manifest</button>
        </div>
        <textarea
          aria-label="Experiment definition JSON"
          value={definitionText}
          onChange={(event) => setDefinitionText(event.target.value)}
          placeholder="Enter or paste the complete experiment definition. Missing values remain blocking."
          rows={18}
        />
      </div>

      <div className="lab-run-actions">
        <button
          type="button"
          onClick={runExperiment}
          disabled={!adapter?.available || !selectedModel || !definitionText || Boolean(activeJobId)}
        >
          Run independent flexion poses
        </button>
        {activeJobId && <button type="button" onClick={cancel}>Cancel and preserve partial evidence</button>}
        {retryRecord && !activeJobId && <button type="button" onClick={retry}>Retry unchanged job</button>}
        <p role="status">{status}</p>
      </div>

      {runs.length > 0 && (
        <div className="simulation-results">
          <div className="result-heading">
            <div>
              <p className="section-label">Simulated hypothesis</p>
              <h3>Flexion sweep result</h3>
            </div>
            <label className="lab-field compact">
              Run
              <select value={runIndex} onChange={(event) => {
                setRunIndex(Number(event.target.value));
                setPoseIndex(0);
              }}>
                {runs.map((item, index) => (
                  <option key={item.jobId} value={index}>Run {index + 1} · {item.jobId.slice(0, 8)}</option>
                ))}
              </select>
            </label>
            <label className="lab-field compact">
              Pose
              <select value={poseIndex} onChange={(event) => setPoseIndex(Number(event.target.value))}>
                {selectedRun?.result.poses.map((item, index) => (
                  <option key={item.flexion_angle_degrees} value={index}>
                    {item.flexion_angle_degrees}° · {item.status}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {pose && (
            <>
              <div className={`pose-status pose-${pose.status}`}>
                <strong>{pose.flexion_angle_degrees}° · {pose.status}</strong>
                {pose.diagnostic && <span>{pose.diagnostic}</span>}
              </div>
              <div className="simulation-metrics">
                <Metric label="Contact pressure" value={pose.contact_pressure_mpa} unit="MPa" />
                <Metric label="Contact area" value={pose.contact_area_mm2} unit="mm²" />
                <Metric label="Maximum displacement" value={pose.maximum_displacement_mm} unit="mm" />
                <Metric label="Reaction force" value={pose.reaction_force_n} unit="N" />
              </div>
              <SimulationFieldViewer reference={pose.field_artifact_reference} />
            </>
          )}
          {selectedRun && (
            <dl className="lab-model-summary result-provenance">
              <div><dt>Job</dt><dd>{selectedRun.jobId}</dd></div>
              <div><dt>Validation tier</dt><dd>{selectedRun.result.validation_tier}</dd></div>
              <div><dt>Solver</dt><dd>FEBio {selectedRun.result.solver_version}</dd></div>
              <div>
                <dt>Executable SHA-256</dt>
                <dd><code>{selectedRun.result.solver_executable_sha256}</code></dd>
              </div>
              <div>
                <dt>Definition SHA-256</dt>
                <dd><code>{selectedRun.result.experiment_definition_sha256}</code></dd>
              </div>
            </dl>
          )}
          <p className="chart-note">
            {runs.length} immutable run{runs.length === 1 ? "" : "s"} retained for comparison.
            Numerical convergence is not scientific or clinical validation.
          </p>
          {runs.length > 1 && pose && (
            <div className="run-comparison">
              <h4>Run comparison at {pose.flexion_angle_degrees}°</h4>
              <table>
                <thead><tr><th>Run</th><th>Load range</th><th>Status</th><th>Pressure</th><th>Reaction</th></tr></thead>
                <tbody>
                  {runs.map((item, index) => {
                    const matchingPose = item.result.poses.find(
                      (candidate) => candidate.flexion_angle_degrees === pose.flexion_angle_degrees,
                    );
                    return (
                      <tr key={item.jobId}>
                        <td>{index + 1}</td>
                        <td>{loadRange(item.definition)}</td>
                        <td>{matchingPose?.status ?? "unavailable"}</td>
                        <td>{formatValue(matchingPose?.contact_pressure_mpa, "MPa")}</td>
                        <td>{formatValue(matchingPose?.reaction_force_n, "N")}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function loadRange(definition: ExperimentManifest): string {
  const boundary = definition.boundary;
  if (!boundary || typeof boundary !== "object") return "Unavailable";
  const load = (boundary as Record<string, unknown>).compressive_load;
  if (!load || typeof load !== "object") return "Unavailable";
  const sourced = load as Record<string, unknown>;
  const range = sourced.range;
  return Array.isArray(range) && range.length === 2
    ? `${String(range[0])}–${String(range[1])} ${String(sourced.unit ?? "")}`
    : "Unavailable";
}

function formatValue(value: number | null | undefined, unit: string): string {
  return typeof value === "number" ? `${value.toPrecision(4)} ${unit}` : "Unavailable";
}

function Metric({ label, value, unit }: { label: string; value: number | null; unit: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value === null ? "Unavailable" : `${value.toPrecision(4)} ${unit}`}</strong>
    </div>
  );
}

async function detail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    return typeof payload.detail === "string" ? payload.detail : `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}
