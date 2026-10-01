from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature

from .entity import VevorEntity


async def async_setup_entry(hass, entry, add):
    c = entry.runtime_data
    add([Level(c, "level", "Level"), TargetTemp(c, "target_temp", "Target temperature")])


class Level(VevorEntity, NumberEntity):
    _attr_native_min_value = 1
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:fire"

    @property
    def native_value(self):
        return self.d.get("set_level")

    async def async_set_native_value(self, value):
        await self.coordinator.set_level(int(value))


class TargetTemp(VevorEntity, NumberEntity):
    """Sent and shown in whatever unit the heater itself is set to."""
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    @property
    def _f(self):
        return self.d.get("temp_unit_f", False)

    @property
    def native_unit_of_measurement(self):
        return UnitOfTemperature.FAHRENHEIT if self._f else UnitOfTemperature.CELSIUS

    @property
    def native_min_value(self):
        return 46 if self._f else 8

    @property
    def native_max_value(self):
        return 97 if self._f else 36

    @property
    def native_value(self):
        return self.d.get("set_temp")

    async def async_set_native_value(self, value):
        await self.coordinator.set_temperature(int(value))
