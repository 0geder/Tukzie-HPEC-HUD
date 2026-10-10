"""Read the stand-in ToF sensors (VL53L0X micromouse micro-sensors) on the Pi.

The UCT 2025 micromouse sensor board carries three micro-sensors facing
left, ahead and right. Each is a VL53L0X (VL53L0CXV0DH1 in the micro-sensor
schematic) on a six-pin header: 1 GPIO1 (interrupt, unused), 2 XSHUT,
3 SDA, 4 SCL, 5 GND, 6 3V3. XSHUT has a 10k pull-up on the sensor, so a
sensor is on unless its XSHUT is pulled low. There are no I2C pull-ups on
the sensor; the Pi's own 1.8k pull-ups on pins 3 and 5 are enough.

All VL53L0X start at address 0x29. With three sensors, each XSHUT goes to
a Pi GPIO; the script holds all low, then wakes them one at a time and
moves each to its own address. With one sensor (--single) no XSHUT wire is
needed.

Wiring (Pi physical pins): 3V3 pin 1, GND pin 6 (pin 9 is the ESP32 sync ground), SDA pin 3, SCL pin 5,
XSHUT left/ahead/right to GPIO22/23/24 (pins 15, 16, 18).
Enable I2C first: sudo raspi-config nonint do_i2c 0
Install: venv/bin/pip install adafruit-blinka adafruit-circuitpython-vl53l0x

Usage: python3 tof_reader.py [--single] [--duration 30] [--csv tof.csv]
"""
import argparse
import time

XSHUT = {"left": 22, "ahead": 23, "right": 24}
ADDRESSES = {"left": 0x30, "ahead": 0x31, "right": 0x32}
OUT_OF_RANGE_MM = 8000   # the VL53L0X reports about 8190 when nothing returns
IO_TIMEOUT_S = 0.5       # the driver's default 0 waits forever; one stuck sensor froze all three (10 Oct)


def clean_mm(mm):
    """A range reading in mm, or None when there is no valid return
    (0, about 8190 for nothing in range, or not a number)."""
    if mm is None or isinstance(mm, bool):
        return None
    try:
        mm = int(mm)
    except (TypeError, ValueError, OverflowError):
        return None
    return None if mm <= 0 or mm >= OUT_OF_RANGE_MM else mm


def open_sensors(single, handles=None):
    """Return {name: VL53L0X}. If a list is passed as handles, the I2C bus
    and XSHUT pins are appended to it so a long-running caller (the
    telemetry bridge) can release them with deinit() before retrying."""
    import board
    import busio
    import digitalio
    import adafruit_vl53l0x

    i2c = busio.I2C(board.SCL, board.SDA)
    if handles is not None:
        handles.append(i2c)
    if single:
        return {"ahead": adafruit_vl53l0x.VL53L0X(i2c, io_timeout_s=IO_TIMEOUT_S)}

    pins = {}
    for name, gpio in XSHUT.items():
        p = digitalio.DigitalInOut(getattr(board, "D%d" % gpio))
        if handles is not None:
            handles.append(p)
        p.switch_to_output(value=False)
        pins[name] = p
    time.sleep(0.05)
    sensors = {}
    for name in XSHUT:
        pins[name].value = True        # wake this one only
        time.sleep(0.05)
        try:
            s = adafruit_vl53l0x.VL53L0X(i2c, io_timeout_s=IO_TIMEOUT_S)
            s.set_address(ADDRESSES[name])
        except (ValueError, OSError, RuntimeError) as e:
            # One sensor not answering (loose wire, dead board) must not take the other two
            # down with it: hold it off so it cannot sit at 0x29, and carry on without it.
            pins[name].value = False
            print("ToF %s not answering (%s: %s); continuing without it" % (name, type(e).__name__, e))
            continue
        sensors[name] = s
    if not sensors:
        raise ValueError("no ToF sensor answered")
    return sensors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--single", action="store_true", help="one sensor at 0x29, no XSHUT wiring")
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()

    sensors = open_sensors(a.single)
    for s in sensors.values():
        s.start_continuous()
    print("sensors: %s" % ", ".join(sensors))
    out = open(a.csv, "w") if a.csv else None
    if out:
        out.write("t_mono_s," + ",".join("%s_mm" % n for n in sensors) + "\n")

    n, t0 = 0, time.monotonic()
    try:
        while time.monotonic() - t0 < a.duration:
            vals = {}
            for name, s in sensors.items():
                vals[name] = clean_mm(s.range)
            n += 1
            print("  ".join("%s %5s" % (k, "-" if v is None else "%d mm" % v) for k, v in vals.items()))
            if out:
                out.write("%.3f,%s\n" % (time.monotonic(), ",".join("" if v is None else str(v) for v in vals.values())))
    except KeyboardInterrupt:
        pass
    finally:
        for s in sensors.values():
            s.stop_continuous()
        if out:
            out.close()
    dt = time.monotonic() - t0
    print("%d readings in %.1f s (%.1f per second per sensor)" % (n, dt, n / dt if dt else 0))


if __name__ == "__main__":
    main()
