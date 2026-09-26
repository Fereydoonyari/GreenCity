import type { AnalysisReport } from "../api/reports";
import { priorityFill } from "../lib/priorityColors";

interface ExplainabilityPanelProps {
  report: AnalysisReport | null;
  aoiName?: string;
}

/**
 * Structured explainable report: summary, ranked drivers, recommendations.
 */
export function ExplainabilityPanel({ report, aoiName }: ExplainabilityPanelProps) {
  if (!report) {
    return (
      <aside className="explain-panel explain-panel--empty">
        <h2>Score breakdown</h2>
        <p>Run analysis, then select an area to see what drives its score.</p>
      </aside>
    );
  }

  const drivers = [...report.drivers].sort(
    (a, b) => b.weighted_points - a.weighted_points,
  );
  const maxPts = Math.max(...drivers.map((d) => d.weighted_points), 1);

  return (
    <aside className="explain-panel" aria-live="polite">
      <p className="explain-meta">{aoiName ?? "Selected area"}</p>
      <h2>{report.headline}</h2>
      <div className="explain-score-row">
        <span
          className="priority-badge"
          style={{ backgroundColor: priorityFill(report.priority_band) }}
        >
          {report.priority_band}
        </span>
        <span className="explain-score">{report.score.toFixed(1)} / 100</span>
      </div>
      <p className="explain-summary">{report.executive_summary}</p>

      <h3>Drivers</h3>
      <ul className="driver-list">
        {drivers.map((driver) => (
          <li key={driver.key}>
            <div className="driver-meta">
              <strong>{driver.label}</strong>
              <span>{driver.weighted_points.toFixed(1)} pts</span>
            </div>
            <div className="driver-bar" aria-hidden="true">
              <span
                style={{ width: `${(driver.weighted_points / maxPts) * 100}%` }}
              />
            </div>
            <p>{driver.explanation}</p>
          </li>
        ))}
      </ul>

      <h3>Suggestions</h3>
      <ul className="recommend-list">
        {report.recommendations.map((rec) => (
          <li key={rec}>{rec}</li>
        ))}
      </ul>

      <details className="explain-method">
        <summary>How this was calculated</summary>
        <p>{report.methodology_notes}</p>
        <p className="explain-source">Source: {report.source}</p>
      </details>
    </aside>
  );
}
