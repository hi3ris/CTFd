#!/usr/bin/env python3
"""Generate an I2C bus capture (CSV) of a single write transaction.

Two channels are recorded, oversampled:

  SCL - clock
  SDA - data

I2C rules encoded here:
  * SDA may only change while SCL is LOW; it is valid while SCL is HIGH.
  * START  = SDA falls (1->0) while SCL is HIGH.
  * STOP   = SDA rises (0->1) while SCL is HIGH.
  * A byte is 8 bits MSB-first followed by a 9th ACK bit (SDA pulled LOW by
    the receiver = ACK).

The master addresses a 7-bit slave (write), then streams the flag as data
bytes. The flag is the ASCII payload.
"""

import csv
import os

Q = 4  # samples per phase quarter
FLAG = "NCTF{i2c_start_addr_ack_stop_ok}"
SLAVE_ADDR = 0x42  # 7-bit


class I2C:
    def __init__(self):
        self.rows = []
        self.scl = 1
        self.sda = 1

    def emit(self, n=Q):
        for _ in range(n):
            self.rows.append((self.scl, self.sda))

    def start(self):
        self.scl, self.sda = 1, 1
        self.emit()
        self.sda = 0  # SDA falls while SCL high
        self.emit()
        self.scl = 0
        self.emit()

    def stop(self):
        self.scl, self.sda = 0, 0
        self.emit()
        self.scl = 1
        self.emit()
        self.sda = 1  # SDA rises while SCL high
        self.emit()

    def bit(self, value):
        self.scl = 0
        self.sda = value  # change data while clock low
        self.emit()
        self.scl = 1  # clock high -> data valid
        self.emit()
        self.emit()
        self.scl = 0
        self.emit()

    def byte(self, value, ack=0):
        for i in range(7, -1, -1):
            self.bit((value >> i) & 1)
        self.bit(ack)  # 9th ACK/NACK bit


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, os.pardir, "i2c_capture.csv")

    bus = I2C()
    bus.emit(8)  # idle
    bus.start()
    bus.byte((SLAVE_ADDR << 1) | 0, ack=0)  # address + write, ACK
    for b in FLAG.encode():
        bus.byte(b, ack=0)
    bus.stop()
    bus.emit(8)

    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample", "SCL", "SDA"])
        for i, (scl, sda) in enumerate(bus.rows):
            w.writerow([i, scl, sda])

    print("wrote", os.path.abspath(out), "samples:", len(bus.rows))


if __name__ == "__main__":
    main()
