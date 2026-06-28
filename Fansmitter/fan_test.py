import sys, time
sys.path.insert(0, r"C:\Fansmitter\lhm")

import clr
clr.AddReference("LibreHardwareMonitorLib")
from LibreHardwareMonitor.Hardware import Computer, SensorType

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
                if sensor.Name == "Fan #2":
                    if sensor.SensorType == SensorType.Fan:
                        fan_s = sensor
                    if sensor.SensorType == SensorType.Control:
                        ctrl_s = sensor
    return fan_s, ctrl_s

def read_rpm(fan_s):
    refresh()
    return int(fan_s.Value or 0)

fan_s, ctrl_s = find_sensors()

print("")
print("=== FAN CONTROL TEST ===")
print("Watch your PC fan physically during this test")
print("or listen for the speed change")
print("")

# Read baseline
print(f"Baseline RPM: {read_rpm(fan_s)}")
print("")

# Set to minimum
print("Setting fan to 20% (minimum)...")
ctrl_s.Control.SetSoftware(20.0)
time.sleep(8)
rpm_low = read_rpm(fan_s)
print(f"RPM at 20%: {rpm_low}")
print("")

# Set to maximum
print("Setting fan to 100% (maximum)...")
ctrl_s.Control.SetSoftware(100.0)
time.sleep(8)
rpm_high = read_rpm(fan_s)
print(f"RPM at 100%: {rpm_high}")
print("")

# Restore
print("Restoring automatic control...")
ctrl_s.Control.SetDefault()
time.sleep(3)
rpm_restore = read_rpm(fan_s)
print(f"RPM after restore: {rpm_restore}")
print("")

# Result
diff = rpm_high - rpm_low
print("=== RESULT ===")
print(f"Low  (20%):  {rpm_low} RPM")
print(f"High (100%): {rpm_high} RPM")
print(f"Difference:  {diff} RPM")
print("")
if diff > 300:
    print("SUCCESS — fan is responding to control commands")
    print("The RPM difference is large enough for Fansmitter")
else:
    print("WARNING — fan is not responding correctly")
    print("Difference is too small — wrong fan or control blocked")