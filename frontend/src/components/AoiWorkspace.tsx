import { useCallback, useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import {
  requestNeighborhoodBrief,
  requestNeighborhoodComparison,
  requestVegetationPlan,
  type AgentNarrative,
  type NeighborhoodSnapshotPayload,
} from "../api/agent";
import {
  createAnalysisJob,
  runAnalysisJob,
  type AnalysisOrchestration,
} from "../api/analysisJobs";
import {
  createAreaOfInterest,
  deleteAreaOfInterest,
  listAreasOfInterest,
  type AreaOfInterest,
  type GeoJsonGeometry,
} from "../api/aois";
import { sendComparisonSummaryEmail } from "../api/notifications";
import { bootstrapWorkspace, listMyProjects } from "../api/projects";
import type { AnalysisReport } from "../api/reports";
import { listMyScoringProfiles } from "../api/scoringProfiles";
import { rankNeighborhoods, type RankedNeighborhood } from "../api/scoring";
import { priorityFill, priorityStroke } from "../lib/priorityColors";
import { geometryCentroid } from "../lib/geometryCentroid";
import {
  heatExposureFill,
  vegetationDensityFill,
  vegetationHotspotFill,
  type OverlayMode,
} from "../lib/vegetationColors";
import { AgentNarrativePanel } from "./AgentNarrativePanel";
import { AnalysisOverlayLayer } from "./AnalysisOverlayLayer";
import { ExplainabilityPanel } from "./ExplainabilityPanel";
import { PolygonDrawControl, type DrawnPolygonPayload } from "./PolygonDrawControl";
import { RankingsPanel } from "./RankingsPanel";
import "leaflet/dist/leaflet.css";

type WorkspaceStep = 1 | 2;

interface AoiAnalysisResult {
  orchestration: AnalysisOrchestration;
  report: AnalysisReport | null;
}

interface AoiWorkspaceProps {
  accountLabel?: string;
  onLogout?: () => void;
}

/**
 * Authenticated planning workspace: city AOI → neighborhoods → compare + email.
 */
export function AoiWorkspace({ accountLabel, onLogout }: AoiWorkspaceProps) {
  const [step, setStep] = useState<WorkspaceStep>(1);
  const [projectId, setProjectId] = useState("");
  const [scoringProfileId, setScoringProfileId] = useState("");
  const [cityName, setCityName] = useState("City study area");
  const [neighborhoodName, setNeighborhoodName] = useState("Neighborhood");
  const [aois, setAois] = useState<AreaOfInterest[]>([]);
  const [pendingGeometry, setPendingGeometry] = useState<GeoJsonGeometry | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [resultsByAoi, setResultsByAoi] = useState<Record<string, AoiAnalysisResult>>({});
  const [rankings, setRankings] = useState<RankedNeighborhood[]>([]);
  const [selectedAoiIdByStep, setSelectedAoiIdByStep] = useState<
    Record<WorkspaceStep, string | null>
  >({ 1: null, 2: null });
  const [overlayModeByStep, setOverlayModeByStep] = useState<Record<WorkspaceStep, OverlayMode>>({
    1: "vegetation",
    2: "vegetation",
  });
  const [lastVegetationSource, setLastVegetationSource] = useState<string | null>(null);
  const [lastHeatSource, setLastHeatSource] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);
  const [agentNarrative, setAgentNarrative] = useState<AgentNarrative | null>(null);
  const [agentBusy, setAgentBusy] = useState(false);

  const cityAoi = useMemo(() => aois.find((a) => a.kind === "city") ?? null, [aois]);
  const neighborhoodAois = useMemo(
    () => aois.filter((a) => a.kind === "neighborhood"),
    [aois],
  );

  const selectedAoiId = selectedAoiIdByStep[step];
  const overlayMode = overlayModeByStep[step];

  const setSelectedAoiId = (aoiId: string | null) => {
    setSelectedAoiIdByStep((prev) => ({ ...prev, [step]: aoiId }));
  };

  const setOverlayMode = (mode: OverlayMode) => {
    setOverlayModeByStep((prev) => ({ ...prev, [step]: mode }));
  };

  const goToStep = (next: WorkspaceStep) => {
    setStep(next);
    setPendingGeometry(null);
  };

  const refresh = useCallback(async (id: string) => {
    if (!id) {
      setAois([]);
      return;
    }
    const items = await listAreasOfInterest(id);
    setAois(items);
    const city = items.find((a) => a.kind === "city");
    if (city) {
      setStep(2);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setBooting(true);
      setError(null);
      try {
        const projects = await listMyProjects();
        const existing = projects[0];
        if (existing) {
          const profiles = await listMyScoringProfiles();
          let profileId = profiles[0]?.id ?? "";
          if (!profileId) {
            const boot = await bootstrapWorkspace(existing.name);
            profileId = boot.scoringProfile.id;
          }
          if (cancelled) {
            return;
          }
          setProjectId(existing.id);
          setScoringProfileId(profileId);
          await refresh(existing.id);
          setMessage(`Loaded project “${existing.name}”.`);
        } else {
          const boot = await bootstrapWorkspace();
          if (cancelled) {
            return;
          }
          setProjectId(boot.project.id);
          setScoringProfileId(boot.scoringProfile.id);
          setMessage("Project ready — draw your city study area (step 1).");
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load workspace");
        }
      } finally {
        if (!cancelled) {
          setBooting(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const selectedReport = useMemo(() => {
    if (!selectedAoiId) {
      return null;
    }
    return resultsByAoi[selectedAoiId]?.report ?? null;
  }, [resultsByAoi, selectedAoiId]);

  const selectedAoiName = useMemo(() => {
    return aois.find((a) => a.id === selectedAoiId)?.name;
  }, [aois, selectedAoiId]);

  const selectedOverlayMask = useMemo(() => {
    if (!selectedAoiId || overlayMode === "off") {
      return null;
    }
    const selected = aois.find((a) => a.id === selectedAoiId);
    // City overlays only on step 1; neighborhood overlays only on step 2.
    if (!selected) {
      return null;
    }
    if (step === 1 && selected.kind !== "city") {
      return null;
    }
    if (step === 2 && selected.kind !== "neighborhood") {
      return null;
    }
    const orch = resultsByAoi[selectedAoiId]?.orchestration;
    if (!orch) {
      return null;
    }
    if (overlayMode === "vegetation") {
      return orch.vegetation_mask ?? null;
    }
    if (overlayMode === "veg_hotspots") {
      return orch.vegetation_hotspot_mask ?? null;
    }
    if (overlayMode === "heat") {
      return orch.heat_exposure_mask ?? null;
    }
    return null;
  }, [aois, resultsByAoi, selectedAoiId, overlayMode, step]);

  const scoreByAoi = useMemo(() => {
    const map: Record<string, { score: number; band: string }> = {};
    for (const [aoiId, result] of Object.entries(resultsByAoi)) {
      const gds = result.orchestration.green_deficiency_score;
      map[aoiId] = { score: gds.score, band: gds.priority_band };
    }
    for (const ranked of rankings) {
      map[ranked.id] = {
        score: ranked.green_deficiency_score.score,
        band: ranked.green_deficiency_score.priority_band,
      };
    }
    return map;
  }, [resultsByAoi, rankings]);

  const runAnalysisForAois = async (targets: AreaOfInterest[]) => {
    if (!projectId || !scoringProfileId) {
      throw new Error("Project is not ready yet.");
    }

    const nextResults: Record<string, AoiAnalysisResult> = { ...resultsByAoi };
    for (const aoi of targets) {
      setMessage(`Analyzing “${aoi.name}”…`);
      const job = await createAnalysisJob({
        project_id: projectId,
        aoi_id: aoi.id,
        scoring_profile_id: scoringProfileId,
      });
      const run = await runAnalysisJob(job.id, {
        auto_start: true,
      });
      nextResults[aoi.id] = {
        orchestration: run.analysis,
        report: run.analysis.report,
      };
    }
    setResultsByAoi(nextResults);

    const sources = [
      ...new Set(
        Object.values(nextResults).map((r) => r.orchestration.vegetation_source).filter(Boolean),
      ),
    ];
    setLastVegetationSource(sources.join(", ") || null);
    const heatSources = [
      ...new Set(
        Object.values(nextResults)
          .map((r) => r.orchestration.heat_source)
          .filter(Boolean) as string[],
      ),
    ];
    setLastHeatSource(heatSources.join(", ") || null);
    return nextResults;
  };

  const handleSaveGeometry = async (geometry: GeoJsonGeometry) => {
    setError(null);
    setMessage(null);
    if (!projectId) {
      setError("Project is still loading.");
      return;
    }
    setBusy(true);
    try {
      if (step === 1) {
        if (cityAoi) {
          setError("City study area already exists. Continue to neighborhoods (step 2).");
          return;
        }
        const created = await createAreaOfInterest({
          project_id: projectId,
          name: cityName.trim() || "City study area",
          description: "City-scale study boundary",
          geometry,
          kind: "city",
        });
        setPendingGeometry(null);
        await refresh(projectId);
        setSelectedAoiIdByStep((prev) => ({ ...prev, 1: created.id }));
        setMessage("City area saved. Run city analysis, then continue to neighborhoods.");
      } else {
        if (!cityAoi) {
          setError("Save a city study area first (step 1).");
          return;
        }
        const created = await createAreaOfInterest({
          project_id: projectId,
          name: neighborhoodName.trim() || "Neighborhood",
          description: "Neighborhood comparison polygon",
          geometry,
          kind: "neighborhood",
          parent_aoi_id: cityAoi.id,
        });
        setPendingGeometry(null);
        await refresh(projectId);
        setSelectedAoiIdByStep((prev) => ({ ...prev, 2: created.id }));
        setMessage("Neighborhood saved.");
      }
    } catch (err: unknown) {
      setError(`Save failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const handleDrawn = (geometry: DrawnPolygonPayload) => {
    setPendingGeometry(geometry as GeoJsonGeometry);
    setMessage(
      step === 1
        ? "City polygon drawn — click Save to continue."
        : "Neighborhood drawn — click Save to add it.",
    );
  };

  const handleUpload = async (file: File | null) => {
    if (!file) {
      return;
    }
    setError(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as Record<string, unknown>;
      await handleSaveGeometry(parsed as unknown as GeoJsonGeometry);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid GeoJSON file");
    }
  };

  const handleDelete = async (aoiId: string) => {
    setBusy(true);
    setError(null);
    try {
      await deleteAreaOfInterest(aoiId);
      setResultsByAoi((prev) => {
        const next = { ...prev };
        delete next[aoiId];
        return next;
      });
      setRankings((prev) => prev.filter((r) => r.id !== aoiId));
      setSelectedAoiIdByStep((prev) => ({
        1: prev[1] === aoiId ? null : prev[1],
        2: prev[2] === aoiId ? null : prev[2],
      }));
      setMessage("AOI deleted.");
      await refresh(projectId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  };

  const handleAnalyzeCity = async () => {
    if (!cityAoi) {
      setError("Draw and save the city study area first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await runAnalysisForAois([cityAoi]);
      setSelectedAoiIdByStep((prev) => ({ ...prev, 1: cityAoi.id }));
      setMessage(
        "City analysis complete — a summary email was queued for your account. Continue to neighborhoods.",
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "City analysis failed");
    } finally {
      setBusy(false);
    }
  };

  const buildSnapshots = (
    results: Record<string, AoiAnalysisResult>,
    ranked: RankedNeighborhood[],
  ): NeighborhoodSnapshotPayload[] => {
    const rankById = Object.fromEntries(ranked.map((row) => [row.id, row.rank]));
    return neighborhoodAois
      .filter((aoi) => results[aoi.id])
      .map((aoi) => {
        const orch = results[aoi.id].orchestration;
        return {
          id: aoi.id,
          name: aoi.name,
          score: orch.green_deficiency_score.score,
          priority_band: orch.green_deficiency_score.priority_band,
          rank: rankById[aoi.id] ?? null,
          indicators: orch.indicators,
        };
      });
  };

  const handleAgentBrief = async (aoiId: string) => {
    const result = resultsByAoi[aoiId];
    if (!result || !projectId) {
      setError("Analyse this neighborhood first, then request an agent brief.");
      return;
    }
    setAgentBusy(true);
    setError(null);
    setSelectedAoiId(aoiId);
    try {
      const peers = buildSnapshots(resultsByAoi, rankings);
      const focus = peers.find((p) => p.id === aoiId);
      if (!focus) {
        throw new Error("Neighborhood score not found.");
      }
      const narrative = await requestNeighborhoodBrief({
        project_id: projectId,
        focus,
        peers,
      });
      setAgentNarrative(narrative);
      setMessage(`Agent brief ready for “${focus.name}”.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Agent brief failed");
    } finally {
      setAgentBusy(false);
    }
  };

  const handleAgentCompareAll = async () => {
    const scored = neighborhoodAois.filter((aoi) => resultsByAoi[aoi.id]);
    if (scored.length === 0) {
      setError("Analyse neighborhoods first (Analyse & compare), then run agent compare.");
      return;
    }
    if (!projectId) {
      setError("Project is not ready yet.");
      return;
    }
    setAgentBusy(true);
    setError(null);
    try {
      const neighborhoods = buildSnapshots(resultsByAoi, rankings);
      const narrative = await requestNeighborhoodComparison({
        project_id: projectId,
        neighborhoods,
      });
      setAgentNarrative(narrative);
      setMessage(`Agent comparison ready for ${neighborhoods.length} neighborhood(s).`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Agent comparison failed");
    } finally {
      setAgentBusy(false);
    }
  };

  const handleVegetationPlan = async (aoiId: string) => {
    const result = resultsByAoi[aoiId];
    if (!result || !projectId) {
      setError("Analyse this neighborhood first, then request a vegetation plan.");
      return;
    }
    if (!cityAoi) {
      setError("Save a city study area first so the agent can use its location.");
      return;
    }
    const center = geometryCentroid(cityAoi.geometry);
    if (!center) {
      setError("Could not read city coordinates from the city polygon.");
      return;
    }
    setAgentBusy(true);
    setError(null);
    setSelectedAoiId(aoiId);
    try {
      const peers = buildSnapshots(resultsByAoi, rankings);
      const focus = peers.find((p) => p.id === aoiId);
      if (!focus) {
        throw new Error("Neighborhood score not found.");
      }
      const narrative = await requestVegetationPlan({
        project_id: projectId,
        city: {
          name: cityAoi.name,
          latitude: center.lat,
          longitude: center.lon,
        },
        focus,
      });
      setAgentNarrative(narrative);
      setMessage(`Vegetation plan ready for “${focus.name}”.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Vegetation plan failed");
    } finally {
      setAgentBusy(false);
    }
  };

  const handleCompareNeighborhoods = async () => {
    if (neighborhoodAois.length === 0) {
      setError("Add at least one neighborhood before comparing.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const nextResults = await runAnalysisForAois(neighborhoodAois);
      const ranked = await rankNeighborhoods({
        scoring_profile_id: scoringProfileId,
        items: neighborhoodAois.map((aoi) => ({
          id: aoi.id,
          label: aoi.name,
          indicators: nextResults[aoi.id].orchestration.indicators,
        })),
      });
      setRankings(ranked.rankings);
      setSelectedAoiIdByStep((prev) => ({
        ...prev,
        2: ranked.rankings[0]?.id ?? neighborhoodAois[0]?.id ?? null,
      }));

      await sendComparisonSummaryEmail({
        project_id: projectId,
        rankings: ranked.rankings.map((row, index) => ({
          rank: index + 1,
          name: row.label,
          score: row.green_deficiency_score.score,
          priority_band: row.green_deficiency_score.priority_band,
        })),
        notes: cityAoi
          ? `Compared against city study area “${cityAoi.name}”.`
          : "Neighborhood comparison complete.",
      });

      setMessage(
        `Comparison complete — ${ranked.rankings.length} neighborhood(s) ranked. A summary email was sent to your account.`,
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setBusy(false);
    }
  };

  const visibleAois = step === 1 ? (cityAoi ? [cityAoi] : []) : neighborhoodAois;
  const mapAois = step === 1 ? (cityAoi ? [cityAoi] : []) : aois;

  return (
    <section className="planning-workspace">
      <div className="aoi-panel">
        <div className="aoi-panel-top">
          <p className="aoi-product">GreenCity</p>
          {(accountLabel || onLogout) && (
            <div className="aoi-account">
              {accountLabel && <span className="aoi-account-name">{accountLabel}</span>}
              {onLogout && (
                <button type="button" className="aoi-logout" onClick={onLogout}>
                  Log out
                </button>
              )}
            </div>
          )}
        </div>

        <nav className="workspace-steps" aria-label="Workflow">
          <button
            type="button"
            className={step === 1 ? "workspace-step workspace-step--active" : "workspace-step"}
            onClick={() => goToStep(1)}
            disabled={busy}
          >
            City
          </button>
          <button
            type="button"
            className={step === 2 ? "workspace-step workspace-step--active" : "workspace-step"}
            onClick={() => goToStep(2)}
            disabled={busy || !cityAoi}
          >
            Neighborhoods
          </button>
        </nav>

        <p className="aoi-copy">
          {step === 1
            ? "Draw the city boundary, then run analysis."
            : "Add districts, compare them, open a brief or planting plan when needed."}
        </p>
        <p className="aoi-hint">
          Draw polygon on the map → add points → Finish (or Enter).
        </p>

        {booting && <p className="aoi-message">Preparing project…</p>}

        <div className="aoi-controls">
          {step === 1 ? (
            <label className="field">
              <span>City area name</span>
              <input value={cityName} onChange={(event) => setCityName(event.target.value)} />
            </label>
          ) : (
            <label className="field">
              <span>Neighborhood name</span>
              <input
                value={neighborhoodName}
                onChange={(event) => setNeighborhoodName(event.target.value)}
              />
            </label>
          )}
          <label className="file-field">
            <span>Upload GeoJSON</span>
            <input
              type="file"
              accept=".json,.geojson,application/geo+json,application/json"
              onChange={(event) => {
                void handleUpload(event.target.files?.[0] ?? null);
                event.target.value = "";
              }}
            />
          </label>
          {pendingGeometry && (
            <button
              type="button"
              onClick={() => void handleSaveGeometry(pendingGeometry)}
              disabled={busy || booting}
            >
              Save drawn polygon
            </button>
          )}
          {step === 1 ? (
            <button
              type="button"
              className="btn-primary"
              onClick={() => void handleAnalyzeCity()}
              disabled={busy || booting || !cityAoi}
            >
              Analyse city area
            </button>
          ) : (
            <>
              <button
                type="button"
                className="btn-primary"
                onClick={() => void handleCompareNeighborhoods()}
                disabled={busy || booting || neighborhoodAois.length === 0}
              >
                Analyse &amp; compare neighborhoods
              </button>
              <button
                type="button"
                className="btn-agent"
                onClick={() => void handleAgentCompareAll()}
                disabled={
                  busy || agentBusy || booting || neighborhoodAois.every((a) => !resultsByAoi[a.id])
                }
              >
                Compare all
              </button>
            </>
          )}
          <fieldset className="field overlay-fieldset">
            <legend>Map overlay</legend>
            <label className="radio-field">
              <input
                type="radio"
                name="overlay-mode"
                checked={overlayMode === "off"}
                onChange={() => setOverlayMode("off")}
              />
              None
            </label>
            <label className="radio-field">
              <input
                type="radio"
                name="overlay-mode"
                checked={overlayMode === "vegetation"}
                onChange={() => setOverlayMode("vegetation")}
              />
              Vegetation density
            </label>
            <label className="radio-field">
              <input
                type="radio"
                name="overlay-mode"
                checked={overlayMode === "veg_hotspots"}
                onChange={() => setOverlayMode("veg_hotspots")}
              />
              Low-vegetation hotspots
            </label>
            <label className="radio-field">
              <input
                type="radio"
                name="overlay-mode"
                checked={overlayMode === "heat"}
                onChange={() => setOverlayMode("heat")}
              />
              Heat exposure
            </label>
          </fieldset>
        </div>

        {message && <p className="aoi-message">{message}</p>}
        {error && <p className="aoi-error">{error}</p>}
        {lastVegetationSource && (
          <p className="aoi-source">Vegetation source: {lastVegetationSource}</p>
        )}
        {lastHeatSource && <p className="aoi-source">Heat source: {lastHeatSource}</p>}

        <ul className="aoi-list">
          {visibleAois.map((aoi) => {
            const scored = scoreByAoi[aoi.id];
            const hasAnalysis = Boolean(resultsByAoi[aoi.id]);
            return (
              <li key={aoi.id}>
                <button
                  type="button"
                  className={
                    selectedAoiId === aoi.id ? "aoi-select aoi-select--active" : "aoi-select"
                  }
                  onClick={() => setSelectedAoiId(aoi.id)}
                >
                  <strong>
                    {aoi.kind === "city" ? "City · " : ""}
                    {aoi.name}
                  </strong>
                  <span>
                    {scored ? `${scored.score.toFixed(1)} · ${scored.band}` : aoi.geometry.type}
                  </span>
                </button>
                <div className="aoi-row-actions">
                  {step === 2 && hasAnalysis && (
                    <>
                      <button
                        type="button"
                        className="btn-agent-inline"
                        title="Ask the agent for a comprehensive neighborhood analysis"
                        onClick={() => void handleAgentBrief(aoi.id)}
                        disabled={busy || agentBusy}
                      >
                        Brief
                      </button>
                      <button
                        type="button"
                        className="btn-agent-inline"
                        title="Short / mid / long-term planting plan"
                        onClick={() => void handleVegetationPlan(aoi.id)}
                        disabled={busy || agentBusy || !cityAoi}
                      >
                        Planting
                      </button>
                    </>
                  )}
                  <button type="button" onClick={() => void handleDelete(aoi.id)} disabled={busy}>
                    Delete
                  </button>
                </div>
              </li>
            );
          })}
          {projectId && visibleAois.length === 0 && (
            <li className="aoi-empty">
              {step === 1 ? "No city area yet — draw it on the map." : "No neighborhoods yet."}
            </li>
          )}
        </ul>
      </div>

      <div className="map-column">
        <div className="aoi-map-shell">
          <MapContainer center={[48.8566, 2.3522]} zoom={12} className="aoi-map" scrollWheelZoom>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <PolygonDrawControl onCreated={handleDrawn} />
            {mapAois.map((aoi) => {
              const isCity = aoi.kind === "city";
              // On the neighborhoods tab, city is context outline only — no city analysis overlay.
              const cityContextOnly = step === 2 && isCity;
              const scored = cityContextOnly ? undefined : scoreByAoi[aoi.id];
              const band = scored?.band ?? "unset";
              const selected = !cityContextOnly && selectedAoiId === aoi.id;
              const hasOverlay = Boolean(selectedOverlayMask?.features?.length);
              const lightFill = overlayMode !== "off" && selected && hasOverlay;
              return (
                <GeoJSON
                  key={`${aoi.id}-${step}-${band}-${selected ? "on" : "off"}-${overlayMode}`}
                  data={
                    {
                      type: "Feature",
                      properties: { name: aoi.name, kind: aoi.kind },
                      geometry: aoi.geometry,
                    } as GeoJSON.Feature
                  }
                  style={() => ({
                    color: cityContextOnly
                      ? "#2f7fb8"
                      : scored
                        ? priorityStroke(band)
                        : isCity
                          ? "#2f7fb8"
                          : "#6bb8e8",
                    fillColor: cityContextOnly
                      ? "#4aa3d9"
                      : scored
                        ? priorityFill(band)
                        : isCity
                          ? "#4aa3d9"
                          : "#87ceeb",
                    fillOpacity: cityContextOnly
                      ? 0.06
                      : lightFill
                        ? 0.08
                        : scored
                          ? selected
                            ? 0.72
                            : 0.5
                          : isCity
                            ? 0.12
                            : 0.28,
                    weight: cityContextOnly ? 2 : selected ? 3 : isCity ? 2.5 : 1.5,
                    dashArray: cityContextOnly || (isCity && !scored) ? "6 4" : undefined,
                  })}
                  eventHandlers={{
                    click: () => {
                      if (cityContextOnly) {
                        return;
                      }
                      setSelectedAoiId(aoi.id);
                    },
                  }}
                />
              );
            })}
            <AnalysisOverlayLayer mask={selectedOverlayMask} mode={overlayMode} />
          </MapContainer>
          <div className="map-legend" aria-hidden="true">
            <span>
              <i style={{ background: priorityFill("high") }} /> High priority
            </span>
            <span>
              <i style={{ background: priorityFill("medium") }} /> Medium
            </span>
            <span>
              <i style={{ background: priorityFill("low") }} /> Low
            </span>
          </div>
          {overlayMode === "vegetation" && selectedOverlayMask?.features?.length ? (
            <div className="map-legend map-legend--veg" aria-hidden="true">
              <span>
                <i style={{ background: vegetationDensityFill("sparse") }} /> Sparse
              </span>
              <span>
                <i style={{ background: vegetationDensityFill("moderate") }} /> Moderate
              </span>
              <span>
                <i style={{ background: vegetationDensityFill("dense") }} /> Dense
              </span>
            </div>
          ) : null}
          {overlayMode === "veg_hotspots" && selectedOverlayMask?.features?.length ? (
            <div className="map-legend map-legend--veg" aria-hidden="true">
              <span>
                <i style={{ background: vegetationHotspotFill("elevated") }} /> Elevated
              </span>
              <span>
                <i style={{ background: vegetationHotspotFill("high") }} /> High
              </span>
              <span>
                <i style={{ background: vegetationHotspotFill("critical") }} /> Critical
              </span>
            </div>
          ) : null}
          {overlayMode === "heat" && selectedOverlayMask?.features?.length ? (
            <div className="map-legend map-legend--veg" aria-hidden="true">
              <span>
                <i style={{ background: heatExposureFill("elevated") }} /> Elevated
              </span>
              <span>
                <i style={{ background: heatExposureFill("high") }} /> High
              </span>
              <span>
                <i style={{ background: heatExposureFill("extreme") }} /> Extreme
              </span>
            </div>
          ) : null}
        </div>

        <div className="results-row">
          <RankingsPanel
            rankings={step === 2 ? rankings : []}
            selectedId={selectedAoiId}
            onSelect={setSelectedAoiId}
          />
          <ExplainabilityPanel report={selectedReport} aoiName={selectedAoiName} />
        </div>
        {step === 2 && (
          <AgentNarrativePanel narrative={agentNarrative} busy={agentBusy} />
        )}
      </div>
    </section>
  );
}
