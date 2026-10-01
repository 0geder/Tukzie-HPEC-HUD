"""Read the vehicle BMS over Bluetooth from the laptop (read-only).

Lists the BMS's GATT services and characteristics, then sends the JBD
basic-info query (DD A5 03 00 FF FD 77, register 0x03, a read) and decodes
the reply. Nothing is written to the BMS apart from that query. Used to
check what the pack exposes when the ESP32 cannot find its characteristics.

Usage: python bms_probe.py [MAC] (default: the address in main.cpp)
"""
import asyncio
import sys

from bleak import BleakClient, BleakScanner

MAC = sys.argv[1] if len(sys.argv) > 1 else "a5:c2:37:46:13:76"
NOTIFY = "0000ff01-0000-1000-8000-00805f9b34fb"
WRITE = "0000ff02-0000-1000-8000-00805f9b34fb"
QUERY = bytes([0xDD, 0xA5, 0x03, 0x00, 0xFF, 0xFD, 0x77])


def decode(frame):
    # DD 03 status len data... checksum(2) 77
    if len(frame) < 7 or frame[0] != 0xDD or frame[-1] != 0x77:
        return "not a JBD frame"
    n = frame[3]
    d = frame[4:4 + n]
    csum = (0x10000 - (sum(frame[2:4 + n]) & 0xFFFF)) & 0xFFFF
    ok = csum == int.from_bytes(frame[4 + n:6 + n], "big")
    if len(d) < 23:
        return "short data (%d bytes), checksum %s" % (len(d), "ok" if ok else "BAD")
    u16 = lambda i: int.from_bytes(d[i:i + 2], "big")
    s16 = lambda i: int.from_bytes(d[i:i + 2], "big", signed=True)
    ntc = d[22]
    temps = [(u16(23 + 2 * k) - 2731) / 10 for k in range(ntc) if 24 + 2 * k < len(d)]
    return ("checksum %s | pack %.2f V | current %.2f A | remaining %.2f Ah of %.2f Ah | "
            "SoC %d%% | cycles %d | cells %d | temps %s C | protection 0x%04x | FET 0x%02x"
            % ("ok" if ok else "BAD", u16(0) / 100, s16(2) / 100, u16(4) / 100, u16(6) / 100,
               d[19], u16(8), d[21], temps, u16(16), d[20]))


async def main():
    print("scanning for %s ..." % MAC)
    dev = await BleakScanner.find_device_by_address(MAC, timeout=20)
    if dev is None:
        print("not found (out of range, or another device is connected to it)")
        return
    print("found: %s" % (dev.name,))
    async with BleakClient(dev, timeout=20) as c:
        print("connected")
        for s in c.services:
            print("service %s" % s.uuid)
            for ch in s.characteristics:
                print("   char %s  %s" % (ch.uuid, ",".join(ch.properties)))
        buf = bytearray()
        done = asyncio.Event()

        def on_data(_, data):
            buf.extend(data)
            if buf and buf[-1] == 0x77 and len(buf) >= 7:
                done.set()

        await c.start_notify(NOTIFY, on_data)
        await c.write_gatt_char(WRITE, QUERY, response=False)
        try:
            await asyncio.wait_for(done.wait(), 5)
        except asyncio.TimeoutError:
            pass
        await c.stop_notify(NOTIFY)
        print("reply (%d bytes): %s" % (len(buf), buf.hex(" ")))
        print(decode(bytes(buf)) if buf else "no reply")


asyncio.run(main())
