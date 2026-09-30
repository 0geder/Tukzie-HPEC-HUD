"""Identify the time-of-flight sensor on the Pi's I2C bus.

The stand-in sensors from the micromouse board are not marked in the
photos. VL53L0X, VL53L1X, VL6180X and VL53L5CX all answer at address 0x29,
so this reads each chip's model-ID register to tell them apart and prints
which driver to install. Reads only, apart from the VL53L5CX page-select
write, which is tried last and undone.

Enable I2C first: sudo raspi-config nonint do_i2c 0
Usage: python3 tof_probe.py [bus] (default 1: Pi pins 3 SDA, 5 SCL)
"""
import sys

from smbus2 import SMBus, i2c_msg

ADDR = 0x29
DRIVERS = {
    "VL53L0X": "pip install adafruit-circuitpython-vl53l0x (single zone, up to about 2 m)",
    "VL53L1X": "pip install vl53l1x (single zone, up to about 4 m)",
    "VL6180X": "pip install adafruit-circuitpython-vl6180x (single zone, up to about 0.2 m: too short for the vehicle)",
    "VL53L5CX": "the 8x8 sensor ordered for the project",
}


def read8(bus, reg, n=1):
    w, r = i2c_msg.write(ADDR, [reg]), i2c_msg.read(ADDR, n)
    bus.i2c_rdwr(w, r)
    return list(r)


def read16(bus, reg, n=1):
    w, r = i2c_msg.write(ADDR, [reg >> 8, reg & 0xFF]), i2c_msg.read(ADDR, n)
    bus.i2c_rdwr(w, r)
    return list(r)


def write16(bus, reg, val):
    bus.i2c_rdwr(i2c_msg.write(ADDR, [reg >> 8, reg & 0xFF, val]))


def scan(bus):
    found = []
    for a in range(0x08, 0x78):
        try:
            bus.i2c_rdwr(i2c_msg.read(a, 1))
            found.append(a)
        except OSError:
            pass
    return found


def identify(bus):
    # 8-bit register index first: a one-byte write only sets the index,
    # so it cannot change a 16-bit-index chip.
    if read8(bus, 0xC0, 3) == [0xEE, 0xAA, 0x10]:
        return "VL53L0X"
    if read16(bus, 0x010F, 2) == [0xEA, 0xCC]:
        return "VL53L1X"
    if read16(bus, 0x0000) == [0xB4]:
        return "VL6180X"
    write16(bus, 0x7FFF, 0x00)
    try:
        if read16(bus, 0x0000, 2) == [0xF0, 0x02]:
            return "VL53L5CX"
    finally:
        write16(bus, 0x7FFF, 0x02)
    return None


def main():
    busno = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    try:
        bus = SMBus(busno)
    except FileNotFoundError:
        print("/dev/i2c-%d not found: enable I2C (sudo raspi-config nonint do_i2c 0)" % busno)
        return
    with bus:
        found = scan(bus)
        print("devices on bus %d: %s" % (busno, " ".join("0x%02x" % a for a in found) or "none"))
        if ADDR not in found:
            print("nothing at 0x29: check 3V3, GND, SDA, SCL, and that the shutdown pin is not held low")
            return
        chip = identify(bus)
        if chip:
            print("chip: %s -> %s" % (chip, DRIVERS[chip]))
        else:
            print("0x29 answers but the model ID matches none of the known parts")


if __name__ == "__main__":
    main()
