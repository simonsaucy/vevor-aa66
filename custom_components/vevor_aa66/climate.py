"""Cabin thermostat: drives the heater in Level mode from an external HA sensor.

- Below target by `on_delta`  -> start heater (after min off time / cooldown)
- Running                     -> level scales 1..max_level with how far below target
- Above target by `off_delta` -> stop heater (only after min run time)
- Sensor silent 15 min        -> hold heater at level 1, never full blast blind
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta

from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE, ATTR_UNIT_OF_MEASUREMENT, STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature,
)
from homeassistant.core import Event, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import (
    CONF_FULL_DELTA, CONF_MAX_LEVEL, CONF_MIN_RUN, CONF_OFF_DELTA, CONF_ON_DELTA, CONF_SENSOR,
    DEFAULT_FULL_DELTA, DEFAULT_MAX_LEVEL, DEFAULT_MIN_RUN, DEFAULT_OFF_DELTA, DEFAULT_ON_DELTA,
    LEVEL_CHANGE_SECONDS, MIN_OFF_SECONDS, MODE_LEVEL, MODE_TEMPERATURE, SENSOR_STALE_SECONDS,
)
from .entity import VevorEntity

_LOGGER = logging.getLogger(__name__)
C = UnitOfTemperature.CELSIUS


async def async_setup_entry(hass, entry, add):
    if entry.options.get(CONF_SENSOR):
        add([CabinThermostat(entry.runtime_data, entry.options)])


class CabinThermostat(VevorEntity, ClimateEntity, RestoreEntity):
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coord, opts) -> None:
        super().__init__(coord, "cabin_thermostat", "Cabin thermostat")
        self._opts = opts
        self._sensor_id: str = opts[CONF_SENSOR]
        self._hvac = HVACMode.OFF
        self._target_c = 20.0
        self._cur_c: float | None = None
        self._cur_ts = 0.0
        self._last_power = float("-inf")
        self._last_level = float("-inf")
        self._lock = asyncio.Lock()
        self._engaged = False  # thermostat has taken control of the heater

    # ---------- unit helpers (everything internal is °C) ----------
    def _to_c(self, v, unit):
        return TemperatureConverter.convert(v, unit, C)

    def _from_c(self, v):
        return None if v is None else round(TemperatureConverter.convert(v, C, self.temperature_unit), 1)

    def _delta_c(self, key, default):
        return TemperatureConverter.convert_interval(self._opts.get(key, default), self.temperature_unit, C)

    @property
    def temperature_unit(self):
        return self.hass.config.units.temperature_unit

    @property
    def target_temperature_step(self):
        return 1.0 if self.temperature_unit != C else 0.5

    @property
    def min_temp(self):
        return self._from_c(5)

    @property
    def max_temp(self):
        return self._from_c(30)

    # ---------- lifecycle ----------
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            if last.state in (HVACMode.HEAT, HVACMode.OFF):
                self._hvac = HVACMode(last.state)
            if (t := last.attributes.get(ATTR_TEMPERATURE)) is not None:
                self._target_c = self._to_c(float(t), self.temperature_unit)

        self._read_sensor(self.hass.states.get(self._sensor_id))
        self.async_on_remove(async_track_state_change_event(
            self.hass, [self._sensor_id], self._sensor_changed))
        self.async_on_remove(async_track_time_interval(
            self.hass, self._tick, timedelta(seconds=30)))

    def _read_sensor(self, state) -> None:
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return
        try:
            v = float(state.state)
        except ValueError:
            return
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, self.temperature_unit)
        self._cur_c = self._to_c(v, unit)
        self._cur_ts = time.monotonic()

    @callback
    def _sensor_changed(self, event: Event) -> None:
        self._read_sensor(event.data.get("new_state"))
        self.async_write_ha_state()
        self.hass.async_create_task(self._evaluate())

    async def _tick(self, _now) -> None:
        await self._evaluate()

    # ---------- control ----------
    def _level_for(self, err_c: float) -> int:
        span = self._delta_c(CONF_FULL_DELTA, DEFAULT_FULL_DELTA)
        frac = max(0.0, min(1.0, err_c / span))
        top = int(self._opts.get(CONF_MAX_LEVEL, DEFAULT_MAX_LEVEL))
        return 1 + round((top - 1) * frac)

    async def _evaluate(self) -> None:
        if self._hvac != HVACMode.HEAT or self._lock.locked():
            return
        async with self._lock:
            d = self.d
            if not d.get("connected"):
                return
            c = self.coordinator
            now = time.monotonic()
            running = d.get("running_state") == 1
            mode = d.get("running_mode")
            if mode == MODE_LEVEL:
                self._engaged = True
            elif mode == MODE_TEMPERATURE and self._engaged:
                # You picked the heater's own Temperature mode: step aside, leave heater running
                _LOGGER.info("Heater switched to Temperature mode; cabin thermostat set to Off")
                self._hvac = HVACMode.OFF
                self._engaged = False
                self.async_write_ha_state()
                return
            try:
                # Sensor gone quiet: don't heat blind
                if self._cur_c is None or now - self._cur_ts > SENSOR_STALE_SECONDS:
                    if running and d.get("set_level") != 1:
                        _LOGGER.warning("Cabin sensor %s stale; holding heater at level 1", self._sensor_id)
                        await c.set_level(1)
                    return

                err = self._target_c - self._cur_c
                on_d = self._delta_c(CONF_ON_DELTA, DEFAULT_ON_DELTA)
                off_d = self._delta_c(CONF_OFF_DELTA, DEFAULT_OFF_DELTA)
                min_run = self._opts.get(CONF_MIN_RUN, DEFAULT_MIN_RUN) * 60

                if not running:
                    if d.get("running_step") == 4:  # cooldown in progress
                        return
                    if err >= on_d and now - self._last_power >= MIN_OFF_SECONDS:
                        await c.set_level(self._level_for(err))
                        await c.turn_on()
                        self._last_power = now
                        _LOGGER.info("Thermostat start: cabin %.1f°C, target %.1f°C", self._cur_c, self._target_c)
                    return

                if err <= -off_d and now - self._last_power >= min_run:
                    _LOGGER.info("Thermostat stop: cabin %.1f°C, target %.1f°C", self._cur_c, self._target_c)
                    await c.turn_off()
                    self._last_power = now
                    return

                lvl = self._level_for(err)
                if (lvl != d.get("set_level") or mode != MODE_LEVEL) and now - self._last_level >= LEVEL_CHANGE_SECONDS:
                    await c.set_level(lvl)
                    self._last_level = now
            except UpdateFailed as err_:
                _LOGGER.warning("Thermostat command failed: %s", err_)

    # ---------- climate API ----------
    @property
    def hvac_mode(self):
        return self._hvac

    @property
    def hvac_action(self):
        if self._hvac == HVACMode.OFF:
            return HVACAction.OFF
        d = self.d
        if d.get("running_state") == 1 and d.get("running_step") in (2, 3):
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def current_temperature(self):
        return self._from_c(self._cur_c)

    @property
    def target_temperature(self):
        return self._from_c(self._target_c)

    @property
    def extra_state_attributes(self):
        return {"cabin_sensor": self._sensor_id, "heater_level": self.d.get("set_level")}

    async def async_set_temperature(self, **kwargs) -> None:
        if (t := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        self._target_c = self._to_c(float(t), self.temperature_unit)
        self.async_write_ha_state()
        await self._evaluate()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self._hvac = hvac_mode
        self._engaged = False
        self.async_write_ha_state()
        if hvac_mode == HVACMode.OFF:
            if self.d.get("running_state") == 1:
                await self.coordinator.turn_off()
                self._last_power = time.monotonic()
        else:
            await self._evaluate()

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)
