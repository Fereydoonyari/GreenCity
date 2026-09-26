/**
 * Auth API: register, login, me.
 */

import { apiJson, setAccessToken } from "./http";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface AuthSession {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export async function registerAccount(input: {
  email: string;
  full_name: string;
  password: string;
}): Promise<AuthSession> {
  const session = await apiJson<AuthSession>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
  setAccessToken(session.access_token);
  return session;
}

export async function loginAccount(input: {
  email: string;
  password: string;
}): Promise<AuthSession> {
  const session = await apiJson<AuthSession>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
  setAccessToken(session.access_token);
  return session;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  return apiJson<AuthUser>("/api/v1/auth/me");
}

export function logoutAccount(): void {
  setAccessToken(null);
}
