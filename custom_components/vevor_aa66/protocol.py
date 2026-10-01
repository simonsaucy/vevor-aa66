"""AA66 encrypted protocol only (48-byte XOR-encrypted status frames).

Byte map taken from diesel-heater-ble (ProtocolAA66Encrypted).
Commands use the plain 8-byte AA55 frame, same as the original integration.
"""
from __future__ import annotations

_KEY = b"password"


def xor(data: bytes) -> bytes:
    return bytes(b ^ _KEY[i % 8] for i, b in enumerate(data))


def _s16(hi: int, lo: int) -> int:
    v = (hi << 8) | lo
    return v - 0x10000 if v & 0x8000 else v


def _s8(v: int) -> int:
    return v - 256 if v > 127 else v


def build_command(command: int, argument: int, pin: int) -> bytes:
    p = bytearray([0xAA, 0x55, pin // 100, pin % 100, command & 0xFF,
                   argument & 0xFF, (argument >> 8) & 0xFF, 0])
    p[7] = sum(p[2:7]) & 0xFF
    return bytes(p)


def parse(raw: bytes) -> dict | None:
    """Return parsed state, or None if this isn't an AA66 encrypted frame."""
    if len(raw) != 48:
        return None
    d = xor(raw)
    if d[0] != 0xAA or d[1] != 0x66:
        return None
    return {
        "running_state": d[3],
        "running_step": d[5],
        "running_mode": d[8],
        "set_temp_raw": d[9],
        "set_level": max(1, min(10, d[10])),
        "supply_voltage": ((d[11] << 8) | d[12]) / 10,
        "case_temperature": _s16(d[13], d[14]),
        "device_time_min": (d[19] << 8) | d[20],
        "timer_start_min": (d[21] << 8) | d[22],
        "timer_duration_min": (d[23] << 8) | d[24],
        "timer_enabled": bool(d[25]),
        "temp_unit_f": d[27] == 1,
        "auto_start_stop": d[31] == 1,
        "cab_temperature_raw": _s16(d[32], d[33]),
        "heater_offset": _s8(d[34]),
        "error_code": d[35],
        "decrypted_hex": d.hex(),
    }
