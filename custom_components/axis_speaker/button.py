"""Button entities for the Axis Speaker integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AxisSpeakerError
from .const import DOMAIN
from .coordinator import AxisSpeakerCoordinator
from .entity import AxisSpeakerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up one button per clip configured on the speaker, plus Stop."""
    coordinator: AxisSpeakerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ButtonEntity] = [AxisSpeakerStopButton(coordinator)]
    entities.extend(
        AxisSpeakerClipButton(coordinator, clip.clip_id, clip.name)
        for clip in coordinator.data.clips.values()
    )
    async_add_entities(entities)


class AxisSpeakerClipButton(AxisSpeakerEntity, ButtonEntity):
    """Plays a single clip that is configured on the speaker itself."""

    def __init__(self, coordinator: AxisSpeakerCoordinator, clip_id: int, name: str) -> None:
        super().__init__(coordinator, f"{coordinator.device_identifier}_clip_{clip_id}")
        self._clip_id = clip_id
        self._attr_name = f"Play {name}"
        self._attr_icon = "mdi:play-circle"

    async def async_press(self) -> None:
        try:
            await self.coordinator.client.async_play_clip(
                self._clip_id, volume=self.coordinator.volume
            )
        except AxisSpeakerError as err:
            raise HomeAssistantError(f"Could not play clip: {err}") from err


class AxisSpeakerStopButton(AxisSpeakerEntity, ButtonEntity):
    """Stops whatever clip is currently playing."""

    def __init__(self, coordinator: AxisSpeakerCoordinator) -> None:
        super().__init__(coordinator, f"{coordinator.device_identifier}_stop")
        self._attr_name = "Stop"
        self._attr_icon = "mdi:stop-circle"

    async def async_press(self) -> None:
        try:
            await self.coordinator.client.async_stop_clip()
        except AxisSpeakerError as err:
            raise HomeAssistantError(f"Could not stop clip: {err}") from err
