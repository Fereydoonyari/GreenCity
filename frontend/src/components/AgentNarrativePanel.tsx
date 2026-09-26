import type { AgentNarrative } from "../api/agent";

interface AgentNarrativePanelProps {
  narrative: AgentNarrative | null;
  busy?: boolean;
}

/**
 * Displays comprehensive agent brief / comparison write-ups.
 */
export function AgentNarrativePanel({ narrative, busy }: AgentNarrativePanelProps) {
  if (busy) {
    return (
      <aside className="agent-panel agent-panel--busy" aria-live="polite">
        <h2>Notes</h2>
        <p>Writing…</p>
      </aside>
    );
  }

  if (!narrative) {
    return (
      <aside className="agent-panel agent-panel--empty">
        <h2>Notes</h2>
        <p>
          After a neighborhood is analysed, use Brief, Planting plan, or Compare all to fill this
          space.
        </p>
      </aside>
    );
  }

  const kindLabel =
    narrative.kind === "neighborhood_comparison"
      ? "Comparison"
      : narrative.kind === "vegetation_plan"
        ? "Planting plan"
        : "Brief";

  return (
    <aside className="agent-panel" aria-live="polite">
      <p className="agent-meta">
        {kindLabel}
        {narrative.source === "llm_augmented" ? " · edited" : ""}
      </p>
      <h2>{narrative.title}</h2>
      {narrative.sections.map((section) => (
        <section key={section.title} className="agent-section">
          <h3>{section.title}</h3>
          <p>{section.body}</p>
        </section>
      ))}
    </aside>
  );
}
