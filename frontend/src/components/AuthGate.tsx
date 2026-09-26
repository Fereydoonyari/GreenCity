import { useState } from "react";
import { loginAccount, registerAccount, type AuthUser } from "../api/auth";

interface AuthGateProps {
  onAuthenticated: (user: AuthUser) => void;
}

/**
 * Email register / login gate before the planning workspace.
 */
export function AuthGate({ onAuthenticated }: AuthGateProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const session =
        mode === "register"
          ? await registerAccount({
              email: email.trim(),
              full_name: fullName.trim() || email.trim().split("@")[0],
              password,
            })
          : await loginAccount({ email: email.trim(), password });
      onAuthenticated(session.user);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="auth-gate">
      <div className="auth-card">
        <p className="auth-kicker">GreenCity</p>
        <h1 className="auth-brand">Sign in</h1>
        <p className="auth-lede">Work on city and neighborhood green-space studies.</p>

        <div className="auth-mode-links">
          <button
            type="button"
            className={mode === "login" ? "auth-link auth-link--active" : "auth-link"}
            onClick={() => setMode("login")}
          >
            Log in
          </button>
          <span aria-hidden="true">·</span>
          <button
            type="button"
            className={mode === "register" ? "auth-link auth-link--active" : "auth-link"}
            onClick={() => setMode("register")}
          >
            Create account
          </button>
        </div>

        <form className="auth-form" onSubmit={(event) => void submit(event)}>
          {mode === "register" && (
            <label className="field">
              <span>Full name</span>
              <input
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                autoComplete="name"
              />
            </label>
          )}
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === "register" ? "new-password" : "current-password"}
            />
          </label>
          {error && <p className="auth-error">{error}</p>}
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Working…" : mode === "register" ? "Create account" : "Log in"}
          </button>
        </form>
      </div>
    </section>
  );
}
