from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .entity import VevorEntity


async def async_setup_entry(hass, entry, add):
    c = entry.runtime_data
    add([PowerSwitch(c, "power", "Power"), AutoStartStop(c, "auto_start_stop", "Auto start/stop")])


class PowerSwitch(VevorEntity, SwitchEntity):
    _attr_icon = "mdi:power"

    @property
    def is_on(self):
        return self.d.get("running_state") == 1

    async def async_turn_on(self, **kw):
        await self.coordinator.turn_on()

    async def async_turn_off(self, **kw):
        await self.coordinator.turn_off()


class AutoStartStop(VevorEntity, SwitchEntity):
    _attr_icon = "mdi:thermostat-auto"

    @property
    def is_on(self):
        return self.d.get("auto_start_stop")

    async def async_turn_on(self, **kw):
        await self.coordinator.set_auto_start_stop(True)

    async def async_turn_off(self, **kw):
        await self.coordinator.set_auto_start_stop(False)
