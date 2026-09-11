"""Volume number entity for the Axis Speaker integration.

The speaker has no persistent device-side volume setting - volume is a
parameter passed along with every playclip call. This entity just holds the
value that clip buttons should use for their next play, mirroring how the
previous YAML-based setup used an input_number for the same purpose.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_VOLUME, DOMAIN
from .coordinator import AxisSpeakerCoordinator
from .entity import AxisSpeakerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AxisSpeakerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AxisSpeakerVolumeNumber(coordinator)])


class AxisSpeakerVolumeNumber(AxisSpeakerEntity, NumberEntity):
    """Volume used for the next clip playback."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:volume-high"

    def __init__(self, coordinator: AxisSpeakerCoordinator) -> None:
        super().__init__(coordinator, f"{coordinator.device_identifier}_volume")
        self._attr_name = "Volume"
        coordinator.volume = DEFAULT_VOLUME

    @property
    def native_value(self) -> float:
        return self.coordinator.volume

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.volume = int(value)
        self.async_write_ha_state()
