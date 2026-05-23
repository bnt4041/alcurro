import { ALCURRO, LOGO_DARK, LOGO_LIGHT } from "../lib/brand";

type Variant = "light" | "dark";

interface BrandLogoProps {
  /** light = fondo claro (logo color); dark = sidebar/fondo oscuro (logo blanco) */
  variant?: Variant;
  /** Solo isotipo más pequeño en sidebar */
  compact?: boolean;
  /** Subtítulo bajo el logo (login) */
  showTagline?: boolean;
  /** Nombre de cuenta en sidebar (sustituye tagline) */
  subtitle?: string;
  className?: string;
}

export default function BrandLogo({
  variant = "light",
  compact = false,
  showTagline = false,
  subtitle,
  className = "",
}: BrandLogoProps) {
  const src = variant === "dark" ? LOGO_DARK : LOGO_LIGHT;

  return (
    <div className={`brand-logo ${compact ? "brand-logo--compact" : ""} ${className}`.trim()}>
      <img src={src} alt={ALCURRO.name} className="brand-logo__img" />
      {(showTagline || subtitle) && !compact && (
        <p className="brand-logo__tagline">
          {subtitle ? (
            <>
              <span className="brand-logo__account">{subtitle}</span>
            </>
          ) : (
            <>
              HRM que se gestiona por{" "}
              <span className="brand-logo__wa">WhatsApp</span>
            </>
          )}
        </p>
      )}
    </div>
  );
}
