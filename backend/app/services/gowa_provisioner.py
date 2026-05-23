"""Provisiona un contenedor goWA dedicado por tenant en la red Docker."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import docker
from docker.errors import APIError, ImageNotFound, NotFound
from sqlmodel import Session, select

from app.config import get_settings
from app.models.tenant import GoWAStatus, Tenant

GOWA_IMAGE = "ghcr.io/aldinokemal/go-whatsapp-web-multidevice:latest"
BASE_HOST_PORT = 3010


def _docker_client() -> docker.DockerClient:
    return docker.from_env()


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


def _ensure_network(client: docker.DockerClient, network_name: str) -> None:
    try:
        client.networks.get(network_name)
    except NotFound:
        client.networks.create(network_name, driver="bridge")


def provision_gowa(session: Session, tenant_id: UUID) -> Tenant:
    settings = get_settings()
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Tenant no encontrado")

    if tenant.gowa_status == GoWAStatus.RUNNING and tenant.gowa_container_name:
        return tenant

    slug = tenant.slug.replace("_", "-").lower()
    container_name = f"hrm-gowa-{slug}"
    host = container_name
    port = tenant.gowa_port or _next_free_port(session)
    webhook = f"http://backend:8000/webhook/whatsapp/{tenant.slug}"
    volume_name = f"hrm_gowa_{slug}"

    tenant.gowa_status = GoWAStatus.PROVISIONING
    tenant.gowa_error = None
    session.add(tenant)
    session.commit()

    try:
        client = _docker_client()
        _ensure_network(client, settings.docker_network)

        try:
            old = client.containers.get(container_name)
            old.remove(force=True)
        except NotFound:
            pass

        try:
            client.images.get(GOWA_IMAGE)
        except ImageNotFound:
            client.images.pull(GOWA_IMAGE)

        cont = client.containers.run(
            GOWA_IMAGE,
            command=["rest", "--port=3000"],
            name=container_name,
            detach=True,
            network=settings.docker_network,
            ports={"3000/tcp": port},
            volumes={volume_name: {"bind": "/app/storages", "mode": "rw"}},
            environment={
                "WHATSAPP_WEBHOOK": webhook,
                "WHATSAPP_WEBHOOK_EVENTS": "message",
                "APP_PORT": "3000",
                "APP_BASIC_AUTH": tenant.gowa_basic_auth,
                "APP_OS": "Chrome",
                "APP_ACCOUNT_VALIDATION": "false",
            },
            restart_policy={"Name": "unless-stopped"},
        )

        tenant.gowa_container_name = (cont.short_id or cont.id or container_name)[:12]
        tenant.gowa_host = host
        tenant.gowa_port = port
        tenant.gowa_send_url = f"http://{host}:3000/send/message"
        tenant.gowa_ui_url = f"http://localhost:{port}"
        tenant.gowa_webhook_path = f"/webhook/whatsapp/{tenant.slug}"
        tenant.gowa_status = GoWAStatus.RUNNING
    except FileNotFoundError:
        tenant.gowa_status = GoWAStatus.ERROR
        tenant.gowa_error = (
            "No se encuentra el socket de Docker. Monta /var/run/docker.sock en el backend."
        )
    except APIError as exc:
        tenant.gowa_status = GoWAStatus.ERROR
        tenant.gowa_error = str(exc.explanation or exc)[:500]
    except Exception as exc:
        tenant.gowa_status = GoWAStatus.ERROR
        tenant.gowa_error = str(exc)[:500]

    tenant.updated_at = datetime.utcnow()
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def stop_gowa(session: Session, tenant_id: UUID) -> Tenant:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Tenant no encontrado")

    slug = tenant.slug.replace("_", "-").lower()
    container_name = tenant.gowa_host or f"hrm-gowa-{slug}"

    try:
        client = _docker_client()
        try:
            cont = client.containers.get(container_name)
            cont.stop(timeout=15)
        except NotFound:
            pass
        tenant.gowa_status = GoWAStatus.STOPPED
    except Exception as exc:
        tenant.gowa_error = str(exc)[:500]

    tenant.updated_at = datetime.utcnow()
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant
