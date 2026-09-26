import type { RankedNeighborhood } from "../api/scoring";
import { priorityFill } from "../lib/priorityColors";

interface RankingsPanelProps {
  rankings: RankedNeighborhood[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/**
 * Ranked neighborhood list (rank 1 = highest green deficiency).
 */
export function RankingsPanel({ rankings, selectedId, onSelect }: RankingsPanelProps) {
  return (
    <aside className="rankings-panel">
      <h2>Ranking</h2>
      <p className="rankings-copy">Highest deficiency first.</p>
      {rankings.length === 0 ? (
        <p className="rankings-empty">Nothing ranked yet.</p>
      ) : (
        <ol className="rankings-list">
          {rankings.map((item) => {
            const band = item.green_deficiency_score.priority_band;
            const selected = item.id === selectedId;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  className={selected ? "rank-item rank-item--selected" : "rank-item"}
                  onClick={() => onSelect(item.id)}
                >
                  <span className="rank-num">{item.rank}</span>
                  <span className="rank-body">
                    <strong>{item.label}</strong>
                    <span className="rank-meta">
                      <span
                        className="priority-dot"
                        style={{ backgroundColor: priorityFill(band) }}
                        aria-hidden="true"
                      />
                      {item.green_deficiency_score.score.toFixed(1)} · {band}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </aside>
  );
}
