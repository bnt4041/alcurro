import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, getToken, setToken } from "../api/client";
import type { Role, UserScope } from "../api/types";
import { setStoredTenantSlug } from "../hooks/useBranding";

export interface AuthUser {
  id: string;
  full_name: string;
  employee_code: string;
  email: string | null;
  role: Role;
  user_type: Role;
  scope: UserScope;
  permissions: string[];
  group_ids: string[];
  tenant_id: string;
  tenant_slug: string;
  tenant_name: string;
  company_id: string;
  company_name: string;
  work_center_id: string | null;
  work_center_name: string | null;
  department_id: string | null;
  department_name: string | null;
}

export interface PlatformUser {
  id: string;
  email: string;
  full_name: string;
  scope: "platform";
}

interface AuthContextValue {
  user: AuthUser | null;
  platformUser: PlatformUser | null;
  loading: boolean;
  login: (
    tenantSlug: string,
    username: string,
    password: string
  ) => Promise<AuthUser>;
  loginPlatform: (email: string, password: string) => Promise<void>;
  loginUnified: (
    login: string,
    password: string
  ) => Promise<{ scope: "platform" | "tenant"; user?: AuthUser }>;
  logout: () => void;
  refresh: () => Promise<void>;
  setActiveCompany: (companyId: string) => void;
  setActiveWorkCenter: (workCenterId: string | null) => void;
  setActiveDepartment: (departmentId: string | null) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const COMPANY_KEY = "hrm_company_id";
const WORK_CENTER_KEY = "hrm_work_center_id";
const DEPARTMENT_KEY = "hrm_department_id";
const SCOPE_KEY = "hrm_scope";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [platformUser, setPlatformUser] = useState<PlatformUser | null>(null);
  const [loading, setLoading] = useState(!!getToken());

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setPlatformUser(null);
      setLoading(false);
      return;
    }
    const scope = localStorage.getItem(SCOPE_KEY) ?? "platform";
    try {
      if (scope === "platform") {
        const me = await fetch("/api/platform/auth/me", {
          headers: { Authorization: `Bearer ${getToken()}` },
        });
        if (!me.ok) throw new Error("me failed");
        setPlatformUser(await me.json());
        setUser(null);
      } else {
        const headers: Record<string, string> = {
          Authorization: `Bearer ${getToken()}`,
        };
        const companyId = localStorage.getItem(COMPANY_KEY);
        const wcId = localStorage.getItem(WORK_CENTER_KEY);
        const deptId = localStorage.getItem(DEPARTMENT_KEY);
        if (companyId) headers["X-Company-Id"] = companyId;
        if (wcId) headers["X-Work-Center-Id"] = wcId;
        if (deptId) headers["X-Department-Id"] = deptId;
        const me = await fetch("/api/auth/me", { headers });
        if (!me.ok) throw new Error("me failed");
        const data: AuthUser = await me.json();
        setUser(data);
        setPlatformUser(null);
        if (!localStorage.getItem(COMPANY_KEY)) {
          localStorage.setItem(COMPANY_KEY, data.company_id);
        }
        setStoredTenantSlug(data.tenant_slug);
      }
    } catch {
      setToken(null);
      setUser(null);
      setPlatformUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = async (
    tenantSlug: string,
    username: string,
    password: string
  ): Promise<AuthUser> => {
    const res = await api.post<{ access_token: string }>("/auth/login", {
      tenant_slug: tenantSlug,
      username,
      password,
    });
    setToken(res.access_token);
    localStorage.setItem(SCOPE_KEY, "tenant");
    setStoredTenantSlug(tenantSlug);
    localStorage.removeItem(WORK_CENTER_KEY);
    localStorage.removeItem(DEPARTMENT_KEY);
    const headers: Record<string, string> = {
      Authorization: `Bearer ${res.access_token}`,
    };
    const me = await fetch("/api/auth/me", { headers });
    if (!me.ok) throw new Error("No se pudo cargar la sesión");
    const data: AuthUser = await me.json().catch(() => { throw new Error("El servidor no responde correctamente"); });
    setUser(data);
    setPlatformUser(null);
    localStorage.setItem(COMPANY_KEY, data.company_id);
    setLoading(false);
    return data;
  };

  const loginUnified = async (
    login: string,
    password: string
  ): Promise<{ scope: "platform" | "tenant"; user?: AuthUser }> => {
    const res = await api.post<{
      access_token: string;
      scope: string;
      tenant_slug?: string;
    }>("/auth/login-unified", { login, password });

    setToken(res.access_token);

    if (res.scope === "platform") {
      localStorage.setItem(SCOPE_KEY, "platform");
      localStorage.removeItem(COMPANY_KEY);
      localStorage.removeItem(WORK_CENTER_KEY);
      localStorage.removeItem(DEPARTMENT_KEY);
      const me = await fetch("/api/platform/auth/me", {
        headers: { Authorization: `Bearer ${res.access_token}` },
      });
      if (!me.ok) throw new Error("No se pudo cargar la sesión");
      const platform = await me.json().catch(() => { throw new Error("El servidor no responde correctamente"); });
      setPlatformUser(platform);
      setUser(null);
      setLoading(false);
      return { scope: "platform" };
    }

    localStorage.setItem(SCOPE_KEY, "tenant");
    if (res.tenant_slug) setStoredTenantSlug(res.tenant_slug);
    localStorage.removeItem(WORK_CENTER_KEY);
    localStorage.removeItem(DEPARTMENT_KEY);

    const headers: Record<string, string> = {
      Authorization: `Bearer ${res.access_token}`,
    };
    const me = await fetch("/api/auth/me", { headers });
    if (!me.ok) throw new Error("No se pudo cargar la sesión");
    const data: AuthUser = await me.json().catch(() => { throw new Error("El servidor no responde correctamente"); });
    setUser(data);
    setPlatformUser(null);
    localStorage.setItem(COMPANY_KEY, data.company_id);
    setLoading(false);
    return { scope: "tenant", user: data };
  };

  const loginPlatform = async (email: string, password: string) => {
    const res = await api.post<{ access_token: string }>("/platform/auth/login", {
      email,
      password,
    });
    setToken(res.access_token);
    localStorage.setItem(SCOPE_KEY, "platform");
    localStorage.removeItem(COMPANY_KEY);
    localStorage.removeItem(WORK_CENTER_KEY);
    localStorage.removeItem(DEPARTMENT_KEY);
    setLoading(true);
    await refresh();
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setPlatformUser(null);
    localStorage.removeItem(COMPANY_KEY);
    localStorage.removeItem(WORK_CENTER_KEY);
    localStorage.removeItem(DEPARTMENT_KEY);
    localStorage.removeItem(SCOPE_KEY);
  };

  const setActiveCompany = (companyId: string) => {
    localStorage.setItem(COMPANY_KEY, companyId);
    localStorage.removeItem(WORK_CENTER_KEY);
    localStorage.removeItem(DEPARTMENT_KEY);
    refresh();
  };

  const setActiveWorkCenter = (workCenterId: string | null) => {
    if (workCenterId) localStorage.setItem(WORK_CENTER_KEY, workCenterId);
    else localStorage.removeItem(WORK_CENTER_KEY);
    localStorage.removeItem(DEPARTMENT_KEY);
    refresh();
  };

  const setActiveDepartment = (departmentId: string | null) => {
    if (departmentId) localStorage.setItem(DEPARTMENT_KEY, departmentId);
    else localStorage.removeItem(DEPARTMENT_KEY);
    refresh();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        platformUser,
        loading,
        login,
        loginPlatform,
        loginUnified,
        logout,
        refresh,
        setActiveCompany,
        setActiveWorkCenter,
        setActiveDepartment,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fuera de AuthProvider");
  return ctx;
}
