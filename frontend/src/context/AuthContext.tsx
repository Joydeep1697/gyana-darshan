import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../utils/api";

type User = { email: string; tenant_id: string; role: string };
type AuthContextValue = {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!window.localStorage.getItem("nyaya_token")) return;
    apiFetch<User>("/api/auth/me").then(setUser).catch(() => window.localStorage.removeItem("nyaya_token"));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      async login(email: string, password: string) {
        const payload = await apiFetch<{ access_token: string; user: User }>("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
          allowAnonymous: true,
        });
        window.localStorage.setItem("nyaya_token", payload.access_token);
        setUser(payload.user);
      },
      logout() {
        window.localStorage.removeItem("nyaya_token");
        setUser(null);
        window.location.href = "/login";
      },
    }),
    [user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
