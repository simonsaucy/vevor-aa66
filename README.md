# Vevor Heater (AA66)

A lean Home Assistant integration for **Vevor diesel heaters that use the AA66 encrypted Bluetooth protocol**. It connects locally over Bluetooth, with no cloud and no app.

This is a stripped-down, single-protocol rework of the protocol work in [MSDATDE/homeassistant-vevor-heater](https://github.com/MSDATDE/homeassistant-vevor-heater) and [diesel-heater-ble](https://pypi.org/project/diesel-heater-ble/) (both MIT). Support for other brands and protocols, fuel tracking, and auto-offset logic has been removed. The goal is predictable control of one type of heater.

## Is this for my heater?

Only if your heater reports the **AA66 encrypted** protocol. If you're using the original Diesel Heater integration, open **Developer Tools → States** and check `sensor.diesel_heater_protocol`. If it shows anything other than `AA66 encrypted`, use the original integration instead.

## Features

- **Power, Level (1–10), Running mode, and Target temperature**, with the heater automatically switched to the correct mode before each command. The heater uses the same command for "level" and "temperature," so sending it in the wrong mode would set the wrong value.
- **Cabin thermostat** driven by any Home Assistant temperature sensor (for example, a Zigbee sensor inside the cabin while the heater sits outside), with a configurable **max level** cap.
- **Shutdown diagnostics**: every on→off transition is logged with the reason (error code, voltage, running step, timer state, raw frame) and fires a `vevor_aa66_shutdown` event.
- **Built-in timer visibility**: shows whether the heater's own timer is enabled and its duration, which is a common cause of unexplained shutoffs.
- **Correct units**: temperatures follow the heater's own °C/°F setting.
- **Fuel estimate**: set your tank size (1–15 L) and heater size, and get estimated fuel remaining, fuel rate, and runtime left, with a reset button for when you refill.

## Installation

### HACS (recommended)

1. In HACS, open **⋮ → Custom repositories**.
2. Add `https://github.com/simonsaucy/vevor-aa66` with type **Integration**.
3. Search for **Vevor Heater (AA66)**, download it, and restart Home Assistant.

### Manual

Copy `custom_components/vevor_aa66` into your Home Assistant `/config/custom_components/` folder and restart.

## Setup

1. **Disable any other heater integration or close the Vevor app.** The heater only accepts one Bluetooth connection at a time.
2. Go to **Settings → Devices & Services → Add Integration → Vevor Heater (AA66)**.
3. Enter the heater's Bluetooth MAC address and PIN (the default is `1234`).

Home Assistant's Bluetooth adapter or an ESPHome Bluetooth proxy must be in range of the heater.

## Entities

| Entity | What it does |
|---|---|
| `switch.vevor_heater_power` | Heater on/off |
| `number.vevor_heater_level` | Level 1–10 (switches to Level mode first) |
| `number.vevor_heater_target_temperature` | Heater's own Temperature mode target, in the heater's unit (switches to Temperature mode first) |
| `select.vevor_heater_running_mode` | Level / Temperature |
| `switch.vevor_heater_auto_start_stop` | Heater's built-in auto start/stop (Temperature mode only) |
| `climate.vevor_heater_cabin_thermostat` | Cabin thermostat (appears once a sensor is configured) |
| `sensor.vevor_heater_cabin_temperature` | Heater's own temperature reading |
| `sensor.vevor_heater_case_temperature` | Heater case temperature |
| `sensor.vevor_heater_supply_voltage` | Supply voltage |
| `sensor.vevor_heater_running_step` | Standby / Self-test / Ignition / Running / Cooldown |
| `sensor.vevor_heater_error` | Fault code, in plain text |
| `binary_sensor.vevor_heater_built_in_timer` | Heater timer enabled, with start, duration, and heater clock as attributes |
| `binary_sensor.vevor_heater_problem` | On when the heater reports a fault |
| `binary_sensor.vevor_heater_connected` | Bluetooth link status |
| `sensor.vevor_heater_raw_frame` | Decrypted status frame, for debugging |
| `button.vevor_heater_sync_clock` | Sets the heater clock to Home Assistant time |
| `select.vevor_heater_cabin_sensor` | Pick the cabin temperature sensor from the device page |
| `number.vevor_heater_tank_size` | Fuel tank size, 1–15 L |
| `select.vevor_heater_heater_size` | 2 / 5 / 8 kW, used for the fuel estimate |
| `sensor.vevor_heater_fuel_remaining` | Estimated fuel left in the tank |
| `sensor.vevor_heater_fuel_used_since_refill` | Estimated fuel burned since the last reset |
| `sensor.vevor_heater_fuel_rate` | Current estimated burn rate (L/h) |
| `sensor.vevor_heater_fuel_runtime_left` | Hours left at the current level |
| `sensor.vevor_heater_last_refueled` | When the fuel counter was last reset |
| `button.vevor_heater_reset_fuel_refilled` | Press after refilling the tank |

## Cabin thermostat

Use this when the heater's own sensor doesn't reflect the space you're heating. Go to **Settings → Devices & Services → Vevor Heater (AA66) → Configure**, pick a temperature sensor, and save. Then set the thermostat to **Heat** and choose a target.

The thermostat runs the heater in **Level mode** and controls it as follows:

- **Starts** when the cabin falls a set distance below target.
- **Scales the level** from 1 up to your max level depending on how far below target the cabin is.
- **Stops** only when the cabin is a set distance above target **and** the heater has run for the minimum run time. This prevents short-cycling, which carbons up diesel heaters.
- **Waits 5 minutes** after a stop before restarting, so the cooldown can finish.
- **Holds level 1** if the sensor stops reporting for 15 minutes, rather than heating blind.
- **Hands off control**: if you switch the heater to its own Temperature mode, the thermostat turns itself off and leaves the heater running.

The options are entered in your Home Assistant temperature unit:

| Option | Default |
|---|---|
| Start when this far below target | 2 |
| Stop when this far above target | 2 |
| Max level when this far below target | 6 |
| Max level the thermostat will use | 6 |
| Minimum run time before stopping (minutes) | 15 |

## Fuel estimate

The integration counts fuel only while the heater is in the Running stage. It uses the burn rate for your heater size, scaled by level, based on Vevor's published consumption ranges:

| Heater size | Level 1 | Level 10 |
|---|---|---|
| 2 kW | 0.14 L/h | 0.24 L/h |
| 5 kW | 0.16 L/h | 0.52 L/h |
| 8 kW | 0.19 L/h | 0.62 L/h |

Press **Reset fuel (refilled)** whenever you fill the tank. The counter survives Home Assistant restarts. If Bluetooth drops out, gaps longer than 10 minutes are not counted, so treat the result as an estimate, not a gauge.

## Diagnosing shutoffs

Whenever the heater turns off, a warning like this is logged:

```
Heater turned OFF: {'sent_off_from_ha': False, 'step': 'Cooldown', 'error': 'No fault', 'voltage': 12.1, 'timer_enabled': True, 'timer_duration_min': 60, ...}
```

If `sent_off_from_ha` is `False`, the heater shut itself off. Check `error`, `voltage`, and `timer_enabled` to see why. You can also build automations on the event:

```yaml
trigger:
  - platform: event
    event_type: vevor_aa66_shutdown
action:
  - service: notify.mobile_app_your_phone
    data:
      message: >
        Heater off: {{ trigger.event.data.error }},
        {{ trigger.event.data.voltage }} V,
        timer {{ trigger.event.data.timer_enabled }}
```

For more detail, enable debug logging:

```yaml
logger:
  logs:
    custom_components.vevor_aa66: debug
```

## Troubleshooting

- **"Heater not seen by any Bluetooth adapter/proxy"**: the heater is out of range, powered off, or already connected to the app or another integration.
- **Commands do nothing**: check the PIN.
- **Temperature looks wrong**: compare `sensor.vevor_heater_raw_frame` with the heater display and open an issue that includes both.

## License

MIT. Derived from [MSDATDE/homeassistant-vevor-heater](https://github.com/MSDATDE/homeassistant-vevor-heater) and [diesel-heater-ble](https://pypi.org/project/diesel-heater-ble/). This project is unofficial and not affiliated with Vevor.
