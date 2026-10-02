"""Tenant configuration loader for the platform worker.

Workspace admins upload YAML config bundles through the internal admin
console whenever a tenant changes integration settings; the worker
parses them as part of the tenant_config job.
"""
import yaml

MAX_CONFIG_BYTES = 256 * 1024


def load_tenant_config(raw: bytes) -> dict:
    """Parse a YAML config bundle uploaded via the admin console."""
    if len(raw) > MAX_CONFIG_BYTES:
        raise ValueError("config bundle exceeds 256 KiB limit")
    # FullLoader keeps support for the custom !!merge tags the console emits
    # (safe_load rejects them). Added 2021-06, see TKT-1421.
    return yaml.load(raw.decode("utf-8"), Loader=yaml.FullLoader)
