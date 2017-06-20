from instruments import B2901A, list_usbtmc_devices
from os import listdir

"""Test script to verify that I have communication with SMU working"""

voltage_list = list(range(40))
tstep = 1

print("The following USBTMC devices were found:")
print(list_usbtmc_devices())

smu = B2901A()
dev = smu.find()
if dev is None:
    print("Could not find the SMU! Exiting...")
    exit()
else:
    smu.connect(dev)

smu.reset()
[v,i] = smu.performVoltageListSweep(voltage_list, tstep, compliance=0.1)
print("Measured voltages: " + str(v))
print("Measured currents: " + str(i))
