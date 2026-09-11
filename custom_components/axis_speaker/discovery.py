"""Active network scan for Axis devices, used by the config flow's manual step.

Reuses Home Assistant's own zeroconf instance (already running for other
integrations) rather than opening a second multicast socket. The service
types were confirmed by hand against a real AXIS C1410 Network Mini
Speaker: it advertises both `_axis-video._tcp.local.` (generic Axis
network device) and `_axis-audiosite._tcp.local.` (Axis audio devices
specifically, TXT record includes the product name directly).

Best-effort only: any failure here should never block manually entering a
host, so callers should treat an empty result the same as "scan failed".
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components import zeroconf as ha_zeroconf
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

AXIS_SERVICE_TYPES = ["_axis-video._tcp.local.", "_axis-audiosite._tcp.local."]
SCAN_TIMEOUT_SECONDS = 3.0


async def async_discover_axis_hosts(hass: HomeAssistant) -> dict[str, str]:
    """Return {host: friendly_name} for Axis devices seen on the network."""
    try:
        from zeroconf import ServiceStateChange
        from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo
    except ImportError:
        _LOGGER.debug("zeroconf library not available, skipping active scan")
        return {}

    discovered: dict[str, str] = {}

    try:
        aiozc = await ha_zeroconf.async_get_async_instance(hass)
    except Exception:  # noqa: BLE001 - discovery is always best-effort
        _LOGGER.debug("Could not get Home Assistant's zeroconf instance", exc_info=True)
        return {}

    async def _resolve(service_type: str, name: str) -> None:
        try:
            info = AsyncServiceInfo(service_type, name)
            if await info.async_request(aiozc.zeroconf, 3000):
                addresses = info.parsed_addresses()
                if addresses:
                    friendly_name = name.split(f".{service_type}")[0]
                    discovered[addresses[0]] = friendly_name
        except Exception:  # noqa: BLE001 - one bad record shouldn't kill the scan
            _LOGGER.debug("Failed resolving %s", name, exc_info=True)

    def _on_change(zeroconf, service_type, name, state_change) -> None:
        if state_change is ServiceStateChange.Added:
            hass.async_create_task(_resolve(service_type, name))

    browser = None
    try:
        browser = AsyncServiceBrowser(aiozc.zeroconf, AXIS_SERVICE_TYPES, handlers=[_on_change])
        await asyncio.sleep(SCAN_TIMEOUT_SECONDS)
    except Exception:  # noqa: BLE001 - discovery is always best-effort
        _LOGGER.debug("Active Axis network scan failed", exc_info=True)
    finally:
        if browser is not None:
            await browser.async_cancel()

    return discovered
