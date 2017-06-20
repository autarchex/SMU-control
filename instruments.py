import time
import usbtmc

"""This module contains control classes for USB Test & Measurement Class
(USBTMC) instruments, using the python-ivi python-usbtmc driver."""

def list_usbtmc_devices():
    """List all attached USBTMC devices.  Now just calls function in driver."""
    return usbtmc.list_devices()

class Instrument:
    """Template class for generic instruments.  Creates an instance of
    usbtmc.Instrument class in upon connection. Other specific instruments
    inherit from this.  Instruments must speak SCPI / USB488."""
    def __init__(self):
        self.description = "USB TMC instrument (generic)"
        self.drv = ""
        self.connected = False
        self.mfr = ""               #manufacturer
        self.model = ""             #model number
        self.sn = ""                #serial number
        self.version = ""           #revision number
        self.expectedModel = ""     #expected model number
        self.expectedMfr = ""       #expected manufacturer
        self.VID = ""               #USB vendor ID code
        self.PID = ""               #USB product ID code

    def find(self):
        """Find first attached instance of the instrument and return its
        device ID in device reference form usable by connect()."""
        if self.VID is None or self.PID is None:
            print("Error: No VID/PID to find!")
            return None
        else:
            dev = usbtmc.find_device(idVendor=self.VID, idProduct=self.PID)
            if dev is None:
                print("Error: Could not find instrument!")
            return dev

    def connect(self, device):
        """Open connection to the instrument. Request instrument to identify,
        populate mfr, model, serial, version numbers, and check that they match."""
        if device is None:
            print("Error: No device found, cannot connect.")
            return
        self.drv = usbtmc.Instrument(dev=device)    #create driver interface
        self.drv.open()
        self.connected = True
        [self.mfr, self.model, self.sn, self.version] = self.identify().split(',')
        if self.mfr != self.expectedMfr:
            print("Warning: manufacturer mismatch. Received \'" + self.mfr + "\', expected \'" + self.expectedMfr + "\'")
        if self.model != self.expectedModel:
            print("Warning: model mismatch. Received \'" + self.model + "\', expected \'" + self.expectedModel + "\'")

    def disconnect(self):
        """Close connection with instrument."""
        if not self.connected:
            return
        else:
            self.drv.close()            #close the driver interface
            self.drv = ""               #delete object reference
            self.connected = False

    def write(self, command):
        """Write a command string to the instrument."""
        self.drv.write(command)

    def read(self, length=-1):
        """Read data from the instrument."""
        return self.drv.read(length)

    def ask(self, command, length=-1):
        """combined write-read for commands that end in '?', for convenience."""
        self.drv.write(command)
        return self.drv.read(length)

    #COMMON SCPI COMMANDS
    def identify(self):
        return self.ask("*IDN?")

    def reset(self):
        self.write("*RST")

    def clearStatus(self):
        self.write("*CLS")

    def status(self):
        return self.drv.read_stb()

    def wait(self):
        """Issues a *WAI 'wait' command, which prohibits instrument from
        executing new commands until all pending commands have completed.  Does
        not block."""
        self.write("*WAI")

    def shortWaitForComplete(self):
        """This is a BLOCKING wait for previous operations to complete.  It is
        suitable for waiting on completion of reasonably short-duration (<2 sec)
        operations.  Using this method to wait on longer operations WILL result
        in a timeout error."""
        self.ask("*OPC?")

    def monitor(self):
        """This should be called immediately after any operation which will
        take a long time (>2 s) to complete.  It sets the OPC (operation complete)
        bit in the status register.  Subsequent calls to busy() will check this
        bit and use it to determine if the long operation has completed yet."""
        self.write("*WAI;*OPC")

    def done(self):
        """This is a NON-BLOCKING query that returns True if the instrument has
        completed all previously assigned operations that were followed by a
        call to monitor(), and False if it is still busy. This clears the ESR
        register."""
        print("Requesting status byte")
        n = int(self.status())       #get status register
        opcbit = n & 0x01                 #OPC bit is bit 0
        print("STB=" + str(n) + " and OPC bit is: ", opcbit)
        if opcbit == 1:                 #if operation is complete
            return True
        else:
            return False



