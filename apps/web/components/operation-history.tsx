"use client";

import { useEffect, useState } from "react";
import {
  parseProcessingOperationList,
  type ProcessingOperation,
} from "@/lib/operation-contracts";

export function OperationHistory({ refreshKey }: { refreshKey: string }) {
  const [operations, setOperations] = useState<ProcessingOperation[] | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const response = await fetch("/api/operations", { cache: "no-store" });
        const parsed = response.ok ? parseProcessingOperationList(await response.json()) : null;
        if (active) setOperations(parsed?.operations.slice(0, 5) ?? []);
      } catch {
        if (active) setOperations([]);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [refreshKey]);

  if (!operations || operations.length === 0) return null;
  return (
    <section className="operation-history" aria-labelledby="operation-history-title">
      <h3 id="operation-history-title">Recent processing provenance</h3>
      <ul>
        {operations.map((operation) => (
          <li key={operation.id} className={`operation-${operation.status}`}>
            <strong>{operation.status}</strong> · {operation.stage} · {operation.duration_ms ?? "—"} ms
            <code>{operation.id}</code>
            {operation.error_detail && <span>{operation.error_detail}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}
