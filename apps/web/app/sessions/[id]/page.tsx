import { HistoricalSessionDetail } from "@/components/historical-session-detail";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function SessionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main>
      <section className="hero compact-hero">
        <Link href="/">← Back to capture and history</Link>
        <div className="eyebrow">Knee Twin · Longitudinal evidence</div>
        <h1>Historical session replay</h1>
        <p className="lede">
          Preserved evidence and versioned analyses are replayed without recalculating biomechanics
          in the browser.
        </p>
      </section>
      <HistoricalSessionDetail sessionId={id} />
    </main>
  );
}
