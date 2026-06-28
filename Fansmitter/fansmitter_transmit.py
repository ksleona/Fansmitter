# fansmitter_transmit.py
# Run as Administrator: python fansmitter_transmit.py
# LibreHardwareMonitor must be running with web server ON

import sys, time
sys.path.insert(0, r"C:\Fansmitter\lhm")

import clr
clr.AddReference("LibreHardwareMonitorLib")
from LibreHardwareMonitor.Hardware import Computer, SensorType

# ============================================================
# CONFIGURATION — edit these values
# ============================================================
FAN_NAME       = "Fan #2"        # CPU fan confirmed
PCT_BIT_0      = 10              # fan speed % for binary 0
PCT_BIT_1      = 100             # fan speed % for binary 1
BIT_DURATION   = 10              # stable acoustic seconds per bit (decoder uses this)
STABILIZE_TIME = 3               # extra seconds for fan to reach target speed
PREAMBLE       = "10100000"
SECRET         = "EH2026" # string to exfiltrate
# ============================================================

computer = Computer()
computer.IsMotherboardEnabled = True
computer.Open()

def refresh():
    for hw in computer.Hardware:
        hw.Update()
        for sub in hw.SubHardware:
            sub.Update()

def find_sensors():
    refresh()
    fan_s = ctrl_s = None
    for hw in computer.Hardware:
        for sub in hw.SubHardware:
            for sensor in sub.Sensors:
                if sensor.Name == FAN_NAME:
                    if sensor.SensorType == SensorType.Fan:
                        fan_s = sensor
                    if sensor.SensorType == SensorType.Control:
                        ctrl_s = sensor
    return fan_s, ctrl_s

def set_fan(ctrl_s, pct):
    ctrl_s.Control.SetSoftware(float(pct))

def read_rpm(fan_s):
    refresh()
    return int(fan_s.Value or 0)

def restore_auto(ctrl_s):
    ctrl_s.Control.SetDefault()

def string_to_binary(text):
    return "".join(format(ord(c), "08b") for c in text)

def build_frame(payload_bits):
    length_bits = format(len(payload_bits) // 8, "08b")
    checksum = 0
    for i in range(0, len(payload_bits), 8):
        checksum ^= int(payload_bits[i:i+8], 2)
    return PREAMBLE + length_bits + payload_bits + format(checksum, "08b")

# Find sensors
fan_s, ctrl_s = find_sensors()

if not ctrl_s:
    print(f"[!] Could not find control sensor for '{FAN_NAME}'")
    print("    Make sure LibreHardwareMonitor is running as Administrator")
    print("    and Options -> Remote Web Server -> Run is enabled")
    computer.Close()
    sys.exit(1)

# Build frame
payload_binary = string_to_binary(SECRET)
frame          = build_frame(payload_binary)
total_time     = len(frame) * (BIT_DURATION + STABILIZE_TIME)
mins           = total_time // 60
secs           = total_time % 60

print("")
print("╔══════════════════════════════════════════════╗")
print("║       FANSMITTER TRANSMITTER                 ║")
print("╠══════════════════════════════════════════════╣")
print(f"║  Fan        : {FAN_NAME:<31}║")
print(f"║  Secret     : {SECRET:<31}║")
print(f"║  Total bits : {len(frame):<31}║")
print(f"║  Duration   : {mins}m {secs}s{'':<27}║")
print(f"║  Speed 0    : {PCT_BIT_0}% (~1000 RPM) (bit 0){'':<10}║")
print(f"║  Speed 1    : {PCT_BIT_1}% (~2800 RPM) (bit 1){'':<10}║")
print(f"║  Stabilize  : {STABILIZE_TIME}s per bit{'':<24}║")
print("╚══════════════════════════════════════════════╝")
print("")
print("  START RECORDING on your phone now")
print("  Position mic end of phone toward the PC fan")
print("")
input("  Press ENTER when phone is recording...")
print("")
print("  Pre-conditioning fan (3s at 50%)...")
set_fan(ctrl_s, 50)
time.sleep(3)
print("  Starting transmission...")
print("")

try:
    for i, bit in enumerate(frame):
        pct = PCT_BIT_1 if bit == "1" else PCT_BIT_0
        set_fan(ctrl_s, pct)

        time.sleep(STABILIZE_TIME)
        rpm = read_rpm(fan_s)
        time.sleep(BIT_DURATION)

        if i < len(PREAMBLE):
            section = "PREAMBLE"
        elif i < len(PREAMBLE) + 8:
            section = "LENGTH"
        elif i < len(frame) - 8:
            char_idx = (i - len(PREAMBLE) - 8) // 8
            char     = SECRET[min(char_idx, len(SECRET)-1)]
            section  = f"PAYLOAD char {char_idx+1} = '{char}'"
        else:
            section = "CHECKSUM"

        progress = int((i / len(frame)) * 40)
        bar = chr(9608) * progress + chr(9617) * (40 - progress)
        print(f"  [{bar}] bit {i+1:3d}/{len(frame)}  val={bit}  {pct:3d}%  RPM={rpm}  {section}")

except KeyboardInterrupt:
    print("\n  Interrupted")

finally:
    restore_auto(ctrl_s)
    computer.Close()
    print("")
    print("  Transmission complete")
    print("  STOP RECORDING on your phone now")
    print("")
    print("  Transfer WAV to C:\\Fansmitter\\recordings\\")
    print("  Then run: python fansmitter_decode.py recordings\\yourfile.wav")