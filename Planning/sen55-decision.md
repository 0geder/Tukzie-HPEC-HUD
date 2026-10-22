# SEN55: repair or future work (22 Oct 2026)

## Facts

- The brief names environmental and air-quality sensing; the SEN55 (particulates, VOC, NOx, humidity, temperature) is the planned part (Methodology, environmental sensing).
- It came without its cable. Its connector is a 6-pin 1.25 mm JST GH type (ACES 51451-0060N-001; mating cable JST GHR-06V-S). Pins: 1 VDD 5 V, 2 GND, 3 SDA, 4 SCL, 5 SEL (to GND for I2C), 6 NC.
- Wires were soldered to test pads instead. The VDD pad (TP1) came off, other pads are damaged, and the sensor does not power up.
- On 21 Oct nothing answered at its address (0x69) on the Pi 4 bus, while the time-of-flight sensors on the same bus did.

## The one test that decides it

Feed 5 V and GND into the connector itself, pins 1 and 2, not the pads:
- with the proper cable (JST GHR-06V-S 6-pin with leads, often sold as a "SEN5x cable" or "GH 1.25 mm 6-pin"), or
- carefully with two fine wires pressed into the connector's pin 1 and pin 2 contacts.

Then:
- The fan spins and the current is about 70 mA or more: the sensor works. Wire SDA and SCL and SEL to GND, check for 0x69 on the bus, add the reading code (Sensirion's I2C commands, start measurement, read every 1 s), and log it with the telemetry. About one day once the cable is in hand.
- The fan does not spin with 5 V at the connector: the board is damaged (most likely where the pads lifted). Stop.

## Deadline and decision

If the cable is not in hand by 31 Oct, or the test above fails, the SEN55 becomes future work. That is not a dummy: the report states plainly that environmental sensing was in scope, the sensor was damaged during fitting without its cable, and gives the recommendation.

Report wording if it becomes future work (Scope and limitations, and Recommendations):
"The SEN55 air-quality sensor was received without its cable. Wires were soldered to its test pads, the supply pad lifted, and the sensor did not power up afterwards, so no environmental data were recorded. A replacement sensor with its cable (JST GHR-06V-S) would let the existing I2C bus of the Raspberry Pi 4 read it with no other hardware change."

Lesson for the report's investigations: fit a connector-based cable; do not solder to a sensor's test pads.
