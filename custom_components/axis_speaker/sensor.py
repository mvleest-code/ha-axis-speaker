"""Sensor entities for the Axis Speaker integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AxisSpeakerCoordinator
from .entity import AxisSpeakerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AxisSpeakerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AxisSpeakerFirmwareSensor(coordinator),
            AxisSpeakerMqttStatusSensor(coordinator),
        ]
    )


class AxisSpeakerFirmwareSensor(AxisSpeakerEntity, SensorEntity):
    """Firmware version currently running on the speaker."""

    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AxisSpeakerCoordinator) -> None:
        super().__init__(coordinator, f"{coordinator.device_identifier}_firmware")
        self._attr_name = "Firmware version"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.device_info.firmware_version


class AxisSpeakerMqttStatusSensor(AxisSpeakerEntity, SensorEntity):
    """Connection status of the speaker's built-in MQTT client.

    Lets you see, from Home Assistant, whether the speaker is actually
    connected to a broker after using the `axis_speaker.configure_mqtt`
    service - previously there was no visibility into this at all.
    """

    _attr_icon = "mdi:transit-connection-variant"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AxisSpeakerCoordinator) -> None:
        super().__init__(coordinator, f"{coordinator.device_identifier}_mqtt_status")
        self._attr_name = "MQTT client status"

    @property
    def native_value(self) -> str:
        status = self.coordinator.data.mqtt_status
        if not status:
            return "unknown"
        return (
            status.get("data", {})
            .get("status", {})
            .get("connectionStatus", "unknown")
        )
