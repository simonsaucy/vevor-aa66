from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME, EntityCategory
from homeassistant.helpers import entity_registry as er

from .const import CONF_SENSOR, HEATER_SIZES, MODES
from .entity import VevorEntity

NONE_OPTION = "None (heater's own sensor)"


async def async_setup_entry(hass, entry, add):
    c = entry.runtime_data
    add([RunningMode(c, "running_mode", "Running mode"),
         CabinSensorPicker(c, "cabin_sensor_picker", "Cabin sensor", entry),
         HeaterSize(c, "heater_size", "Heater size")])


class RunningMode(VevorEntity, SelectEntity):
    _attr_options = list(MODES)
    _attr_icon = "mdi:cog"

    @property
    def current_option(self):
        m = self.d.get("running_mode")
        return next((k for k, v in MODES.items() if v == m), None)

    async def async_select_option(self, option):
        await self.coordinator.set_mode(MODES[option])


class CabinSensorPicker(VevorEntity, SelectEntity):
    """Pick the cabin temperature sensor right from the device page.
    Saves to the integration's options (same as Configure) and reloads."""
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:thermometer-lines"

    def __init__(self, c, key, name, entry):
        super().__init__(c, key, name)
        self._entry = entry

    def _sensors(self) -> dict[str, str]:
        """label -> entity_id for every temperature sensor except our own."""
        own = {
            e.entity_id for e in er.async_entries_for_config_entry(
                er.async_get(self.hass), self._entry.entry_id)
        }
        out = {}
        for st in self.hass.states.async_all("sensor"):
            if st.attributes.get(ATTR_DEVICE_CLASS) != "temperature" or st.entity_id in own:
                continue
            name = st.attributes.get(ATTR_FRIENDLY_NAME, st.entity_id)
            out[f"{name} ({st.entity_id})"] = st.entity_id
        return dict(sorted(out.items()))

    @property
    def options(self):
        return [NONE_OPTION, *self._sensors()]

    @property
    def available(self):
        return True

    @property
    def current_option(self):
        cur = self._entry.options.get(CONF_SENSOR)
        if not cur:
            return NONE_OPTION
        return next((k for k, v in self._sensors().items() if v == cur), NONE_OPTION)

    async def async_select_option(self, option):
        opts = dict(self._entry.options)
        if option == NONE_OPTION:
            opts.pop(CONF_SENSOR, None)
        else:
            opts[CONF_SENSOR] = self._sensors()[option]
        # Triggers the integration's update listener -> reload with the new sensor
        self.hass.config_entries.async_update_entry(self._entry, options=opts)


class HeaterSize(VevorEntity, SelectEntity):
    """Used only for the fuel estimate."""
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(HEATER_SIZES)
    _attr_icon = "mdi:radiator"

    @property
    def available(self):
        return True

    @property
    def current_option(self):
        return self.coordinator.fuel["heater_size"]

    async def async_select_option(self, option):
        self.coordinator.set_heater_size(option)
