from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfElectricPotential, UnitOfTemperature

from .const import ERROR_NAMES, STEP_NAMES
from .entity import VevorEntity


async def async_setup_entry(hass, entry, add):
    c = entry.runtime_data
    add([
        CabinTemp(c, "cab_temperature", "Cabin temperature"),
        CaseTemp(c, "case_temperature", "Case temperature"),
        Voltage(c, "supply_voltage", "Supply voltage"),
        Mapped(c, "running_step", "Running step", STEP_NAMES),
        Mapped(c, "error_code", "Error", ERROR_NAMES),
        RawFrame(c, "decrypted_hex", "Raw frame"),
    ])


class CabinTemp(VevorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self):
        return UnitOfTemperature.FAHRENHEIT if self.d.get("temp_unit_f") else UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        return self.d.get("cab_temperature")

    @property
    def extra_state_attributes(self):
        return {"raw": self.d.get("cab_temperature_raw"), "heater_offset": self.d.get("heater_offset")}


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
