"""Constants for the Vevor AA66-encrypted heater integration."""
DOMAIN = "vevor_aa66"
CONF_PIN = "pin"
DEFAULT_PIN = 1234

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

POLL_SECONDS = 15
RESPONSE_TIMEOUT = 5.0
STALE_CYCLES = 3  # keep last good data this many failed polls

CMD_STATUS = 1
CMD_MODE = 2
CMD_POWER = 3
CMD_LEVEL_OR_TEMP = 4
CMD_TIME_SYNC = 10
CMD_AUTO_START_STOP = 18

MODE_LEVEL = 1
MODE_TEMPERATURE = 2
MODES = {"Level": MODE_LEVEL, "Temperature": MODE_TEMPERATURE}

STEP_NAMES = {0: "Standby", 1: "Self-test", 2: "Ignition", 3: "Running", 4: "Cooldown", 6: "Ventilation"}
ERROR_NAMES = {
    0: "No fault", 1: "Startup failure", 2: "Lack of fuel", 3: "Supply voltage fault",
    4: "Outlet sensor fault", 5: "Inlet sensor fault", 6: "Pulse pump fault",
    7: "Fan fault", 8: "Ignition unit fault", 9: "Overheating", 10: "Overheat sensor fault",
}

EVENT_SHUTDOWN = f"{DOMAIN}_shutdown"

# Cabin thermostat options (deltas are in the HA system unit, °F or °C)
CONF_SENSOR = "cabin_sensor"
CONF_ON_DELTA = "on_delta"
CONF_OFF_DELTA = "off_delta"
CONF_FULL_DELTA = "full_power_delta"
CONF_MIN_RUN = "min_run_minutes"
DEFAULT_ON_DELTA = 2.0
DEFAULT_OFF_DELTA = 2.0
DEFAULT_FULL_DELTA = 6.0
DEFAULT_MIN_RUN = 15
CONF_MAX_LEVEL = "max_level"
DEFAULT_MAX_LEVEL = 6
MIN_OFF_SECONDS = 300       # let cooldown finish before restarting
LEVEL_CHANGE_SECONDS = 60   # don't spam level changes
SENSOR_STALE_SECONDS = 900  # sensor silent this long -> drop to level 1
