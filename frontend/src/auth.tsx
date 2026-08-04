import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getTokens, setTokens } from "./api";

interface User {
  user_id: string;
  email: string;
  is_active: boolean;
}
interface AuthCtx {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

// Safe default so a consumer never crashes if rendered before the provider
// (e.g. during a hot-module reload).
const Ctx = createContext<AuthCtx>({
  user: null,
  ready: false,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      if (getTokens()) {
        try {
          setUser(await api.me());
        } catch {
          setTokens(null);
        }
      }
      setReady(true);
    })();
  }, []);

  async function login(email: string, password: string) {
    setTokens(await api.login(email, password));
    setUser(await api.me());
  }
  async function register(email: string, password: string) {
    setTokens(await api.register(email, password));
    setUser(await api.me());
  }
  function logout() {
    setTokens(null);
    setUser(null);
  }

  return <Ctx.Provider value={{ user, ready, login, register, logout }}>{children}</Ctx.Provider>;
}
