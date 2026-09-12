"""Helpers for finding sibling entities from the official `axis` integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


async def async_find_mirrored_pir_entity_id(hass: HomeAssistant, mac_address: str) -> str | None:
    """Find a motion/PIR binary_sensor belonging to a device with this MAC.

    This device's PIR is exposed over ONVIF events, which the official
    `axis` integration (if configured) already subscribes to. Rather than
    re-implementing ONVIF event subscriptions here, we mirror the state of
    that existing entity so PIR shows up under this integration's device
    too.
    """
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    # async_get_device_by_connection() requires scoping to one config_entry_id
    # on this HA version (a MAC is no longer globally unique across entries),
    # but we deliberately don't know which entry owns the sibling `axis`
    # integration's device - so scan all devices for a matching connection
    # instead, same as async_get_devices() the deprecation notice suggested.
    target = (dr.CONNECTION_NETWORK_MAC, dr.format_mac(mac_address))
    device = next(
        (d for d in dev_reg.devices if target in d.connections),
        None,
    )
    if device is None:
        return None

    for entity in er.async_entries_for_device(ent_reg, device.id, include_disabled_entities=False):
        if entity.domain != "binary_sensor":
            continue
        if entity.original_device_class == "motion" or "pir" in entity.entity_id.lower():
            return entity.entity_id
    return None
