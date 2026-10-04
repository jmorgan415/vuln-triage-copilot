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
    # SafeLoader resolves the console's `!!merge <<:` keys natively (TKT-1421);
    # FullLoader was never needed and permits python/* constructor tags.
    return yaml.safe_load(raw.decode("utf-8"))
