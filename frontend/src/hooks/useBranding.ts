import { useEffect } from "react";

import { api } from "../api/client";

import { ALCURRO } from "../lib/brand";



export interface Branding {

  slug: string;

  name: string;

  logo_url: string | null;

  primary_color: string;

  secondary_color: string;

  accent_color: string;

}



const STORAGE_KEY = "hrm_tenant_slug";



export function getStoredTenantSlug(): string {

  return localStorage.getItem(STORAGE_KEY) || "demo";

}



export function setStoredTenantSlug(slug: string) {

  localStorage.setItem(STORAGE_KEY, slug.toLowerCase());

}



/** Aplica variables CSS; mantiene identidad alcurro si el tenant no personaliza. */

export function applyBranding(b?: Partial<Branding> | null) {

  const root = document.documentElement;

  root.style.setProperty("--primary-custom", b?.primary_color ?? ALCURRO.green);

  root.style.setProperty("--sidebar-custom", b?.secondary_color ?? ALCURRO.sidebarBg);

  root.style.setProperty("--accent", b?.accent_color ?? ALCURRO.green);

  document.title = b?.name ? `${b.name} — alcurro` : "alcurro — Administración";

}



export function applyAlcurroDefaults() {

  applyBranding(null);

}



export function useBranding(tenantSlug: string) {

  useEffect(() => {

    applyAlcurroDefaults();

    if (!tenantSlug) return;

    api

      .get<Branding>(`/tenants/public/${tenantSlug}/branding`)

      .then(applyBranding)

      .catch(() => applyAlcurroDefaults());

  }, [tenantSlug]);

}


