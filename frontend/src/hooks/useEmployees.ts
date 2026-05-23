import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Employee } from "../api/types";

export function useEmployees() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setEmployees(await api.get<Employee[]>("/employees"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const byId = (id: string) =>
    employees.find((e) => e.id === id)?.full_name ?? id.slice(0, 8);

  return { employees, loading, reload, byId };
}
