/**
 * Health API client.
 * Talks to the FastAPI readiness endpoint via the Vite proxy (`/api`).
 */

export interface HealthStatus {
  status: string;
  database: string;
  version: string;
}

/**
 * Fetch application health from the backend.
 *
 * @throws Error when the response is not OK or the payload is invalid.
 */
export async function fetchHealth(): Promise<HealthStatus> {
  const response = await fetch("/api/v1/health");

  if (!response.ok) {
    throw new Error(`Health check failed (${response.status})`);
  }

  return (await response.json()) as HealthStatus;
}
