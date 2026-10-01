from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .const import MODES
from .entity import VevorEntity


async def async_setup_entry(hass, entry, add):
    add([RunningMode(entry.runtime_data, "running_mode", "Running mode")])


class RunningMode(VevorEntity, SelectEntity):
    _attr_options = list(MODES)
    _attr_icon = "mdi:cog"

    @property
    def current_option(self):
        m = self.d.get("running_mode")
        return next((k for k, v in MODES.items() if v == m), None)

    async def async_select_option(self, option):
        await self.coordinator.set_mode(MODES[option])
