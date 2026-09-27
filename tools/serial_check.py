"""Shows what your Arduino sends over USB, so the game can be matched to it.

Run:  .venv\Scripts\python tools\serial_check.py
Then move the stick and press its button while it prints. Close the Arduino IDE
Serial Monitor first (only one program can use the port).
"""
import sys
import time

import serial
from serial.tools import list_ports

ports = list(list_ports.comports())
if not ports:
    sys.exit("No COM ports found. Check the USB cable and drivers.")

print("Ports found:")
for i, port in enumerate(ports):
    print(f"  [{i}] {port.device}  {port.description}")
choice = 0 if len(ports) == 1 else int(input("Which one? "))
device = ports[choice].device

for baud in (9600, 115200, 57600, 38400, 19200):
    print(f"\n--- {device} at {baud} baud (move the stick for 3 seconds) ---")
    try:
        with serial.Serial(device, baud, timeout=0.5) as connection:
            end = time.time() + 3
            shown = 0
            while time.time() < end and shown < 15:
                line = connection.readline()
                if line:
                    print(" ", line)
                    shown += 1
    except serial.SerialException as error:
        print("  could not open:", error)
        break
print("\nCopy the readable lines above and send them back.")
