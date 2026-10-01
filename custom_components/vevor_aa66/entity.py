from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VevorCoordinator


class VevorEntity(CoordinatorEntity[VevorCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coord: VevorCoordinator, key: str, name: str) -> None:
        super().__init__(coord)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{coord.address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coord.address)},
            connections={(CONNECTION_BLUETOOTH, coord.address)},
            name="Vevor Heater", manufacturer="Vevor", model="AA66 encrypted",
        )

    @property
    def d(self) -> dict:
        return self.coordinator.data or {}
