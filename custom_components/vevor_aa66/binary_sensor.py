from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory

from .entity import VevorEntity


async def async_setup_entry(hass, entry, add):
    c = entry.runtime_data
    add([Connected(c, "connected", "Connected"), Problem(c, "problem", "Problem"),
         TimerOn(c, "timer_enabled", "Built-in timer")])


class Connected(VevorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        return self.coordinator.last_update_success and self.d.get("connected", False)


class Problem(VevorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self):
        return self.d.get("error_code", 0) != 0


class TimerOn(VevorEntity, BinarySensorEntity):
    _attr_icon = "mdi:timer-outline"

    @property
    def is_on(self):
        return self.d.get("timer_enabled")

    @property
    def extra_state_attributes(self):
        d = self.d
        def hm(m):
            return None if m is None else f"{m // 60:02d}:{m % 60:02d}"
        dur = d.get("timer_duration_min")
        return {
            "start": hm(d.get("timer_start_min")),
            "duration_min": "infinite" if dur == 65535 else dur,
            "heater_clock": hm(d.get("device_time_min")),
        }
