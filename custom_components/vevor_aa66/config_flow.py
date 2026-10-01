from __future__ import annotations

import re

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak, async_discovered_service_info,
)
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_FULL_DELTA, CONF_MAX_LEVEL, CONF_MIN_RUN, CONF_OFF_DELTA, CONF_ON_DELTA, CONF_PIN, CONF_SENSOR,
    DEFAULT_FULL_DELTA, DEFAULT_MAX_LEVEL, DEFAULT_MIN_RUN, DEFAULT_OFF_DELTA, DEFAULT_ON_DELTA, DEFAULT_PIN, DOMAIN,
    SERVICE_UUID,
)

_MAC = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


class VevorConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return VevorOptionsFlow()

    _discovered: BluetoothServiceInfoBleak | None = None

    def _create(self, addr: str, pin: int):
        return self.async_create_entry(
            title=f"Vevor Heater {addr[-5:]}",
            data={CONF_ADDRESS: addr, CONF_PIN: int(pin)},
        )

    # Home Assistant found the heater on its own
    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        await self.async_set_unique_id(discovery_info.address.upper())
        self._abort_if_unique_id_configured()
        self._discovered = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name or discovery_info.address}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input=None):
        info = self._discovered
        if user_input is not None:
            return self._create(info.address.upper(), user_input[CONF_PIN])
        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PIN, default=DEFAULT_PIN): int}),
            description_placeholders={"name": info.name or "Heater", "address": info.address},
        )

    # Manual add: pick from heaters in range, or type a MAC
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            addr = user_input[CONF_ADDRESS].strip().upper()
            if not _MAC.match(addr):
                errors[CONF_ADDRESS] = "invalid_mac"
            else:
                await self.async_set_unique_id(addr)
                self._abort_if_unique_id_configured()
                return self._create(addr, user_input[CONF_PIN])

        taken = self._async_current_ids()
        found = []
        for info in async_discovered_service_info(self.hass, connectable=True):
            addr = info.address.upper()
            uuids = [u.lower() for u in info.service_uuids]
            if addr in taken or not (SERVICE_UUID in uuids or 65535 in info.manufacturer_data):
                continue
            found.append(selector.SelectOptionDict(
                value=addr, label=f"{info.name or 'Unknown'}  {addr}  ({info.rssi} dBm)"))

        addr_field = (
            selector.SelectSelector(selector.SelectSelectorConfig(
                options=found, custom_value=True, mode=selector.SelectSelectorMode.DROPDOWN))
            if found else str
        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS, default=found[0]["value"] if len(found) == 1 else vol.UNDEFINED): addr_field,
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