class B2901A(Instrument):
    """This class represents and controls a Keysight B2901A SMU.  For operating
    details of this instrument, refer to Keysight document B2910-90030, titled
    "Keysight B2900 SCPI Command Reference"."""

    def __init__(self):
        super().__init__()
        self.description = "Keysight B2901 SMU"
        self.expectedMfr = "Keysight Technologies"
        self.expectedModel = "B2901A"
        self.VID = 0x0957
        self.PID = 0x8b18

    #SOURCE control methods
    def setSourceFunctionToVoltage(self):
        self.write(":FUNC:MODE VOLT")

    def setSourceFunctionToCurrent(self):
        self.write(":FUNC:MODE CURR")

    def setVoltage(self,v):
        """Takes float argument."""
        self.write(":VOLT " + str(v))

    def setCurrent(self,a):
        """Takes float argument."""
        self.write(":CURR " + str(a))

    def setOutputShapeToDC(self):
        self.write(":FUNC DC")

    def setOutputShapeToPulse(self):
        self.write(":FUNC PULS")

    def setVoltageModeToList(self):
        self.write(":SOURCE:VOLT:MODE LIST")

    def setVoltageModeToFixed(self):
        self.write(":SOURCE:VOLT:MODE FIX")

    def setVoltageList(self, vsl):
        """vsl is list of voltages for sweep"""
        s = str(vsl).split(']')[0].split('[')[1]  #make string from list, remove brackets
        self.write(":LIST:VOLT " + s)

    def enableContinuousTrigger(self, en=True):
        if en:
            self.write(":FUNC:TRIG:CONT ON")
        else:
            self.write(":FUNC:TRIG:CONT OFF")

    def enableSourceVoltAutorange(self, en=True):
        if en:
            self.write(":SOUR:VOLT:RANG:AUTO ON")
        else:
            self.write(":SOUR:VOLT:RANG:AUTO OFF")

    #SENSE control methods
    #--------------------------
    def setSenseFunctionToCurrent(self):
        self.write(":SENS:FUNC CURR")

    def setSenseFunctionToVoltage(self):
        self.write(":SENS:FUNC VOLT")

    def setCurrentComplianceLevel(self,a):
        self.write(":SENS:CURR:PROT " + str(a))

    def setVoltageProtectionLevel(self,v):
        self.write(":SENS:VOLT:PROT " + str(v))

    def enableRemoteSensing(self, en=True):
        if en:
            self.write(":SENS:REM ON")
        else:
            self.write(":SENS:REM OFF")

    def enableSenseCurrentAutorange(self, en=True):
        if en:
            self.write(":SENS:CURR:RANG:AUTO ON")
        else:
            self.write(":SENS:CURR:RANG:AUTO OFF")

    #TRIGGER control
    #-------------------------
    def setTriggerAcquisitionDelay(self, delay):
        """set delay between trigger and acquisition"""
        self.write(":TRIG:ACQ:DEL " + str(delay))

    def setTriggerTransientDelay(self, delay):
        """set delay between trigger and transient (output change)"""
        self.write(":TRIG:TRAN:DEL " + str(delay))

    def setArmCount(self, count):
        self.write(":ARM:COUNT " + str(count))

    def setArmImmediate(self):
        self.write(":ARM:IMM")

    def setArmDelay(self, delay):
        self.write(":ARM:DELAY " + str(delay))

    def setTriggerSourceToTimer(self):
        self.write("TRIG:SOURCE TIMER")

    def setTriggerCount(self, count):
        self.write("TRIG:COUNT " + str(count))

    def setTriggerTimerInterval(self, interval):
        self.write("TRIG:TIMER " + str(interval))

    #Other
    #------------------------
    def enableOutput(self, en=True):
        if en:
            self.write(":OUTP ON")
        else:
            self.write(":OUTP OFF")

    def measure(self):
        """Perform a spot measurement using current parameters, returns a float."""
        return float(self.ask(":MEAS?"))

    def initiate(self):
        """Initiates a source/measure operation already set up"""
        self.write(":INIT")

    #Combination functions which make life easier
    #--------------------------
    def performVoltageListSweep(self, vlist, tstep, compliance=0.1):
        """Performs a list sweep, outputting voltage and measuring current.
        vlist is a list of voltages. tstep is the time step (seconds).
        compliance is current compliance limit (amps). Returns a list of two
        lists: [voltages, currents]."""
        print("Trying a list sweep of voltages:" + str(vlist))
        points = len(vlist)
        self.reset()
        self.setSourceFunctionToVoltage()        #output voltage
        self.enableSourceVoltAutorange(True)        #enable voltage autoranging
        self.setVoltageModeToList()                #using list sweep mode
        self.setVoltageList(vlist)                #load requested sweep list
        self.setSenseFunctionToCurrent()            #sensing current
        self.enableSenseCurrentAutorange(True)    #enable current autoranging
        self.setCurrentComplianceLevel(compliance)        #set current compliance
        self.setTriggerSourceToTimer()            #use timer as trigger source
        self.setTriggerTimerInterval(tstep)        #program the timer step
        self.setTriggerCount(points)            #number of data points to collect
        self.setTriggerAcquisitionDelay(tstep/10)
        self.enableOutput(True)                    #turn on output
        self.initiate()                            #begin measurement operation
        self.monitor()
        i = 1
        while(not self.done()):      #poll status byte, wait for operation completion
            print("Instrument busy. Iteration: " + str(i) + " x 100ms")
            i = i + 1
            time.sleep(1)
        print("Instrument no longer busy.")
        self.enableOutput(False)                    #disable source output
        vreply = self.ask(":FETCH:ARR:VOLT?", (10*points))  #get measured voltages
        ireply = self.ask(":FETCH:ARR:CURR?", (10*points))  #""current.  allocate 10 bytes per point in the response
        vmeas = [float(s) for s in vreply.split(',')]        #split reply on commas and convert to floating point values
        imeas = [float(s) for s in ireply.split(',')]
        return [vmeas, imeas]



class MSO2102A(Instrument):
    def __init__(self, device):
        super().__init__()
        self.description = "Rigol MSO2102A Oscilloscope"
        self.expectedMfr = "RIGOL TECHNOLOGIES"
        self.expectedModel = "MSO2102A"
        self.VID = 0x1ab1
        self.PID = 0x04b0
