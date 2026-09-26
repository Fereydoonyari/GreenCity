import { useEffect, useState } from "react";
import { fetchCurrentUser, logoutAccount, type AuthUser } from "./api/auth";
import { getAccessToken } from "./api/http";
import { AuthGate } from "./components/AuthGate";
import { AoiWorkspace } from "./components/AoiWorkspace";

/**
 * Auth gate, then full-viewport planning workspace (no app chrome).
 */
export function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const token = getAccessToken();
    if (!token) {
      setAuthChecked(true);
      return;
    }
    fetchCurrentUser()
      .then((me) => {
        if (!cancelled) {
          setUser(me);
        }
      })
      .catch(() => {
        if (!cancelled) {
          logoutAccount();
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAuthChecked(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!authChecked) {
    return (
      <div className="shell">
        <p className="auth-loading">Loading…</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="shell">
        <AuthGate onAuthenticated={setUser} />
      </div>
    );
  }

  return (
    <div className="shell shell--app">
      <main className="app-main">
        <AoiWorkspace
          accountLabel={user.full_name || user.email}
          onLogout={() => {
            logoutAccount();
            setUser(null);
          }}
        />
      </main>
    </div>
  );
}
