"""BLE connection + polling for a single Vevor AA66-encrypted heater."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CHAR_UUID, CMD_AUTO_START_STOP, CMD_LEVEL_OR_TEMP, CMD_MODE, CMD_POWER,
    CMD_STATUS, CMD_TIME_SYNC, CONF_PIN, DEFAULT_PIN, DOMAIN, ERROR_NAMES, MODE_LEVEL, MODE_TEMPERATURE,
    EVENT_SHUTDOWN, POLL_SECONDS, RESPONSE_TIMEOUT, STALE_CYCLES, STEP_NAMES,
)
from .protocol import build_command, parse

_LOGGER = logging.getLogger(__name__)


class VevorCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN,
            update_interval=timedelta(seconds=POLL_SECONDS),
        )
        self.address: str = entry.data[CONF_ADDRESS].upper()
        self.pin: int = int(entry.data.get(CONF_PIN, DEFAULT_PIN))
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()
        self._waiter: asyncio.Future | None = None
        self._fails = 0
        self._last_off_sent: datetime | None = None
        self._prev_running: int | None = None

    # ---------- BLE plumbing ----------
    async def _connect(self) -> None:
        if self._client and self._client.is_connected:
            return
        dev = bluetooth.async_ble_device_from_address(self.hass, self.address, connectable=True)
        if dev is None:
            raise UpdateFailed(f"Heater {self.address} not seen by any Bluetooth adapter/proxy")
        self._client = await establish_connection(
            BleakClientWithServiceCache, dev, self.address,
            disconnected_callback=self._on_disconnect, max_attempts=3,
        )
        await self._client.start_notify(CHAR_UUID, self._on_notify)
        _LOGGER.debug("Connected to %s", self.address)

    def _on_disconnect(self, _client) -> None:
        _LOGGER.debug("Heater disconnected")
        self._client = None

    def _on_notify(self, _sender, data: bytearray) -> None:
        parsed = parse(bytes(data))
        if parsed is None:
            _LOGGER.debug("Ignoring non-AA66 frame (%d bytes): %s", len(data), bytes(data).hex())
            return
        if self._waiter and not self._waiter.done():
            self._waiter.set_result(parsed)

    async def _send(self, command: int, argument: int = 0) -> dict:
        async with self._lock:
            await self._connect()
            self._waiter = self.hass.loop.create_future()
            try:
                await self._client.write_gatt_char(
                    CHAR_UUID, build_command(command, argument, self.pin), response=False
                )
                return await asyncio.wait_for(self._waiter, RESPONSE_TIMEOUT)
            except (BleakError, asyncio.TimeoutError) as err:
                # Drop the link so the next attempt starts clean
                if self._client:
                    try:
                        await self._client.disconnect()
                    except BleakError:
                        pass
                self._client = None
                raise UpdateFailed(f"cmd {command} failed: {err!r}") from err
            finally:
                self._waiter = None

    # ---------- state ----------
    def _finish(self, p: dict) -> dict:
        unit_f = p["temp_unit_f"]
        p["cab_temperature"] = p["cab_temperature_raw"] / 10
        p["set_temp"] = p["set_temp_raw"]
        p["unit"] = "F" if unit_f else "C"
        p["connected"] = True
        self._log_shutdown(p)
        return p

    def _log_shutdown(self, p: dict) -> None:
        """Record exactly why the heater went from on to off."""
        prev, now = self._prev_running, p["running_state"]
        self._prev_running = now
        if prev == 1 and now == 0:
            by_us = (
                self._last_off_sent is not None
                and (datetime.now() - self._last_off_sent).total_seconds() < 60
            )
            info = {
                "sent_off_from_ha": by_us,
                "step": STEP_NAMES.get(p["running_step"], p["running_step"]),
                "error": ERROR_NAMES.get(p["error_code"], p["error_code"]),
                "voltage": p["supply_voltage"],
                "timer_enabled": p["timer_enabled"],
                "timer_duration_min": p["timer_duration_min"],
                "auto_start_stop": p["auto_start_stop"],
                "mode": p["running_mode"],
                "decrypted_hex": p["decrypted_hex"],
            }
            _LOGGER.warning("Heater turned OFF: %s", info)
            self.hass.bus.async_fire(EVENT_SHUTDOWN, info)

    async def _async_update_data(self) -> dict:
        try:
            p = self._finish(await self._send(CMD_STATUS))
            self._fails = 0
            return p
        except UpdateFailed:
            self._fails += 1
            if self.data and self._fails <= STALE_CYCLES:
                return self.data
            raise

    async def _command(self, command: int, argument: int = 0) -> None:
        p = self._finish(await self._send(command, argument))
        self.async_set_updated_data(p)

    # ---------- public commands ----------
    async def turn_on(self) -> None:
        await self._command(CMD_POWER, 1)

    async def turn_off(self) -> None:
        self._last_off_sent = datetime.now()
        _LOGGER.info("OFF command sent from Home Assistant")
        await self._command(CMD_POWER, 0)

    async def _ensure_mode(self, mode: int) -> None:
        # Cmd 4 means "level" in Level mode and "temperature" in Temperature mode,
        # so always be in the right mode before sending it.
        if (self.data or {}).get("running_mode") != mode:
            await self._command(CMD_MODE, mode)

    async def set_level(self, level: int) -> None:
        await self._ensure_mode(MODE_LEVEL)
        await self._command(CMD_LEVEL_OR_TEMP, max(1, min(10, int(level))))

    async def set_temperature(self, value: int) -> None:
        """Heater's own Temperature mode. Value is in the heater's display unit."""
        lo, hi = (46, 97) if (self.data or {}).get("temp_unit_f") else (8, 36)
        await self._ensure_mode(MODE_TEMPERATURE)
        await self._command(CMD_LEVEL_OR_TEMP, max(lo, min(hi, int(value))))

    async def set_mode(self, mode: int) -> None:
        await self._command(CMD_MODE, mode)

    async def set_auto_start_stop(self, enabled: bool) -> None:
        await self._command(CMD_AUTO_START_STOP, 1 if enabled else 0)

    async def sync_time(self) -> None:
        now = datetime.now()
        await self._command(CMD_TIME_SYNC, now.hour * 60 + now.minute)

    async def shutdown(self) -> None:
        if self._client:
            try:
                await self._client.disconnect()
            except BleakError:
                pass
            self._client = None
