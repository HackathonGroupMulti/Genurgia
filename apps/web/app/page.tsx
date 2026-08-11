import { getBackendHealth } from "@/lib/biomechanics-api";
import { VideoUpload } from "@/components/video-upload";

export const dynamic = "force-dynamic";

export default async function Home() {
  const health = await getBackendHealth();
  const connected = health.ok;

  return (
    <main>
      <section className="hero" aria-labelledby="page-title">
        <div className="eyebrow">Knee Twin · Milestone 0</div>
        <h1 id="page-title">Movement, made comparable.</h1>
        <p className="lede">
          A foundation for turning recorded movement into a longitudinal,
          confidence-aware view of lower-body kinematics.
        </p>

        <div className={`status-card ${connected ? "connected" : "disconnected"}`}>
          <span className="status-dot" aria-hidden="true" />
          <div>
            <p className="status-label">Biomechanics API</p>
            <p className="status-value" role="status">
              {connected ? `Connected to ${health.data.service}` : "Unavailable"}
            </p>
            {!connected && <p className="status-detail">{health.error}</p>}
          </div>
        </div>

        <p className="disclaimer">
          Knee Twin is a movement-analysis tool, not a medical diagnostic device.
        </p>
      </section>
      <VideoUpload />
    </main>
  );
}
