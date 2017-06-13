from instruments import B2901A
from os import listdir

"""Test script to verify that I have communication with SMU working"""

devices = listdir("/dev/")           #get listing of contents of /dev directory
usbtmcdevices = list(s for s in devices if "usbtmc" in s)  #list all usbtmc* filenames in /dev

if len(usbtmcdevices) > 0:
    #print("Found:", usbtmcdevices)
    #print("Selecting:", usbtmcdevices[0])
    devicepath = "/dev/" + usbtmcdevices[0] #select first available match
    found = True
else:
    print("No USB TMC devices found!")
    devicepath = ""
    found = False

if found:
    smu = B2901A(devicepath)
    smu.reset()

    smu.setSourceFunctionVoltage()
    smu.setOutputShapeDC()
    smu.setCurrentComplianceLevel(0.01)
    smu.enableRemoteSensing(True)
    smu.enableContinuousTrigger(True)
    smu.enableSourceVoltAutorange(True)
    smu.setVoltage(11.275)
    smu.enableOutput(True)
