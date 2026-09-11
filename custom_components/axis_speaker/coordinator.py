"""Data update coordinator for the Axis Speaker integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AxisSpeakerClient, AxisSpeakerData, AxisSpeakerError
from .const import UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class AxisSpeakerCoordinator(DataUpdateCoordinator[AxisSpeakerData]):
    """Polls brand/firmware, configured clips and MQTT client status."""

    def __init__(self, hass: HomeAssistant, client: AxisSpeakerClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Axis Speaker",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.client = client
        self.volume: int = 100
        self.device_identifier: str = ""

    async def _async_update_data(self) -> AxisSpeakerData:
        try:
            return await self.client.async_get_data()
        except AxisSpeakerError as err:
            raise UpdateFailed(f"Error talking to Axis speaker: {err}") from err
