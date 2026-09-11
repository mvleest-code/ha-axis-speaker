"""PIR motion binary sensor for the Axis Speaker integration.

The speaker has a built-in PIR (`Properties.Sensor.PIR=yes`), but it is only
exposed over ONVIF events - there is no simple VAPIX polling endpoint for it
(verified: `Input.NbrOfInputs=0`, no working websocket/eventstream CGI found
under `axis-cgi/` or `vapix/`). The official `axis` integration already
subscribes to ONVIF events, so instead of re-implementing that here, this
entity mirrors the state of the sibling PIR binary_sensor it creates - so
PIR shows up under this integration's device too, without needing the
official integration's own device page.

If the official `axis` integration isn't set up for this device, no PIR
entity is created here - there is nothing to mirror.
"""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .coordinator import AxisSpeakerCoordinator
from .entity import AxisSpeakerEntity
from .helpers import async_find_mirrored_pir_entity_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AxisSpeakerCoordinator = hass.data[DOMAIN][entry.entry_id]
    mac_address = coordinator.data.device_info.mac_address
    if not mac_address:
        return

    source_entity_id = await async_find_mirrored_pir_entity_id(hass, mac_address)
    if source_entity_id is None:
        _LOGGER.debug(
            "No PIR binary_sensor found for %s (official 'axis' integration not "
            "set up for this device?) - skipping PIR mirror entity",
            mac_address,
        )
        return

    async_add_entities([AxisSpeakerPirSensor(coordinator, source_entity_id)])


class AxisSpeakerPirSensor(AxisSpeakerEntity, BinarySensorEntity):
    """Mirrors the PIR binary_sensor maintained by the official axis integration."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(self, coordinator: AxisSpeakerCoordinator, source_entity_id: str) -> None:
        super().__init__(coordinator, f"{coordinator.device_identifier}_pir")
        self._attr_name = "PIR motion"
        self._source_entity_id = source_entity_id
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source_entity_id], self._handle_source_event
            )
        )
        source_state = self.hass.states.get(self._source_entity_id)
        self._attr_is_on = source_state is not None and source_state.state == "on"

    @callback
    def _handle_source_event(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        self._attr_is_on = new_state is not None and new_state.state == "on"
        self.async_write_ha_state()
