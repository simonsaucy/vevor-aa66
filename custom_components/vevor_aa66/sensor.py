from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT, STATE_UNAVAILABLE, STATE_UNKNOWN, EntityCategory,
    UnitOfElectricPotential, UnitOfTemperature,
)
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_SENSOR, ERROR_NAMES, STEP_NAMES
from .entity import VevorEntity


async def async_setup_entry(hass, entry, add):
    c = entry.runtime_data
    add([
        CabinTemp(c, "cab_temperature", "Cabin temperature", entry.options.get(CONF_SENSOR)),
        CaseTemp(c, "case_temperature", "Case temperature"),
        Voltage(c, "supply_voltage", "Supply voltage"),
        Mapped(c, "running_step", "Running step", STEP_NAMES),
        Mapped(c, "error_code", "Error", ERROR_NAMES),
        RawFrame(c, "decrypted_hex", "Raw frame"),
    ])


class CabinTemp(VevorEntity, SensorEntity):
    """Cabin temperature: mirrors the selected cabin sensor if one is set,
    otherwise falls back to the heater's own (control-panel) reading."""
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, c, key, name, ext_id):
        super().__init__(c, key, name)
        self._ext_id = ext_id

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self._ext_id:
            self.async_on_remove(async_track_state_change_event(
                self.hass, [self._ext_id], self._ext_changed))

    @callback
    def _ext_changed(self, _event):
        self.async_write_ha_state()

    def _ext(self):
        if not self._ext_id or self.hass is None:
            return None
        st = self.hass.states.get(self._ext_id)
        if st is None or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        try:
            return float(st.state), st.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        except ValueError:
            return None

    @property
    def available(self):
        return self._ext() is not None if self._ext_id else super().available

    @property
    def native_unit_of_measurement(self):
        if self._ext_id:
            ext = self._ext()
            return ext[1] if ext and ext[1] else self.hass.config.units.temperature_unit
        return UnitOfTemperature.FAHRENHEIT if self.d.get("temp_unit_f") else UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        if self._ext_id:
            ext = self._ext()
            return ext[0] if ext else None
        return self.d.get("cab_temperature")

    @property
    def extra_state_attributes(self):
        return {
            "source": self._ext_id or "heater control panel",
            "heater_reading": self.d.get("cab_temperature"),
        }


class CaseTemp(VevorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        return self.d.get("case_temperature")


class Voltage(VevorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    @property
    def native_value(self):
        return self.d.get("supply_voltage")


class Mapped(VevorEntity, SensorEntity):
    def __init__(self, c, key, name, names):
        super().__init__(c, key, name)
        self._names = names

    @property
    def native_value(self):
        v = self.d.get(self._key)
        return None if v is None else self._names.get(v, f"Unknown ({v})")


class RawFrame(VevorEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:code-braces"

    @property
    def native_value(self):
        v = self.d.get(self._key)
        return v[:250] if v else None  # 48 bytes = 96 hex chars
