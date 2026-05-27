import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

/** Sidebar drawer en viewport estrecho; se cierra al cambiar de ruta. */
export function useResponsiveSidebar() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.classList.toggle("sidebar-scroll-lock", open);
    return () => document.body.classList.remove("sidebar-scroll-lock");
  }, [open]);

  return {
    open,
    toggle: () => setOpen((v) => !v),
    close: () => setOpen(false),
  };
}
