"""Shared base entity for Axis Speaker entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AxisSpeakerCoordinator


class AxisSpeakerEntity(CoordinatorEntity[AxisSpeakerCoordinator]):
    """Base entity tying every platform to the same device registry entry."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AxisSpeakerCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        device_info = coordinator.data.device_info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_identifier)},
            manufacturer=MANUFACTURER,
            model=device_info.prod_short_name,
            name=device_info.prod_full_name,
            sw_version=device_info.firmware_version,
        )
