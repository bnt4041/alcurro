"""Provisiona un contenedor goWA dedicado por tenant en la red Docker."""

import subprocess
from uuid import UUID

from sqlmodel import Session, select

from app.config import get_settings
from app.models.tenant import GoWAStatus, Tenant

GOWA_IMAGE = "ghcr.io/aldinokemal/go-whatsapp-web-multidevice:latest"
BASE_HOST_PORT = 3010


def _next_free_port(session: Session) -> int:
    used = {
        t.gowa_port
        for t in session.exec(select(Tenant)).all()
        if t.gowa_port
    }
    port = BASE_HOST_PORT
    while port in used:
        port += 1
    return port


def provision_gowa(session: Session, tenant_id: UUID) -> Tenant:
    settings = get_settings()
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Tenant no encontrado")

    if tenant.gowa_status == GoWAStatus.RUNNING and tenant.gowa_container_name:
        return tenant

    slug = tenant.slug.replace("_", "-").lower()
    container = f"hrm-gowa-{slug}"
    host = container
    port = tenant.gowa_port or _next_free_port(session)
    webhook = f"http://backend:8000/webhook/whatsapp/{tenant.slug}"
    volume = f"hrm_gowa_{slug}"

    tenant.gowa_status = GoWAStatus.PROVISIONING
    tenant.gowa_error = None
    session.add(tenant)
    session.commit()

    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container,
        "--network",
        settings.docker_network,
        "-p",
        f"{port}:3000",
        "-v",
        f"{volume}:/app/storages",
        "-e",
        f"WHATSAPP_WEBHOOK={webhook}",
        "-e",
        "WHATSAPP_WEBHOOK_EVENTS=message",
        "-e",
        "APP_PORT=3000",
        "-e",
        f"APP_BASIC_AUTH={tenant.gowa_basic_auth}",
        "-e",
        "APP_OS=Chrome",
        "-e",
        "APP_ACCOUNT_VALIDATION=false",
        "--restart",
        "unless-stopped",
        GOWA_IMAGE,
        "rest",
        "--port=3000",
    ]

    try:
        subprocess.run(
            ["docker", "rm", "-f", container],
            capture_output=True,
            check=False,
        )
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()[:12]

        tenant.gowa_container_name = container_id or container
        tenant.gowa_host = host
        tenant.gowa_port = port
        tenant.gowa_send_url = f"http://{host}:3000/send/message"
        tenant.gowa_ui_url = f"http://localhost:{port}"
        tenant.gowa_webhook_path = f"/webhook/whatsapp/{tenant.slug}"
        tenant.gowa_status = GoWAStatus.RUNNING
    except subprocess.CalledProcessError as exc:
        tenant.gowa_status = GoWAStatus.ERROR
        tenant.gowa_error = (exc.stderr or exc.stdout or str(exc))[:500]
    except FileNotFoundError:
        tenant.gowa_status = GoWAStatus.ERROR
        tenant.gowa_error = "Docker CLI no disponible en el backend"

    tenant.updated_at = __import__("datetime").datetime.utcnow()
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def stop_gowa(session: Session, tenant_id: UUID) -> Tenant:
    tenant = session.get(Tenant, tenant_id)
    if not tenant or not tenant.gowa_container_name:
        return tenant  # type: ignore[return-value]
    name = tenant.gowa_host or f"hrm-gowa-{tenant.slug}"
    subprocess.run(["docker", "stop", name], capture_output=True, check=False)
    tenant.gowa_status = GoWAStatus.STOPPED
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant
