"""The Axis Speaker integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.httpx_client import get_async_client

from .api import AxisSpeakerClient, AxisSpeakerError
from .const import (
    ATTR_HOST,
    ATTR_PASSWORD,
    ATTR_PORT,
    ATTR_USE_TLS,
    ATTR_USERNAME,
    CONF_VERIFY_SSL,
    DOMAIN,
    SERVICE_CONFIGURE_MQTT,
)
from .coordinator import AxisSpeakerCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
]

CONFIGURE_MQTT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_HOST): cv.string,
        vol.Required(ATTR_PORT): cv.port,
        vol.Optional(ATTR_USERNAME): cv.string,
        vol.Optional(ATTR_PASSWORD): cv.string,
        vol.Optional(ATTR_USE_TLS, default=False): cv.boolean,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Axis Speaker from a config entry."""
    client = AxisSpeakerClient(
        get_async_client(hass, verify_ssl=entry.data[CONF_VERIFY_SSL]),
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    coordinator = AxisSpeakerCoordinator(hass, client)
    coordinator.device_identifier = entry.unique_id or entry.data[CONF_HOST]
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_configure_mqtt(call: ServiceCall) -> None:
        for coord in hass.data[DOMAIN].values():
            try:
                await coord.client.async_configure_mqtt(
                    host=call.data[ATTR_HOST],
                    port=call.data[ATTR_PORT],
                    username=call.data.get(ATTR_USERNAME),
                    password=call.data.get(ATTR_PASSWORD),
                    use_tls=call.data[ATTR_USE_TLS],
                )
            except AxisSpeakerError as err:
                raise HomeAssistantError(f"Could not configure MQTT client: {err}") from err
            await coord.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_CONFIGURE_MQTT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CONFIGURE_MQTT,
            _async_configure_mqtt,
            schema=CONFIGURE_MQTT_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_CONFIGURE_MQTT)
    return unload_ok
