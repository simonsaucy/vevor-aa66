from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory

from .entity import VevorEntity


async def async_setup_entry(hass, entry, add):
    add([SyncTime(entry.runtime_data, "sync_time", "Sync clock")])


class SyncTime(VevorEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-check"

    async def async_press(self):
        await self.coordinator.sync_time()
