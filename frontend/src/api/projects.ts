/**
 * Project helpers for the authenticated planning workspace.
 */

import { apiJson } from "./http";
import { createBalancedScoringProfile, type ScoringProfile } from "./scoringProfiles";

export interface Project {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  status: string;
}

export interface WorkspaceBootstrap {
  project: Project;
  scoringProfile: ScoringProfile;
}

export async function listMyProjects(): Promise<Project[]> {
  return apiJson<Project[]>("/api/v1/projects");
}

export async function createProject(input: {
  name: string;
  description?: string;
}): Promise<Project> {
  return apiJson<Project>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify({
      name: input.name,
      description: input.description ?? "",
      status: "active",
    }),
  });
}

/**
 * Create a project and balanced scoring profile for the signed-in user.
 */
export async function bootstrapWorkspace(projectName?: string): Promise<WorkspaceBootstrap> {
  const stamp = new Date().toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  const project = await createProject({
    name: projectName?.trim() || `Study — ${stamp}`,
    description: "City-scale vegetation and neighborhood comparison",
  });
  const scoringProfile = await createBalancedScoringProfile();
  return { project, scoringProfile };
}
