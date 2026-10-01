from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory

from .entity import VevorEntity


async def async_setup_entry(hass, entry, add):
    c = entry.runtime_data
    add([SyncTime(c, "sync_time", "Sync clock"), ResetFuel(c, "reset_fuel", "Reset fuel (refilled)")])


class SyncTime(VevorEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-check"

    async def async_press(self):
        await self.coordinator.sync_time()


class ResetFuel(VevorEntity, ButtonEntity):
    _attr_icon = "mdi:gas-station-outline"

    @property
    def available(self):
        return True

    async def async_press(self):
        self.coordinator.reset_fuel()
