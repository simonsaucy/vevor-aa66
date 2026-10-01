from __future__ import annotations

import re

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_FULL_DELTA, CONF_MAX_LEVEL, CONF_MIN_RUN, CONF_OFF_DELTA, CONF_ON_DELTA, CONF_PIN, CONF_SENSOR,
    DEFAULT_FULL_DELTA, DEFAULT_MAX_LEVEL, DEFAULT_MIN_RUN, DEFAULT_OFF_DELTA, DEFAULT_ON_DELTA, DEFAULT_PIN, DOMAIN,
)

_MAC = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


class VevorConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return VevorOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            addr = user_input[CONF_ADDRESS].strip().upper()
            if not _MAC.match(addr):
                errors[CONF_ADDRESS] = "invalid_mac"
            else:
                await self.async_set_unique_id(addr)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Vevor Heater {addr[-5:]}",
                    data={CONF_ADDRESS: addr, CONF_PIN: int(user_input[CONF_PIN])},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): str,
                vol.Required(CONF_PIN, default=DEFAULT_PIN): int,
            }),
            errors=errors,
        )


def _num(lo, hi, step):
    return selector.NumberSelector(
        selector.NumberSelectorConfig(min=lo, max=hi, step=step, mode=selector.NumberSelectorMode.BOX)
    )


class VevorOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        o = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_SENSOR, description={"suggested_value": o.get(CONF_SENSOR)}):
                    selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
                    ),
                vol.Required(CONF_ON_DELTA, default=o.get(CONF_ON_DELTA, DEFAULT_ON_DELTA)): _num(0.5, 10, 0.5),
                vol.Required(CONF_OFF_DELTA, default=o.get(CONF_OFF_DELTA, DEFAULT_OFF_DELTA)): _num(0.5, 10, 0.5),
                vol.Required(CONF_FULL_DELTA, default=o.get(CONF_FULL_DELTA, DEFAULT_FULL_DELTA)): _num(1, 20, 0.5),
                vol.Required(CONF_MAX_LEVEL, default=o.get(CONF_MAX_LEVEL, DEFAULT_MAX_LEVEL)): _num(1, 10, 1),
                vol.Required(CONF_MIN_RUN, default=o.get(CONF_MIN_RUN, DEFAULT_MIN_RUN)): _num(5, 120, 1),
            }),
        )
