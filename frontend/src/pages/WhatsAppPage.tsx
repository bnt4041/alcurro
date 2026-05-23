import PageHeader from "../components/PageHeader";
import WhatsAppPanel from "../components/WhatsAppPanel";
import { useAuth } from "../context/AuthContext";
import { canModule } from "../lib/permissions";

export default function WhatsAppPage() {
  const { user } = useAuth();
  const allowed = user && canModule(user.permissions, "read", "tenant");

  if (!allowed) {
    return <p className="muted">No tienes acceso a esta sección.</p>;
  }

  return (
    <>
      <PageHeader
        title="WhatsApp"
        subtitle="Estado de la línea compartida de alcurro (gestionada por la plataforma)"
      />
      <section className="card">
        <WhatsAppPanel />
      </section>
    </>
  );
}
