from instruments import B2901A
from os import listdir

"""Test script to verify that I have communication with SMU working"""

voltage_list = [1,2,3,4,5,6,7,8,9,10]
tstep = 0.1

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
    #SOURCE setup
    smu.setSourceFunctionToVoltage()
    smu.enableSourceVoltAutorange(True)
    smu.setVoltageModeToList()
    smu.setVoltageList(voltage_list)

    #SENSE setup
    smu.setSenseFunctionToCurrent()
    smu.enableSenseCurrentAutorange(True)
    smu.setCurrentComplianceLevel(0.01)

    #smu.enableRemoteSensing(True)
    #smu.enableContinuousTrigger(True)

    #TRIGGER setup
    smu.setTriggerSourceToTimer()
    smu.setTriggerTimerInterval(tstep)
    smu.setTriggerCount(len(voltage_list))
    smu.setTriggerAcquisitionDelay(tstep/10)
    #smu.setTriggerTransientDelay(0)
    #smu.setArmCount(1)
    #smu.setArmImmediate()
    #smu.setArmDelay(0)

    #enable output, initiate measurement, disable output
    smu.enableOutput(True)
    smu.initiate()
    while(smu.busy()):      #polling loop, wait for operation completion
        pass
    smu.enableOutput(False)
    #confirm list was processed
    print(smu.ask(":fetch:arr:volt?"))
