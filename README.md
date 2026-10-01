# Vevor Heater (AA66)

Home Assistant integration for Vevor diesel heaters using the AA66 encrypted Bluetooth protocol only.
Stripped-down fork of the protocol work in [MSDATDE/homeassistant-vevor-heater](https://github.com/MSDATDE/homeassistant-vevor-heater) (MIT).

- Power, Level, Running mode, Target temperature, Auto start/stop
- Cabin thermostat driven by any HA temperature sensor, with max-level cap
- Logs and fires `vevor_aa66_shutdown` with the reason whenever the heater turns off

Install via HACS → Custom repositories → this repo URL, category Integration.
